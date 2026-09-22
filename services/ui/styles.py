# ============================================================
# LawMate Streamlit 스타일
# ============================================================

import streamlit as st


def apply_styles():

    st.markdown(
        """
<style>

.stApp {
    background:
        linear-gradient(
            180deg,
            #f7f9fc 0%,
            #ffffff 38%,
            #f8fafc 100%
        );
    color: #0f172a;
}

.stApp, .stApp *,
.stMarkdown, .stMarkdown *,
[data-testid="stChatMessage"], [data-testid="stChatMessage"] *,
[data-testid="stChatMessageContent"], [data-testid="stChatMessageContent"] * {
    color: #0f172a !important;
}

/* 예외: 알림 박스(success/info/warning/error) 는 각자 색 유지 */
[data-testid="stAlertContainer"] *,
[data-baseweb="notification"] * {
    color: inherit !important;
}

/* 링크는 색을 유지 */
a, a * { color: #dc2626 !important; }

/* 인용문(>) 은 조금 회색 */
blockquote, blockquote * { color: #475569 !important; }

/* 코드 블록 배경·색상 명시 */
code, pre, code *, pre * {
    color: #0f172a !important;
    background: #f1f5f9 !important;
}

.block-container {
    max-width: 1120px;
    padding-top: 2.2rem;
    padding-bottom: 5rem;
}

[data-testid="stHeader"] {
    background: transparent;
}

[data-testid="stToolbar"] {
    visibility: hidden;
}

#MainMenu {
    visibility: hidden;
}

footer {
    visibility: hidden;
}

h1, h2, h3 {
    letter-spacing: -0.025em;
}

.hero-title {
    font-size: 2.55rem;
    font-weight: 800;
    line-height: 1.15;
    margin-bottom: 0.55rem;
    color: #0f172a;
}

.hero-subtitle {
    font-size: 1.05rem;
    line-height: 1.75;
    color: #64748b;
    margin-bottom: 1.6rem;
}

.section-title {
    font-size: 1.15rem;
    font-weight: 750;
    color: #0f172a;
    margin-top: 0.4rem;
    margin-bottom: 0.6rem;
}

.small-muted {
    color: #64748b;
    font-size: 0.9rem;
}

div[data-testid="stForm"] {
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 18px;
    padding: 1rem 1rem 0.2rem 1rem;
    box-shadow:
        0 8px 25px rgba(15, 23, 42, 0.05);
}

div[data-testid="stTextInput"] input {
    border-radius: 12px;
    min-height: 48px;
}

div.stButton > button {
    border-radius: 11px;
    font-weight: 650;
}

div[data-testid="stMetric"] {
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    padding: 0.7rem 0.9rem;
}

div[data-testid="stExpander"] {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
}

div[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 16px;
}

@media (max-width: 768px) {

    .block-container {
        padding-top: 1.2rem;
    }

    .hero-title {
        font-size: 2rem;
    }

    .hero-subtitle {
        font-size: 0.96rem;
    }
}

</style>
""",
        unsafe_allow_html=True,
    )