"""
RAG helper: retrieve context from Azure AI Search, generate answer with Azure OpenAI.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from azure.storage.blob import BlobSasPermissions, generate_blob_sas
from openai import AzureOpenAI

from .config import settings

logger = logging.getLogger(__name__)

# How many conversation turns (user + assistant pairs) to keep in context.
# 5 turns = 10 messages. Enough for a focused topic thread while keeping
# token usage predictable.
MAX_HISTORY_TURNS = 5

SYSTEM_PROMPT = (
    "You are a helpful assistant that answers questions based ONLY on the provided "
    "source documents.\n\n"
    "Rules:\n"
    "1. Answer ONLY using information from the provided sources.\n"
    "2. If the sources don't contain enough information, say exactly: "
    "\"I don't have enough information in the provided documents to answer this question.\"\n"
    "3. Be concise and accurate. Do not make up information.\n\n"
    "Sources:\n{sources}"
)

# Used when the user asks to reformat the previous answer (e.g. "give in steps").
REFORMAT_PROMPT = (
    "You are a helpful assistant. Reformat or restructure the provided previous answer "
    "exactly as the user requests. Do not add new information or change the meaning. "
    "Only change the presentation format."
)

# Used to decide whether the latest message is a reformat request or a new question.
# If it is a new question, the LLM rewrites it as a fully self-contained standalone
# question so the vector search can retrieve the right documents even when the user
# used pronouns or short references like "what about that?" or "how does it apply?".
CONTEXTUALIZE_PROMPT = (
    "You are a conversation assistant. Given the chat history and the user's latest message, "
    "do ONE of the following:\n\n"
    "1. If the user wants to reformat, restructure, or summarize the PREVIOUS assistant answer "
    "(e.g. 'give me in steps', 'list them', 'summarize that', 'make it shorter', "
    "'give me in 3 points', 'list the above', 'give me only 5'), "
    "respond with exactly the single word: REFORMAT\n\n"
    "2. Otherwise rewrite the user's message as a complete, self-contained question "
    "that includes all necessary context from the conversation so it can be understood "
    "without seeing the chat history. Return ONLY the rewritten question — no explanation.\n\n"
    "Examples:\n"
    "  User: 'give me in 3 steps'          → REFORMAT\n"
    "  User: 'list the above'              → REFORMAT\n"
    "  User: 'what about pressure limits?' → 'What are the pressure limits for gas pipeline installation?'\n"
    "  User: 'how does that apply to multi-family buildings?' "
    "→ 'How do the PSE&G gas service application requirements apply to multi-family residential buildings?'"
)


@dataclass
class Citation:
    title: str
    url: str
    page: Optional[int] = None


# ---------------------------------------------------------------------------
# Azure AI Search retrieval
# ---------------------------------------------------------------------------

def _embed(text: str) -> list:
    client = AzureOpenAI(
        azure_endpoint=settings.get_embedding_endpoint(),
        api_key=settings.get_embedding_api_key(),
        api_version=settings.azure_openai_api_version,
    )
    resp = client.embeddings.create(input=text, model=settings.azure_openai_embedding_deployment)
    return resp.data[0].embedding


def _search(query: str, top_k: int) -> list:
    embedding = _embed(query)
    vector_query = VectorizedQuery(
        vector=embedding,
        k_nearest_neighbors=top_k,
        fields="contentVector",
    )
    client = SearchClient(
        endpoint=settings.azure_search_endpoint,
        index_name=settings.azure_search_index_name,
        credential=AzureKeyCredential(settings.azure_search_api_key),
    )
    results = client.search(
        search_text=query,
        vector_queries=[vector_query],
        top=top_k,
        select=["content", "source_file", "page_number", "source_url"],
    )
    return [dict(r) for r in results]


def _sas_url(blob_name: str) -> Optional[str]:
    try:
        conn = settings.azure_storage_connection_string
        parts = dict(p.split("=", 1) for p in conn.split(";") if "=" in p)
        account_name = parts.get("AccountName")
        account_key = parts.get("AccountKey")
        if not account_name or not account_key:
            return None
        token = generate_blob_sas(
            account_name=account_name,
            container_name=settings.azure_storage_container_name,
            blob_name=blob_name,
            account_key=account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.now(timezone.utc) + timedelta(hours=24),
            content_disposition="inline",
            content_type="application/pdf",
        )
        return (
            f"https://{account_name}.blob.core.windows.net"
            f"/{settings.azure_storage_container_name}/{blob_name}?{token}"
        )
    except Exception:
        return None


def _build_citations(chunks: list) -> list:
    seen: set = set()
    citations = []
    for chunk in chunks:
        source_file = chunk.get("source_file", "")
        page = chunk.get("page_number")
        key = (source_file, page)
        if key in seen:
            continue
        seen.add(key)

        url = _sas_url(source_file)
        if url and page:
            url = f"{url}#page={page}"
        elif not url:
            url = chunk.get("source_url") or ""

        title = source_file
        if "." in title:
            title = title.rsplit(".", 1)[0]
        title = title.replace("_", " ").replace("-", " ")

        citations.append(Citation(title=title, url=url, page=page))
    return citations


# ---------------------------------------------------------------------------
# Conversation helpers (Azure OpenAI API as orchestrator)
# ---------------------------------------------------------------------------

def _trim_history(history: list) -> list:
    return history[-(MAX_HISTORY_TURNS * 2):]


def _chat_client() -> AzureOpenAI:
    return AzureOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        api_version=settings.azure_openai_api_version,
    )


def _contextualize_question(question: str, history: list) -> str:
    messages = [{"role": "system", "content": CONTEXTUALIZE_PROMPT}]
    for msg in history:
        role = msg.get("role")
        content = msg.get("content", "")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": question})

    response = _chat_client().chat.completions.create(
        model=settings.azure_openai_chat_deployment,
        messages=messages,
        temperature=0,
        max_tokens=200,
    )
    return (response.choices[0].message.content or "").strip()


def _last_good_assistant_answer(history: list) -> str:
    for msg in reversed(history):
        if msg.get("role") == "assistant":
            content = msg.get("content", "")
            no_info = (
                "don't have enough information" in content.lower()
                or "do not have enough information" in content.lower()
            )
            if content and not no_info:
                return content
    return ""


def _reformat_answer(question: str, prev_answer: str) -> str:
    response = _chat_client().chat.completions.create(
        model=settings.azure_openai_chat_deployment,
        messages=[
            {"role": "system", "content": REFORMAT_PROMPT},
            {"role": "user", "content": f"Previous answer:\n{prev_answer}\n\nRequest: {question}"},
        ],
        temperature=0.1,
        max_tokens=1000,
    )
    return response.choices[0].message.content or ""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def answer(question: str, top_k: Optional[int] = None, chat_history: Optional[list] = None) -> tuple:
    history = _trim_history(chat_history or [])

    if history:
        contextualized = _contextualize_question(question, history)

        if contextualized == "REFORMAT":
            prev_answer = _last_good_assistant_answer(history)
            if prev_answer:
                return _reformat_answer(question, prev_answer), []
        else:
            question = contextualized

    chunks = _search(question, top_k=top_k or settings.top_k)
    if not chunks:
        return (
            "I don't have enough information in the provided documents to answer this question.",
            [],
        )

    sources_text = "\n\n".join(
        f"[{i}] {chunk.get('source_file', 'Unknown')} (Page {chunk.get('page_number', 'N/A')})\n{chunk.get('content', '')}"
        for i, chunk in enumerate(chunks, 1)
    )

    messages = [{"role": "system", "content": SYSTEM_PROMPT.format(sources=sources_text)}]
    for msg in history:
        role = msg.get("role")
        content = msg.get("content", "")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": question})

    response = _chat_client().chat.completions.create(
        model=settings.azure_openai_chat_deployment,
        messages=messages,
        temperature=0.1,
        max_tokens=1000,
    )
    return response.choices[0].message.content or "", _build_citations(chunks)
