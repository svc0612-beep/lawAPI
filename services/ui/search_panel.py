# ============================================================
# LawMate 검색 UI
#
# 검색 버튼 / Enter / 예시 질문을
# 동일한 검색 흐름으로 처리한다.
#
# 중요:
# Streamlit에서는 이미 생성된 widget key의
# session_state 값을 같은 실행 중 직접 수정하면 안 된다.
#
# 따라서:
#
# 직접 입력
# → question_input 사용
#
# 예시 질문
# → pending_question에 임시 저장
# → rerun
# → text_input 생성 전에 question_input으로 반영
# ============================================================

import streamlit as st
import uuid

from services.query_service import (
    process_law_question,
)

from agents.query_analyzer import analyze_question

from services.rag_chat_service import (
    ask_legal_question,
    create_legal_session,
)

from services.ui.common import (
    clean_text,
)


# ============================================================
# 1. 예시 질문
# ============================================================

EXAMPLE_QUESTIONS = [
    # 가족
    "이혼하려면 어떻게 해야 해?",
    "상속받으면 뭘 먼저 해야 해?",

    # 노동 (장애인 고용 의무 관련 포함)
    "월급 밀렸는데 어디에 신고해?",
    "부당해고 당했는데 어떻게 대응해?",
    "회사가 장애인 고용 안 하면 어떻게 돼?",

    # 형사
    "음주운전 하면 어떤 처벌 받아?",
    "사기 당했는데 어디에 신고하지?",

    # 주거·생활
    "전세보증금 못 받으면 어떻게 해?",
    "층간소음 심할 땐 어디에 신고해?",
]


# ============================================================
# 2. Session State 초기화
# ============================================================

def initialize_session_state():

    if "question_input" not in st.session_state:

        st.session_state[
            "question_input"
        ] = ""

    if "pending_question" not in st.session_state:

        st.session_state[
            "pending_question"
        ] = ""

    if "last_result" not in st.session_state:

        st.session_state[
            "last_result"
        ] = None

    if "last_question" not in st.session_state:

        st.session_state[
            "last_question"
        ] = ""

    if "rag_user_id" not in st.session_state:

        st.session_state["rag_user_id"] = uuid.uuid4().hex

    if "rag_session_id" not in st.session_state:

        st.session_state["rag_session_id"] = ""

    if "rag_messages" not in st.session_state:

        st.session_state["rag_messages"] = []

    if "rag_new_topic" not in st.session_state:

        st.session_state["rag_new_topic"] = False


# ============================================================
# 3. Pending 질문 반영
#
# 반드시 text_input이 생성되기 전에 실행해야 한다.
# ============================================================

def apply_pending_question():

    pending_question = clean_text(
        st.session_state.get(
            "pending_question",
            ""
        )
    )

    if not pending_question:

        return

    # --------------------------------------------------------
    # 이 시점에는 아직 question_input 위젯이
    # 생성되지 않았으므로 안전하게 수정할 수 있다.
    # --------------------------------------------------------

    st.session_state[
        "question_input"
    ] = pending_question

    st.session_state[
        "pending_question"
    ] = ""


# ============================================================
# 4. 검색 실행
#
# 중요:
# 여기서는 question_input 값을 수정하지 않는다.
#
# question_input은 Streamlit text_input widget key이므로
# 위젯 생성 이후 수정하면 오류가 발생할 수 있다.
# ============================================================

def execute_search(
    question: str
):

    question = clean_text(
        question
    )

    if not question:

        return False

    # --------------------------------------------------------
    # 마지막 검색 질문만 저장
    # --------------------------------------------------------

    st.session_state[
        "last_question"
    ] = question

    # --------------------------------------------------------
    # 실제 법률 검색
    # --------------------------------------------------------

    with st.spinner(
        "공식 법률정보를 검색하고 있습니다..."
    ):

        analysis = analyze_question(question)

        # A whole-statute request has a dedicated verified renderer and can be
        # too large for a chat model context.  Every other question uses the
        # same persisted RAG session so follow-ups cannot lose their context.
        if analysis.get("question_type") == "법령_전체조회":

            result = process_law_question(question)

        else:

            user_id = st.session_state["rag_user_id"]
            session_id = st.session_state.get("rag_session_id", "")
            if not session_id:
                session_id = create_legal_session(user_id)
                st.session_state["rag_session_id"] = session_id

            new_topic = bool(st.session_state.get("rag_new_topic"))
            try:
                result = ask_legal_question(
                    user_id,
                    session_id,
                    question,
                    new_topic=new_topic,
                )
            except Exception as error:
                # Database, model and source failures are not legal answers.
                # Do not expose exception bodies because request URLs may
                # contain service credentials.
                result = {
                    "status": "model_error",
                    "question_type": "검증형_RAG_대화",
                    "original_question": question,
                    "answer": (
                        "검증형 검색 과정에 오류가 발생해 답변을 공개하지 않습니다. "
                        "Qwen 연결과 공식 출처 상태를 확인한 뒤 다시 시도해 주세요."
                    ),
                    "citations": [],
                    "verification": {"passed": False},
                    "diagnostics": {
                        "failure": "application_rag_error",
                        "error_type": type(error).__name__,
                    },
                }
                print(f"[RAG ERROR] {type(error).__name__}", flush=True)
            st.session_state["rag_new_topic"] = False
            st.session_state["rag_messages"].extend(
                [
                    {"role": "user", "content": question},
                    {
                        "role": "assistant",
                        "content": result.get("answer", "답변을 생성하지 못했습니다."),
                        "result": result,
                    },
                ]
            )

    # --------------------------------------------------------
    # 검색 결과 저장
    # --------------------------------------------------------

    st.session_state[
        "last_result"
    ] = result

    return True


# ============================================================
# 5. Hero
# ============================================================

def render_hero():

    st.markdown(
        '<div class="hero-title">⚖️ LawMate</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        """
<div class="hero-subtitle">
정확한 법률명을 몰라도 질문할 수 있습니다.<br>
법령 · 판례 · 법령해석례 등 공식 근거를 중심으로 검색합니다.
</div>
""",
        unsafe_allow_html=True,
    )


# ============================================================
# 6. 채팅 입력 (화면 하단 sticky 고정)
#
# st.chat_input 은 Streamlit 이 자동으로 페이지 하단에 붙여준다.
# 사용자는 답변을 읽은 후 위로 스크롤할 필요 없이 곧바로 다음 질문 가능.
# ============================================================

def render_new_topic_button():
    """새 주제 버튼 (대화 중일 때만 눈에 띄게)."""
    if st.button("🔄 새 주제로 시작", key="new_rag_topic", width="stretch"):
        st.session_state["rag_new_topic"] = True
        st.session_state["rag_messages"] = []
        st.session_state["last_result"] = None
        st.session_state["last_question"] = ""
        st.rerun()


def render_search_chat_input():
    """
    하단 sticky 채팅 입력창.
    입력 즉시 execute_search 를 실행하지 않고,
    session_state["_pending_question"] 에 저장 후 rerun 한다.
    실제 실행은 app.py 의 process_pending_question() 에서 담당.
    이렇게 하면:
      1) 사용자 입력 → pending 저장 + is_generating=True + rerun
      2) 새 스크립트 실행에서 토글이 disabled 상태로 렌더링됨
      3) 그 후 process_pending_question 이 실제 응답 처리
    결과: 응답 대기 중 사용자가 토글 눌러도 실행이 중단되지 않음.
    """
    # 응답 처리 중이면 입력 자체를 비활성화 (Streamlit 1.30+ 지원)
    is_busy = st.session_state.get("is_generating", False)
    placeholder = (
        "🔄 답변을 생성하고 있어요..."
        if is_busy
        else "궁금한 법률 내용을 자유롭게 물어보세요"
    )
    user_input = st.chat_input(placeholder, disabled=is_busy)

    if user_input:
        question = clean_text(user_input)
        if question:
            # pending 큐에 넣고 실행 중 플래그 세팅 → rerun
            st.session_state["_pending_question"] = question
            st.session_state["is_generating"] = True
            st.rerun()


def process_pending_question():
    """
    app.py 가 매 스크립트 실행마다 호출.
    _pending_question 이 있으면 실제 검색을 실행하고,
    완료되면 is_generating 을 내리고 rerun 해서 결과를 표시한다.

    이 함수를 호출하는 시점에는 이미 토글 UI 가 렌더링된 뒤이므로
    (is_generating=True 상태로 disabled 처리됨) 사용자가 그동안
    토글을 눌러도 스크립트가 중단되지 않는다.
    """
    pending = st.session_state.pop("_pending_question", None)
    if not pending:
        return

    # 사용자에게 처리 중임을 알리는 스피너
    with st.spinner("공식 법률정보를 검색하고 있어요..."):
        execute_search(pending)

    st.session_state["is_generating"] = False
    st.rerun()


# ============================================================
# 7. 예시 질문
#
# 예시 버튼을 누르는 순간에는 이미
# question_input widget이 만들어져 있다.
#
# 따라서 question_input을 직접 변경하지 않고
# pending_question에 저장한 뒤 rerun한다.
# ============================================================

def render_example_questions():
    """
    예시 질문을 3열 그리드로 렌더링.
    9개 예시를 한 줄에 다 넣으면 텍스트가 잘려서 '...' 처리되기 때문에,
    3개씩 3줄로 나눠 배치한다. 버튼 안 텍스트도 CSS 로 wrap 허용.
    """
    st.caption("💡 예시 질문 — 클릭하면 바로 검색됩니다")

    # 버튼 텍스트가 잘 wrap 되도록 CSS 오버라이드
    # (기본 Streamlit 버튼은 white-space: nowrap 이라 강제 override)
    st.markdown("""
    <style>
    div[data-testid="stButton"] button p {
        white-space: normal !important;
        word-break: keep-all !important;
        line-height: 1.4 !important;
        font-size: 15px !important;
        font-weight: 600 !important;
    }
    div[data-testid="stButton"] button {
        min-height: 64px !important;
        padding: 12px 14px !important;
        text-align: center !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # 3개씩 묶어 그리드 배치
    COLS_PER_ROW = 3
    examples = EXAMPLE_QUESTIONS

    # 예시 개수를 3의 배수로 맞추기 위해 필요한 만큼 반복
    for row_start in range(0, len(examples), COLS_PER_ROW):
        # 한 줄에 3열
        cols = st.columns(COLS_PER_ROW)
        # 이 줄의 3개(마지막 줄은 그보다 적을 수도) 배치
        for offset, example in enumerate(examples[row_start:row_start + COLS_PER_ROW]):
            with cols[offset]:
                if st.button(
                    example,
                    key=f"example_{row_start + offset}",
                    width="stretch",
                ):
                    # pending_question 방식과 통일:
                    # 예시 버튼도 채팅 입력창처럼 pending 큐에 넣는다.
                    st.session_state["_pending_question"] = example
                    st.session_state["is_generating"] = True
                    st.rerun()


# ============================================================
# 8. 검색 패널 (상단부)
#
# 화면 상단: hero + 예시 질문 + 새 주제 버튼
# chat_input 은 별도 함수(render_search_chat_input) 로 하단 노출.
# ============================================================

def render_search_panel_top():
    """상단부: hero + 예시 질문 + 새 주제."""
    apply_pending_question()
    render_hero()

    # 대화 이력이 있으면 예시 대신 새 주제 버튼만 (짧게)
    messages = st.session_state.get("rag_messages", [])
    if messages:
        render_new_topic_button()
    else:
        render_example_questions()


def render_search_panel():
    """레거시 호환 (전체 렌더). 새 app.py 는 top/chat_input 을 따로 부른다."""
    render_search_panel_top()
    render_search_chat_input()
