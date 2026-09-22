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
# 2. 스타일
# ============================================================

apply_styles()


# ============================================================
# 3. Session State
# ============================================================

initialize_session_state()


# ============================================================
# 4. 상단 UI (hero + 예시 or 새 주제 버튼)
# ============================================================

render_search_panel_top()


# ============================================================
# 5. 현재 결과 / 대화 이력
# ============================================================

result = st.session_state.get("last_result")
current_question = clean_text(st.session_state.get("last_question", ""))


# ------------------------------------------------------------
# 5-a. 검증형 멀티턴 RAG: 대화 이력 렌더 → chat_input 은 하단
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
# 5-b. 결과 없음 (첫 진입): 안내 + 하단 chat_input
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
