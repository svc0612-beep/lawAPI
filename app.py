# ============================================================
# LawMate Streamlit App
#
# 핵심 기능
# 1. 자유로운 법률 질문
# 2. Enter / 검색 버튼
# 3. 예시 질문
# 4. 특정 조문 조회
# 5. 관련 법령 탐색
# 6. 판례 / 법령해석례
# 7. 법령 전체 전문
# 8. 대형 법령 pagination
#
# 중요 원칙
# - 검색 힌트는 후보이며 실제 법령 원문을 재확인함
# - 기본 사용자 답변에서 LLM 사용하지 않음
# - 공식 Evidence 중심
# ============================================================

import streamlit as st

from services.ui.common import (
    clean_text,
)

from services.ui.styles import (
    apply_styles,
)

from services.ui.search_panel import (
    initialize_session_state,
    render_search_panel_top,
    render_search_chat_input,
    process_pending_question,
)

from services.ui.full_law_view import (
    render_full_law_view,
)

from services.ui.result_view import (
    render_result_header,
    render_general_result,
)

from services.ui.rag_chat_view import (
    render_rag_conversation,
)


# ============================================================
# 1. 페이지 설정
# ============================================================

st.set_page_config(

    page_title="LawMate",

    page_icon="⚖️",

    layout="wide",

    initial_sidebar_state="collapsed",
)


# ============================================================
# 2. Session State (스타일보다 먼저 초기화해야 mode 참조 가능)
# ============================================================

initialize_session_state()

# theme_mode 가 없으면 라이트로 초기화
if "theme_mode" not in st.session_state:
    st.session_state["theme_mode"] = "light"

# font_scale 이 없으면 기본(1.0) 으로 초기화
# 시각 접근성을 위해 사용자가 UI 에서 조절 가능
if "font_scale" not in st.session_state:
    st.session_state["font_scale"] = 1.0


# ============================================================
# 3. 스타일 (현재 mode + font_scale 에 맞는 CSS 주입)
# ============================================================

apply_styles(
    mode=st.session_state["theme_mode"],
    scale=st.session_state["font_scale"],
)


# ============================================================
# 4. 상단 UI 위젯 (폰트 크기 + 테마 토글)
#
# 시각 접근성:
#   - 왼쪽 select box 로 폰트 크기 5단계 조절 가능
#   - 사용자가 선택하면 페이지 전체 텍스트가 그 배율로 재렌더링
#
# 응답 생성 중(is_generating=True)에는 두 위젯 모두 disabled 로
# 두어 사용자가 실수로 조작해서 스크립트를 중단시키지 못하게 함.
# ============================================================

_is_generating = st.session_state.get("is_generating", False)

# 폰트 크기 5단계 매핑 (배율)
FONT_OPTIONS = {
    "🔍 작게":       0.85,
    "🔎 조금 작게":  0.95,
    "📖 기본":       1.00,
    "🔠 조금 크게":  1.15,
    "🔎+ 크게":      1.35,
}
# 현재 값 → 라벨 역매핑
_current_scale = st.session_state["font_scale"]
_current_label = next(
    (label for label, val in FONT_OPTIONS.items() if abs(val - _current_scale) < 0.01),
    "📖 기본",
)

# 3열: [빈 여백] [폰트 크기] [🌙 토글]
_col_spacer, _col_font, _col_toggle = st.columns([6, 3, 1])

# --- 폰트 크기 select ---
with _col_font:
    _picked_label = st.selectbox(
        "폰트 크기",
        options=list(FONT_OPTIONS.keys()),
        index=list(FONT_OPTIONS.keys()).index(_current_label),
        key="font_size_select",
        label_visibility="collapsed",
        disabled=_is_generating,
        help=(
            "응답 생성 중에는 잠시만 기다려주세요"
            if _is_generating
            else "페이지 전체 폰트 크기를 조절합니다"
        ),
    )
    _picked_scale = FONT_OPTIONS[_picked_label]
    # 변경됐으면 저장 후 rerun 해서 전체 재렌더링
    if abs(_picked_scale - _current_scale) > 0.01:
        st.session_state["font_scale"] = _picked_scale
        st.rerun()

# --- 다크/라이트 토글 ---
with _col_toggle:
    _current_mode = st.session_state["theme_mode"]
    _next_mode = "dark" if _current_mode == "light" else "light"
    _icon = "🌙" if _current_mode == "light" else "☀️"
    _help = (
        "응답 생성 중에는 잠시만 기다려주세요"
        if _is_generating
        else ("다크 모드로" if _current_mode == "light" else "라이트 모드로")
    )

    if st.button(
        _icon,
        key="theme_toggle_btn",
        help=_help,
        width="stretch",
        disabled=_is_generating,
    ):
        st.session_state["theme_mode"] = _next_mode
        st.rerun()


# ============================================================
# 5. 상단 UI (hero + 예시 or 새 주제 버튼)
# ============================================================

render_search_panel_top()


# ============================================================
# 6. Pending 질문 처리
#
# render_search_chat_input 에서 입력받은 질문은 _pending_question
# 에 저장만 되고, 실제 실행은 여기서 한다. 이 시점에는 이미
# 토글이 disabled 상태로 렌더링됐으므로, 응답 대기 중 사용자가
# 토글을 눌러도 스크립트가 중단되지 않는다.
# ============================================================

process_pending_question()


# ============================================================
# 7. 현재 결과 / 대화 이력
# ============================================================

result = st.session_state.get("last_result")
current_question = clean_text(st.session_state.get("last_question", ""))


# ------------------------------------------------------------
# 7-a. 검증형 멀티턴 RAG: 대화 이력 렌더 → chat_input 은 하단
# ------------------------------------------------------------
if result and result.get("question_type") == "검증형_RAG_대화":

    render_rag_conversation(
        st.session_state.get("rag_messages", [])
    )

    st.divider()
    st.caption(
        "Qwen은 검색계획과 근거 선택에만 사용됩니다. 화면에 공개되는 법률 내용은 "
        "공식 원문 단위 검증을 통과한 경우로 제한되며, 구체적 사건의 적용 결론은 별도 검토가 필요합니다."
    )

    # 하단 sticky chat_input
    render_search_chat_input()
    st.stop()


# ------------------------------------------------------------
# 7-b. 결과 없음 (첫 진입): 안내 + 하단 chat_input
# ------------------------------------------------------------
if not result:
    st.info("💬 아래 입력창에 궁금한 법률 내용을 자유롭게 물어보세요. 예시 버튼을 눌러 바로 시작할 수도 있어요.")
    render_search_chat_input()
    st.stop()


# ============================================================
# 7. 오류 처리
# ============================================================

status = result.get(
    "status",
    ""
)


if status == "error":

    st.error(
        result.get(
            "message",
            "검색 중 오류가 발생했습니다."
        )
    )

    st.stop()


if status == "not_implemented":

    st.warning(
        result.get(
            "message",
            "현재 처리하지 못하는 질문 유형입니다."
        )
    )

    st.stop()


# ============================================================
# 7. 검색 메타데이터
# ============================================================

render_result_header(

    result=result,

    current_question=current_question
)


# ============================================================
# 8. 질문 유형
# ============================================================

question_type = clean_text(
    result.get(
        "question_type"
    )
)


# ============================================================
# 9. 법령 전체조회
# ============================================================

if question_type == "법령_전체조회":

    render_full_law_view(
        result
    )


# ============================================================
# 10. 일반 검색
# ============================================================

else:

    render_general_result(
        result
    )


# ============================================================
# 11. 하단 안내
# ============================================================

st.divider()

st.caption(
    (
        "LawMate는 공식 법령정보를 찾아 정리하는 정보 검색 도구입니다. "
        "구체적인 사건에 대한 최종 법률 판단이나 법률대리 서비스를 제공하지 않습니다."
    )
)
