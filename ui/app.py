"""
Streamlit UI for the PSEG Tech Manual Assistant.
"""

import os
from typing import Optional

import requests
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# ── Page config (must be first Streamlit call) ────────────────────────────────
st.set_page_config(
    page_title="PSEG Tech Manual Assistant",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    :root {
        --pseg-navy: #1e3a5f;
        --pseg-navy-light: #2d5a87;
        --pseg-orange: #f26522;
        --bg-page: #f7f9fc;
        --bg-card: #ffffff;
        --border-color: #e2e8f0;
        --text-primary: #1a1a2e;
        --text-muted: #718096;
    }

    .stApp { background: var(--bg-page) !important; }

    .main .block-container {
        padding: 1.5rem 2rem 2rem !important;
        max-width: 1300px;
    }

    [data-testid="stChatMessage"] {
        padding: 1rem 1.25rem;
        border-radius: 14px;
        margin: 0.6rem 0;
        box-shadow: 0 1px 3px rgba(30,58,95,0.06);
    }
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatar-user"]) {
        background: linear-gradient(135deg, #eef4fb 0%, #e3ecf7 100%);
        border: 1px solid #d0dff0;
        border-left: 4px solid #4a90d9;
    }
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatar-assistant"]) {
        background: var(--bg-card);
        border: 1px solid var(--border-color);
        border-left: 4px solid var(--pseg-navy);
    }

    [data-testid="stChatInput"] {
        background: var(--bg-card) !important;
        border: 2px solid var(--border-color) !important;
        border-radius: 14px !important;
    }
    [data-testid="stChatInput"]:focus-within {
        border-color: var(--pseg-navy) !important;
    }

    .stButton > button {
        background: linear-gradient(135deg, var(--pseg-navy) 0%, var(--pseg-navy-light) 100%);
        color: white;
        border: none;
        border-radius: 10px;
        font-weight: 600;
    }
    .stLinkButton > a {
        background: var(--pseg-orange) !important;
        color: white !important;
        border-radius: 6px !important;
        font-weight: 600 !important;
    }

    [data-testid="stSidebar"] { background: var(--bg-card) !important; }
    [data-testid="stSidebar"] .stMarkdown h1,
    [data-testid="stSidebar"] .stMarkdown h2,
    [data-testid="stSidebar"] .stMarkdown h3 { color: var(--pseg-navy); }

    .stWarning {
        background: #fffbeb !important;
        border: 1px solid #fde68a !important;
        border-left: 4px solid var(--pseg-orange) !important;
        border-radius: 10px !important;
    }
    .stInfo {
        background: #eff6ff !important;
        border: 1px solid #bfdbfe !important;
        border-left: 4px solid var(--pseg-navy) !important;
        border-radius: 10px !important;
    }

    .streamlit-expanderHeader {
        background: var(--bg-card) !important;
        border: 1px solid #edf2f7 !important;
        border-radius: 10px !important;
        color: var(--pseg-navy) !important;
    }
    .streamlit-expanderContent {
        background: var(--bg-card) !important;
        border: 1px solid #edf2f7 !important;
        border-top: none !important;
    }

    .stSlider > div > div {
        background: linear-gradient(90deg, var(--pseg-navy), var(--pseg-orange)) !important;
    }
    .stSpinner > div { border-top-color: var(--pseg-orange) !important; }

    hr { border: none; height: 1px; background: #edf2f7; margin: 1rem 0; }
</style>
""", unsafe_allow_html=True)

# ── Session state ──────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "feedback" not in st.session_state:
    st.session_state.feedback = {}


# ── Helpers ────────────────────────────────────────────────────────────────────
NO_INFO_PHRASES = [
    "i don't have enough information",
    "i do not have enough information",
    "don't have enough information",
    "do not have enough information",
    "cannot find relevant information",
    "no relevant information",
    "outside the scope",
    "not covered in the documents",
    "not found in the provided",
]


def is_no_info_response(answer: str) -> bool:
    lower = answer.lower()
    return any(phrase in lower for phrase in NO_INFO_PHRASES)


def send_chat_request(question: str, top_k: int, chat_history: Optional[list] = None) -> Optional[dict]:
    try:
        history_payload = [
            {"role": m["role"], "content": m["content"]}
            for m in (chat_history or [])
            if m.get("role") in ("user", "assistant") and m.get("content")
        ]
        resp = requests.post(
            f"{BACKEND_URL}/chat",
            json={"question": question, "top_k": top_k, "chat_history": history_payload},
            timeout=60,
        )
        if resp.status_code == 200:
            return resp.json()
        st.error(f"API Error {resp.status_code}: {resp.text}")
        return None
    except requests.exceptions.ConnectionError:
        st.error(f"Cannot connect to backend at {BACKEND_URL}. Is it running?")
    except requests.exceptions.Timeout:
        st.error("Request timed out. Please try again.")
    except Exception as e:
        st.error(f"Unexpected error: {e}")
    return None


# ── Sidebar ────────────────────────────────────────────────────────────────────
def render_sidebar() -> int:
    with st.sidebar:
        # PSEG logo (inline SVG)
        st.markdown("""
        <div style="text-align:center; padding: 1rem 0 0.5rem;">
            <svg viewBox="0 0 160 60" xmlns="http://www.w3.org/2000/svg" style="height:55px;width:auto;">
                <circle cx="30" cy="30" r="26" fill="#f26522"/>
                <g fill="white">
                    <polygon points="30,8 31.8,19 28.2,19"/>
                    <polygon points="30,8 31.8,19 28.2,19" transform="rotate(30,30,30)"/>
                    <polygon points="30,8 31.8,19 28.2,19" transform="rotate(60,30,30)"/>
                    <polygon points="30,8 31.8,19 28.2,19" transform="rotate(90,30,30)"/>
                    <polygon points="30,8 31.8,19 28.2,19" transform="rotate(120,30,30)"/>
                    <polygon points="30,8 31.8,19 28.2,19" transform="rotate(150,30,30)"/>
                    <polygon points="30,8 31.8,19 28.2,19" transform="rotate(180,30,30)"/>
                    <polygon points="30,8 31.8,19 28.2,19" transform="rotate(210,30,30)"/>
                    <polygon points="30,8 31.8,19 28.2,19" transform="rotate(240,30,30)"/>
                    <polygon points="30,8 31.8,19 28.2,19" transform="rotate(270,30,30)"/>
                    <polygon points="30,8 31.8,19 28.2,19" transform="rotate(300,30,30)"/>
                    <polygon points="30,8 31.8,19 28.2,19" transform="rotate(330,30,30)"/>
                </g>
                <circle cx="30" cy="30" r="6" fill="white"/>
                <text x="66" y="38" font-family="Arial,sans-serif" font-size="28"
                      font-weight="bold" fill="#1e3a5f">PSEG</text>
            </svg>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        st.markdown("### Search Settings")
        top_k = st.slider(
            "Results to retrieve (Top-K)",
            min_value=1, max_value=20, value=5,
            help="Number of document chunks retrieved for each question",
        )

        st.markdown("---")

        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.session_state.feedback = {}
            st.rerun()

        st.markdown("---")

        # Backend health
        st.markdown("### Backend Status")
        try:
            r = requests.get(f"{BACKEND_URL}/health", timeout=4)
            if r.status_code == 200:
                st.success("Connected ✓")
            else:
                st.warning(f"Status {r.status_code}")
        except Exception:
            st.error("Unreachable")

        st.markdown(
            '<div style="margin-top:2rem;font-size:0.75rem;color:#718096;text-align:center;">'
            'PSEG Tech Manual Assistant<br>Powered by Azure AI'
            '</div>',
            unsafe_allow_html=True,
        )

    return top_k


# ── Header ─────────────────────────────────────────────────────────────────────
def render_header():
    st.markdown("""
    <div style="background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%);
                border-radius: 18px; padding: 1.5rem 2rem; margin-bottom: 1.5rem;
                box-shadow: 0 8px 24px rgba(30,58,95,0.12);
                border-bottom: 4px solid #f26522;">
        <div style="display:flex; align-items:center; gap:20px; flex-wrap:wrap;">
            <svg viewBox="0 0 180 50" xmlns="http://www.w3.org/2000/svg"
                 style="height:50px;width:auto;flex-shrink:0;">
                <g transform="translate(22,25)">
                    <circle cx="0" cy="0" r="20" fill="#f26522"/>
                    <g fill="white">
                        <polygon points="0,-17 1.5,-8 -1.5,-8"/>
                        <polygon points="0,-17 1.5,-8 -1.5,-8" transform="rotate(30)"/>
                        <polygon points="0,-17 1.5,-8 -1.5,-8" transform="rotate(60)"/>
                        <polygon points="0,-17 1.5,-8 -1.5,-8" transform="rotate(90)"/>
                        <polygon points="0,-17 1.5,-8 -1.5,-8" transform="rotate(120)"/>
                        <polygon points="0,-17 1.5,-8 -1.5,-8" transform="rotate(150)"/>
                        <polygon points="0,-17 1.5,-8 -1.5,-8" transform="rotate(180)"/>
                        <polygon points="0,-17 1.5,-8 -1.5,-8" transform="rotate(210)"/>
                        <polygon points="0,-17 1.5,-8 -1.5,-8" transform="rotate(240)"/>
                        <polygon points="0,-17 1.5,-8 -1.5,-8" transform="rotate(270)"/>
                        <polygon points="0,-17 1.5,-8 -1.5,-8" transform="rotate(300)"/>
                        <polygon points="0,-17 1.5,-8 -1.5,-8" transform="rotate(330)"/>
                    </g>
                    <circle cx="0" cy="0" r="5" fill="white"/>
                </g>
                <text x="52" y="32" font-family="Arial,sans-serif" font-size="26"
                      font-weight="bold" fill="white">PSEG</text>
            </svg>
            <div style="flex:1;">
                <div style="font-size:1.4rem;font-weight:700;color:white;margin-bottom:4px;">
                    Tech Manual Assistant
                </div>
                <div style="font-size:0.9rem;color:rgba(255,255,255,0.85);">
                    Your intelligent assistant for technical documentation
                </div>
                <div style="display:flex;gap:8px;margin-top:10px;flex-wrap:wrap;">
                    <span style="background:rgba(255,255,255,0.15);padding:4px 12px;
                                 border-radius:20px;font-size:0.75rem;color:white;
                                 border:1px solid rgba(255,255,255,0.2);">AI-Powered</span>
                    <span style="background:rgba(255,255,255,0.15);padding:4px 12px;
                                 border-radius:20px;font-size:0.75rem;color:white;
                                 border:1px solid rgba(255,255,255,0.2);">Citation-Backed</span>
                    <span style="background:rgba(255,255,255,0.15);padding:4px 12px;
                                 border-radius:20px;font-size:0.75rem;color:white;
                                 border:1px solid rgba(255,255,255,0.2);">Enterprise Secure</span>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ── Feedback buttons ───────────────────────────────────────────────────────────
def render_feedback_buttons(msg_idx: int):
    key = f"feedback_{msg_idx}"
    current = st.session_state.feedback.get(key)
    col1, col2, col3 = st.columns([1, 1, 10])
    with col1:
        up_type = "primary" if current == "up" else "secondary"
        if st.button("👍", key=f"up_{msg_idx}", type=up_type, help="Helpful"):
            st.session_state.feedback[key] = None if current == "up" else "up"
            st.rerun()
    with col2:
        down_type = "primary" if current == "down" else "secondary"
        if st.button("👎", key=f"down_{msg_idx}", type=down_type, help="Not helpful"):
            st.session_state.feedback[key] = None if current == "down" else "down"
            st.rerun()
    with col3:
        if current == "up":
            st.caption("Thanks for the feedback!")
        elif current == "down":
            st.caption("Thanks! We'll work to improve.")


# ── Citations renderer ─────────────────────────────────────────────────────────
def render_citations(citations: list):
    """Render an expandable citations panel."""
    with st.expander(f"📚 Sources ({len(citations)})", expanded=False):
        for i, c in enumerate(citations, 1):
            title = c.get("title", "Unknown")
            page = c.get("page")
            url = c.get("url", "")

            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"**[{i}] {title}**")
                if page:
                    st.caption(f"📄 Page {page}")
            with col2:
                if url and page:
                    st.link_button(
                        f"Page {page}", url,
                        use_container_width=True,
                        help=f"Open {title} at page {page}",
                    )
                elif url:
                    st.link_button("Open", url, use_container_width=True)

            if i < len(citations):
                st.divider()


# ── Chat history ───────────────────────────────────────────────────────────────
def render_chat_history():
    assistant_idx = 0
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant":
                no_info = msg.get("no_info", False) or is_no_info_response(msg["content"])
                if no_info:
                    st.warning("This question appears to be outside the scope of the available documents.")
                elif msg.get("citations"):
                    render_citations(msg["citations"])
                render_feedback_buttons(assistant_idx)
                assistant_idx += 1


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    top_k = render_sidebar()
    render_header()
    render_chat_history()

    if prompt := st.chat_input("Ask a question about PSEG technical manuals..."):
        history_before = list(st.session_state.messages)
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Searching documents..."):
                response = send_chat_request(prompt, top_k, chat_history=history_before)

            if response:
                answer = response.get("answer", "No response generated.")
                citations = response.get("citations", [])
                no_info = is_no_info_response(answer)

                st.markdown(answer)

                if no_info:
                    st.warning("This question appears to be outside the scope of the available documents.")
                elif citations:
                    st.markdown("---")
                    render_citations(citations)

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer,
                    "citations": [] if no_info else citations,
                    "no_info": no_info,
                })
            else:
                err = "Failed to get a response. Please check the backend connection."
                st.error(err)
                st.session_state.messages.append({
                    "role": "assistant", "content": err,
                    "citations": [], "no_info": True,
                })

    st.markdown(
        '<div style="text-align:center;padding:1rem 0;margin-top:1.5rem;'
        'color:#718096;font-size:0.8rem;">'
        'PSEG Tech Manual Assistant — Powered by Azure AI'
        '</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
