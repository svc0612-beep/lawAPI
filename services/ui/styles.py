# ============================================================
# LawMate Streamlit 스타일
#
# 두 개의 테마 지원:
#   - light : 밝은 배경 + 다크 네온 포인트 (미니멀 & 세련)
#   - dark  : 다크 네온 그라데이션 (컨셉 C)
#
# 사용 방식:
#   from services.ui.styles import apply_styles
#   apply_styles(mode="dark")   # 또는 "light"
#
# 앱에서는 session_state["theme_mode"] 를 UI 토글로 바꾸고
# apply_styles(mode=st.session_state.get("theme_mode","light")) 로 호출한다.
# ============================================================

import streamlit as st


# ============================================================
# 라이트 모드 CSS
# ============================================================
LIGHT_CSS = """
<style>
/* 1. 전역 */
.stApp {
    background:
        radial-gradient(circle at 15% 20%, rgba(236,72,153,0.05) 0%, transparent 40%),
        radial-gradient(circle at 85% 80%, rgba(168,85,247,0.05) 0%, transparent 40%),
        linear-gradient(180deg, #f7f9fc 0%, #ffffff 100%);
    color: #0f172a; min-height: 100vh;
}
.block-container { max-width: 1120px; padding-top: 2rem; padding-bottom: 5rem; }
[data-testid="stHeader"] { background: transparent; }
[data-testid="stToolbar"] { visibility: hidden; }
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }

/* 2. Hero */
.hero-title {
    font-size: 3rem; font-weight: 800; line-height: 1.15;
    letter-spacing: -0.03em; margin-bottom: 0.5rem;
    background: linear-gradient(135deg, #f43f5e 0%, #a855f7 50%, #06b6d4 100%);
    -webkit-background-clip: text; background-clip: text;
    -webkit-text-fill-color: transparent; color: transparent;
}
.hero-subtitle { font-size: 1.05rem; line-height: 1.7; color: #64748b; margin-bottom: 1.6rem; }

/* 3. 헤딩 */
h1, h2, h3 { color: #0f172a; letter-spacing: -0.02em; }
.stMarkdown h3 {
    position: relative; padding-left: 12px;
    margin-top: 1.3rem !important; margin-bottom: 0.6rem !important;
    color: #0f172a !important;
}
.stMarkdown h3::before {
    content: ""; position: absolute; left: 0; top: 0.3rem; bottom: 0.3rem;
    width: 3px; border-radius: 2px;
    background: linear-gradient(180deg, #ec4899, #a855f7);
}

/* 4. 인용 */
blockquote {
    background: rgba(59,130,246,0.06) !important;
    border-left: 3px solid #3b82f6 !important;
    border-radius: 6px !important; padding: 10px 14px !important;
    margin: 8px 0 !important; color: #1e40af !important;
}
blockquote * { color: #1e3a8a !important; }

/* 5. 링크 */
a, a:visited { color: #ec4899 !important; text-decoration: none; font-weight: 500; }
a:hover { color: #db2777 !important; text-decoration: underline; }

/* 6. 코드 */
code, pre { background: #f1f5f9 !important; color: #0f172a !important; border-radius: 4px; }

/* 7. 채팅 메시지 */
[data-testid="stChatMessage"] {
    background: white !important; border: 1px solid #e2e8f0 !important;
    border-radius: 12px !important; padding: 14px 18px !important;
    margin-bottom: 12px !important;
    box-shadow: 0 2px 8px rgba(15,23,42,0.04);
}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
    background: linear-gradient(90deg, rgba(236,72,153,0.08), rgba(236,72,153,0.02)) !important;
    border-color: rgba(236,72,153,0.2) !important;
}
[data-testid="stChatMessage"] p, [data-testid="stChatMessage"] li { color: #0f172a !important; }

/* 8. 입력창 (라이트) — 더 크고 눈에 띄게 */
/* 하단 sticky 컨테이너 전체 (모든 하위 요소 포함) */
[data-testid="stChatInput"],
[data-testid="stChatInput"] > *,
[data-testid="stChatInputContainer"],
[data-testid="stBottomBlockContainer"] {
    background: rgba(255,255,255,0.98) !important;
    backdrop-filter: blur(10px);
}
/* 상단 경계선: 마젠타 그라데이션으로 눈길 끌기 */
[data-testid="stChatInput"] {
    border-top: 2px solid transparent !important;
    border-image: linear-gradient(90deg, transparent, #ec4899, transparent) 1 !important;
    padding: 14px 8px !important;
}
/* 입력창 자체: 크게, 마젠타 테두리, 글로우 */
[data-testid="stChatInput"] textarea,
[data-testid="stChatInput"] div[data-baseweb="textarea"] {
    background: white !important;
    border: 2px solid #ec4899 !important;
    color: #0f172a !important;
    border-radius: 14px !important;
    min-height: 60px !important;
    font-size: 15px !important;
    padding: 14px 18px !important;
    box-shadow: 0 4px 16px rgba(236,72,153,0.15), 0 0 0 4px rgba(236,72,153,0.06) !important;
}
[data-testid="stChatInput"] textarea::placeholder {
    color: #94a3b8 !important;
    font-weight: 500;
}
[data-testid="stChatInput"] textarea:focus {
    border-color: #db2777 !important;
    box-shadow: 0 4px 20px rgba(236,72,153,0.25), 0 0 0 4px rgba(236,72,153,0.12) !important;
    outline: none !important;
}
/* 전송 버튼 (오른쪽 화살표) */
[data-testid="stChatInput"] button {
    background: linear-gradient(135deg, #ec4899, #a855f7) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
}

/* 9. 버튼 */
div.stButton > button {
    background: white; color: #0f172a; border: 1px solid #cbd5e1;
    border-radius: 10px; font-weight: 600; padding: 8px 14px;
    transition: all 0.15s ease;
}
div.stButton > button:hover {
    background: rgba(236,72,153,0.08); border-color: #ec4899;
    color: #ec4899; transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(236,72,153,0.15);
}

/* 10. 알림 (라이트) */
[data-testid="stAlertContainer"] {
    background: white !important; border: 1px solid #e2e8f0 !important;
    border-left-width: 3px !important; border-radius: 8px !important;
    padding: 10px 14px !important;
}
[data-testid="stAlertContainer"]:has([data-testid="stAlertContentSuccess"]) {
    border-left-color: #10b981 !important; background: #ecfdf5 !important;
}
[data-testid="stAlertContentSuccess"] { color: #065f46 !important; }
[data-testid="stAlertContainer"]:has([data-testid="stAlertContentInfo"]) {
    border-left-color: #3b82f6 !important; background: #eff6ff !important;
}
[data-testid="stAlertContentInfo"] { color: #1e40af !important; }
[data-testid="stAlertContainer"]:has([data-testid="stAlertContentWarning"]) {
    border-left-color: #f59e0b !important; background: #fffbeb !important;
}
[data-testid="stAlertContentWarning"] { color: #92400e !important; }
[data-testid="stAlertContainer"]:has([data-testid="stAlertContentError"]) {
    border-left-color: #ef4444 !important; background: #fef2f2 !important;
}
[data-testid="stAlertContentError"] { color: #991b1b !important; }

/* 11. Caption */
[data-testid="stCaptionContainer"], .stCaption { color: #64748b !important; font-size: 0.85rem !important; }

/* 12. Divider */
hr {
    border: none !important; height: 1px !important;
    background: linear-gradient(90deg, transparent, rgba(236,72,153,0.3), transparent) !important;
    margin: 1.5rem 0 !important;
}


/* 14. 전반 폰트 크기 up (사용자 요청) */
.stApp { font-size: 16px !important; }
.stMarkdown p, .stMarkdown li, .stMarkdown span {
    font-size: 15.5px !important;
    line-height: 1.72 !important;
    color: #0f172a !important;
}
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li {
    font-size: 15.5px !important;
    line-height: 1.72 !important;
}
[data-testid="stCaptionContainer"], .stCaption {
    font-size: 13.5px !important;
}
h1 { font-size: 2.2rem !important; }
h2 { font-size: 1.6rem !important; }
h3, .stMarkdown h3 { font-size: 1.15rem !important; font-weight: 700 !important; }
/* 채팅 메시지 안 텍스트 */
[data-testid="stChatMessage"] p,
[data-testid="stChatMessage"] li {
    font-size: 15.5px !important;
    line-height: 1.72 !important;
}
/* 알림 박스 안 텍스트 */
[data-testid="stAlertContainer"] p,
[data-testid="stAlertContainer"] div {
    font-size: 14px !important;
    line-height: 1.55 !important;
}

/* 13. 모바일 */
@media (max-width: 768px) {
    .block-container { padding: 1rem 0.8rem 5rem; }
    .hero-title { font-size: 2.2rem; }
    .hero-subtitle { font-size: 0.95rem; }
    [data-testid="stChatMessage"] { padding: 12px 14px !important; }
}
</style>
"""


# ============================================================
# 다크 모드 CSS
# ============================================================
DARK_CSS = """
<style>
/* 1. 전역 */
.stApp {
    background:
        radial-gradient(circle at 15% 20%, rgba(168,85,247,0.08) 0%, transparent 40%),
        radial-gradient(circle at 85% 80%, rgba(236,72,153,0.08) 0%, transparent 40%),
        linear-gradient(180deg, #0a0a15 0%, #0f0f1e 100%);
    color: #e5e7eb; min-height: 100vh;
}
.block-container { max-width: 1120px; padding-top: 2rem; padding-bottom: 5rem; }
[data-testid="stHeader"] { background: transparent; }
[data-testid="stToolbar"] { visibility: hidden; }
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }

/* 2. Hero */
.hero-title {
    font-size: 3rem; font-weight: 800; line-height: 1.15;
    letter-spacing: -0.03em; margin-bottom: 0.5rem;
    background: linear-gradient(135deg, #f43f5e 0%, #a855f7 50%, #06b6d4 100%);
    -webkit-background-clip: text; background-clip: text;
    -webkit-text-fill-color: transparent; color: transparent;
}
.hero-subtitle { font-size: 1.05rem; line-height: 1.7; color: #94a3b8; margin-bottom: 1.6rem; }

/* 3. 헤딩 */
h1, h2, h3 { color: #f3f4f6; letter-spacing: -0.02em; }
.stMarkdown h3 {
    position: relative; padding-left: 12px;
    margin-top: 1.3rem !important; margin-bottom: 0.6rem !important;
    color: #f3f4f6 !important;
}
.stMarkdown h3::before {
    content: ""; position: absolute; left: 0; top: 0.3rem; bottom: 0.3rem;
    width: 3px; border-radius: 2px;
    background: linear-gradient(180deg, #ec4899, #a855f7);
}

/* 4. 인용 */
blockquote {
    background: rgba(59,130,246,0.08) !important;
    border-left: 3px solid #3b82f6 !important;
    border-radius: 6px !important; padding: 10px 14px !important;
    margin: 8px 0 !important; color: #93c5fd !important;
}
blockquote * { color: #dbeafe !important; }

/* 5. 링크 */
a, a:visited { color: #ec4899 !important; text-decoration: none; font-weight: 500; }
a:hover { color: #f9a8d4 !important; text-decoration: underline; }

/* 6. 코드 */
code, pre { background: rgba(255,255,255,0.06) !important; color: #e5e7eb !important; border-radius: 4px; }

/* 7. 채팅 메시지 */
[data-testid="stChatMessage"] {
    background: rgba(255,255,255,0.03) !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 12px !important; padding: 14px 18px !important;
    margin-bottom: 12px !important;
}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
    background: linear-gradient(90deg, rgba(244,63,94,0.10), rgba(244,63,94,0.03)) !important;
    border-color: rgba(244,63,94,0.25) !important;
}
[data-testid="stChatMessage"] p, [data-testid="stChatMessage"] li { color: #e5e7eb !important; }

/* 8. 입력창 (다크) — 더 크고 눈에 띄게 */
/* 하단 sticky 컨테이너 & 모든 하위 요소를 다크 톤으로 */
[data-testid="stChatInput"],
[data-testid="stChatInput"] > *,
[data-testid="stChatInputContainer"],
[data-testid="stBottomBlockContainer"] {
    background: rgba(10,10,21,0.98) !important;
    backdrop-filter: blur(10px);
}
/* 상단 경계선: 네온 그라데이션 */
[data-testid="stChatInput"] {
    border-top: 2px solid transparent !important;
    border-image: linear-gradient(90deg, transparent, #a855f7, #ec4899, transparent) 1 !important;
    padding: 14px 8px !important;
}
/* 입력창 자체: 크게, 네온 테두리, 글로우 */
[data-testid="stChatInput"] textarea,
[data-testid="stChatInput"] div[data-baseweb="textarea"] {
    background: rgba(255,255,255,0.06) !important;
    border: 2px solid #a855f7 !important;
    color: #f3f4f6 !important;
    border-radius: 14px !important;
    min-height: 60px !important;
    font-size: 15px !important;
    padding: 14px 18px !important;
    box-shadow: 0 4px 16px rgba(168,85,247,0.25), 0 0 0 4px rgba(168,85,247,0.08) !important;
}
[data-testid="stChatInput"] textarea::placeholder {
    color: #cbd5e1 !important;
    font-weight: 500;
}
[data-testid="stChatInput"] textarea:focus {
    border-color: #ec4899 !important;
    box-shadow: 0 4px 24px rgba(236,72,153,0.35), 0 0 0 4px rgba(236,72,153,0.15) !important;
    outline: none !important;
}
/* 전송 버튼 */
[data-testid="stChatInput"] button {
    background: linear-gradient(135deg, #ec4899, #a855f7) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    box-shadow: 0 0 12px rgba(236,72,153,0.3);
}

/* 9. 버튼 */
div.stButton > button {
    background: rgba(168,85,247,0.15); color: #e5e7eb;
    border: 1px solid rgba(168,85,247,0.3); border-radius: 10px;
    font-weight: 600; padding: 8px 14px; transition: all 0.15s ease;
}
div.stButton > button:hover {
    background: rgba(168,85,247,0.25); border-color: rgba(168,85,247,0.5);
    color: white; transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(168,85,247,0.2);
}

/* 10. 알림 (다크) */
[data-testid="stAlertContainer"] {
    background: rgba(255,255,255,0.04) !important;
    border-radius: 8px !important; padding: 10px 14px !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-left-width: 3px !important;
}
[data-testid="stAlertContainer"]:has([data-testid="stAlertContentSuccess"]) {
    border-left-color: #06b6d4 !important; background: rgba(6,182,212,0.08) !important;
}
[data-testid="stAlertContentSuccess"] { color: #67e8f9 !important; }
[data-testid="stAlertContainer"]:has([data-testid="stAlertContentInfo"]) {
    border-left-color: #a855f7 !important; background: rgba(168,85,247,0.08) !important;
}
[data-testid="stAlertContentInfo"] { color: #c4b5fd !important; }
[data-testid="stAlertContainer"]:has([data-testid="stAlertContentWarning"]) {
    border-left-color: #f59e0b !important; background: rgba(245,158,11,0.08) !important;
}
[data-testid="stAlertContentWarning"] { color: #fcd34d !important; }
[data-testid="stAlertContainer"]:has([data-testid="stAlertContentError"]) {
    border-left-color: #f43f5e !important; background: rgba(244,63,94,0.08) !important;
}
[data-testid="stAlertContentError"] { color: #fda4af !important; }

/* 11. Caption */
[data-testid="stCaptionContainer"], .stCaption { color: #94a3b8 !important; font-size: 0.85rem !important; }

/* 12. Divider */
hr {
    border: none !important; height: 1px !important;
    background: linear-gradient(90deg, transparent, rgba(168,85,247,0.3), transparent) !important;
    margin: 1.5rem 0 !important;
}


/* 14. 전반 폰트 크기 up (사용자 요청) */
.stApp { font-size: 16px !important; }
.stMarkdown p, .stMarkdown li, .stMarkdown span {
    font-size: 15.5px !important;
    line-height: 1.72 !important;
    color: #e5e7eb !important;
}
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li {
    font-size: 15.5px !important;
    line-height: 1.72 !important;
}
[data-testid="stCaptionContainer"], .stCaption {
    font-size: 13.5px !important;
}
h1 { font-size: 2.2rem !important; }
h2 { font-size: 1.6rem !important; }
h3, .stMarkdown h3 { font-size: 1.15rem !important; font-weight: 700 !important; }
/* 채팅 메시지 안 텍스트 */
[data-testid="stChatMessage"] p,
[data-testid="stChatMessage"] li {
    font-size: 15.5px !important;
    line-height: 1.72 !important;
}
/* 알림 박스 안 텍스트 */
[data-testid="stAlertContainer"] p,
[data-testid="stAlertContainer"] div {
    font-size: 14px !important;
    line-height: 1.55 !important;
}

/* 13. 모바일 */
@media (max-width: 768px) {
    .block-container { padding: 1rem 0.8rem 5rem; }
    .hero-title { font-size: 2.2rem; }
    .hero-subtitle { font-size: 0.95rem; }
    [data-testid="stChatMessage"] { padding: 12px 14px !important; }
}
</style>
"""


# ============================================================
# 폰트 사이즈 배율 CSS 생성기
#
# 사용자가 UI 에서 폰트 배율(0.85~1.35)을 선택하면 그 값에 따라
# 페이지의 모든 텍스트 크기를 계산한 CSS 를 리턴한다.
# 시각 접근성을 위해 별도 함수로 분리 — apply_styles 뒤에 주입돼
# 라이트/다크 CSS 의 폰트 사이즈를 덮어씌운다.
# ============================================================
def font_scale_css(scale: float = 1.0) -> str:
    """
    폰트 배율을 반영한 CSS 문자열 생성.
    scale=1.0 은 기본, 1.35 는 매우 크게, 0.85 는 매우 작게.
    """
    return f"""
<style>
/* 사용자 폰트 배율 — 페이지 전체 텍스트 크기 통제 */
.stApp {{ font-size: {16 * scale:.1f}px !important; }}

/* markdown 본문 */
.stMarkdown p, .stMarkdown li, .stMarkdown span,
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li {{
    font-size: {15.5 * scale:.1f}px !important;
    line-height: 1.72 !important;
}}

/* 채팅 메시지 내부 텍스트 */
[data-testid="stChatMessage"] p,
[data-testid="stChatMessage"] li {{
    font-size: {15.5 * scale:.1f}px !important;
    line-height: 1.72 !important;
}}

/* Caption (작은 회색 텍스트) */
[data-testid="stCaptionContainer"], .stCaption {{
    font-size: {13.5 * scale:.1f}px !important;
}}

/* 알림 박스 (success/info/warning/error) */
[data-testid="stAlertContainer"] p,
[data-testid="stAlertContainer"] div {{
    font-size: {14 * scale:.1f}px !important;
}}

/* 예시 버튼 텍스트 */
div[data-testid="stButton"] button p {{
    font-size: {15 * scale:.1f}px !important;
}}

/* 채팅 입력창 */
[data-testid="stChatInput"] textarea {{
    font-size: {15 * scale:.1f}px !important;
}}

/* 헤딩 */
h1 {{ font-size: {2.2 * scale:.2f}rem !important; }}
h2 {{ font-size: {1.6 * scale:.2f}rem !important; }}
h3, .stMarkdown h3 {{ font-size: {1.15 * scale:.2f}rem !important; }}

/* Hero */
.hero-title {{ font-size: {3.0 * scale:.2f}rem !important; }}
.hero-subtitle {{ font-size: {1.05 * scale:.2f}rem !important; }}

/* Select box(폰트 조절 위젯 자체) 안 텍스트 */
[data-baseweb="select"] {{ font-size: {14 * scale:.1f}px !important; }}
</style>
"""


# ============================================================
# 진입 함수: 선택된 mode 와 scale 에 맞는 CSS 를 주입
# ============================================================
def apply_styles(mode: str = "light", scale: float = 1.0):
    """
    선택된 테마 CSS + 폰트 배율 CSS 를 페이지에 주입한다.
    mode: "light" 또는 "dark".
    scale: 폰트 배율 (기본 1.0). 시각 접근성을 위한 사용자 조절값.
    """
    # 1) 라이트/다크 기본 CSS
    css = DARK_CSS if mode == "dark" else LIGHT_CSS
    st.markdown(css, unsafe_allow_html=True)

    # 2) 폰트 배율 CSS 를 뒤에 주입 → 기본 CSS 의 폰트 사이즈를 덮어씀
    st.markdown(font_scale_css(scale), unsafe_allow_html=True)
