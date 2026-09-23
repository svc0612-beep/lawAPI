"""Render the verified multi-turn RAG conversation."""
import streamlit as st


# ============================================================
# profile id → (한국어 라벨, 이모지)
#
# 답변 상단에 어떤 도메인으로 매칭됐는지 chip 형태로 보여준다.
# 이모지는 라이트/다크 두 모드 다 자연스럽게 보이도록 흑백/컬러
# 어느 쪽이든 잘 어울리는 것으로 선택.
# ============================================================
PROFILE_META = {
    # ---- 헌법 ----
    "constitutional_complaint": ("헌법소원", "⚖️"),
    "rights":                   ("기본권",   "🕊️"),

    # ---- 형사 ----
    "drink_driving":            ("음주운전",         "🍺"),
    "unlicensed":               ("무면허운전",       "🚫"),
    "assault":                  ("폭행",             "👊"),
    "online_speech":            ("온라인 명예훼손",  "💬"),
    "fraud":                    ("사기",             "🎭"),
    "theft":                    ("절도",             "🕵️"),
    "sexual_violence":          ("성폭력",           "🚨"),
    "stalking":                 ("스토킹",           "👁️"),
    "child_abuse":              ("아동학대",         "🧒"),
    "school_violence":          ("학교폭력",         "🎒"),
    "drug":                     ("마약",             "💊"),
    "privacy":                  ("개인정보",         "🔐"),

    # ---- 노동·사회보험 ----
    "wages":                    ("임금 체불",        "💰"),
    "dismissal":                ("부당해고",         "📋"),
    "retirement":               ("퇴직금",           "🎁"),
    "minimum_wage":             ("최저임금",         "📊"),
    "workplace_injury":         ("산업재해",         "🩹"),
    "disability_employment":    ("장애인 고용",      "♿"),
    "labor_contract":           ("근로계약",         "📝"),
    "parental_leave":           ("육아휴직",         "🍼"),

    # ---- 민사·소비자 ----
    "refund":                   ("청약철회·환불",    "↩️"),
    "housing_deposit":          ("전세보증금",       "🏠"),
    "loan":                     ("대여금",           "💵"),
    "contract_general":         ("계약 분쟁",        "📄"),
    "debt_collection":          ("채권추심",         "📞"),
    "real_estate_purchase":     ("부동산 매매",      "🏘️"),

    # ---- 가사 ----
    "divorce":                  ("이혼",             "💔"),
    "inheritance":              ("상속",             "🏛️"),

    # ---- 행정 ----
    "administrative":           ("행정심판",         "🗂️"),
    "tax_default":              ("세금 체납",        "🧾"),
    "traffic_fine":             ("교통 과태료·범칙금", "🚦"),

    # ---- 특별·신규 ----
    "patent":                   ("특허",             "💡"),
    "trademark":                ("상표",             "™️"),
    "bankruptcy":               ("회생·파산",        "📉"),
    "real_estate_auction":      ("부동산 경매",      "🔨"),
    "traffic_accident":         ("교통사고",         "🚗"),
    "medical_malpractice":      ("의료사고",         "🏥"),
    "environmental_pollution":  ("환경오염",         "🌱"),
}


# ============================================================
# 하위 호환: 기존 코드가 PROFILE_LABELS 를 import 하는 경우 대비
# ============================================================
PROFILE_LABELS = {pid: meta[0] for pid, meta in PROFILE_META.items()}


# ============================================================
# profile chip HTML 생성
#
# CSS 는 styles.py 가 아니라 이 함수 안에 inline 으로 넣는다.
# → chip 개수·색상을 profile 단위로 다르게 줄 수 있고,
#    라이트/다크 모드 자동 대응이 CSS 변수 없이도 잘 된다.
# ============================================================
def _profile_chips_html(profile_ids: list[str]) -> str:
    """
    profile_id 리스트 → 그라데이션 chip HTML 문자열.
    Streamlit markdown 에 unsafe_allow_html=True 로 넣는다.
    """
    chips = []
    for pid in profile_ids[:3]:
        label, emoji = PROFILE_META.get(pid, (pid, "🏷️"))
        chips.append(
            f"""<span style="
                display: inline-flex;
                align-items: center;
                gap: 6px;
                padding: 5px 12px;
                margin: 0 6px 6px 0;
                border-radius: 999px;
                font-size: 12.5px;
                font-weight: 700;
                color: white;
                background: linear-gradient(135deg, #ec4899, #a855f7);
                box-shadow: 0 2px 8px rgba(168,85,247,0.25);
                white-space: nowrap;
            "><span style="font-size: 14px;">{emoji}</span>{label}</span>"""
        )
    return (
        '<div style="margin: 6px 0 12px 0; line-height: 1.9;">'
        + "".join(chips)
        + "</div>"
    )


# ============================================================
# status → 알림 스타일 매핑
# ============================================================
def _status_style(status: str):
    """status → (스타일, 캡션 텍스트) 튜플."""
    if status == "grounded_excerpt":
        return ("success",
                "공식 원문 검증 통과 · 법률 적용 여부는 별도 검토 필요")
    if status == "context_carryover":
        return ("info",
                "직전 대화의 검증된 요약을 이어 보여드립니다 · "
                "새 조문·판례는 이번 답변에 포함되지 않았습니다")
    if status == "advisory_summary":
        return ("warning",
                "사람이 검토한 정형 요약을 참조로 제시합니다 · "
                "구체 사건 적용은 사실관계 확인 후 판단해야 합니다")
    if status == "temporal_review_required":
        return ("warning",
                "과거 시점의 시행법·개정 부칙을 확인하기 전에는 "
                "결론을 내리지 않습니다.")
    if status in {"clarify", "abstain"}:
        return ("info",
                "근거가 부족하거나 질문 범위가 불명확하여 "
                "답변을 보류했습니다.")
    if status in {"model_error", "verification_failed"}:
        return ("error",
                "Qwen 또는 원문 검증 단계가 실패하여 "
                "내용을 공개하지 않았습니다.")
    return (None, "")


# ============================================================
# 메인 렌더러
# ============================================================
def render_rag_conversation(messages: list[dict]):
    """세션에 쌓인 사용자·AI 메시지들을 순서대로 렌더링."""

    st.subheader("💬 검증형 법률 대화")

    for message in messages:
        role = message.get("role", "assistant")

        with st.chat_message(role):
            # 1) 본문 markdown (AI 답변 또는 사용자 질문)
            st.markdown(message.get("content", ""))

            # 사용자 메시지는 여기서 끝. 이하 로직은 AI 답변에만.
            result = message.get("result") or {}
            if role != "assistant" or not result:
                continue

            status = result.get("status", "")
            diagnostics = result.get("diagnostics", {})
            online = diagnostics.get("online") or {}

            # 2) profile 태그 (chip 배지)
            hint_profiles = online.get("hint_profiles") or []
            if hint_profiles:
                st.markdown(
                    _profile_chips_html(hint_profiles),
                    unsafe_allow_html=True,
                )

            # 3) status 별 시각적 알림 박스
            style, caption = _status_style(status)
            if caption:
                if style == "success":
                    st.success(caption, icon="✅")
                elif style == "info":
                    st.info(caption, icon="ℹ️")
                elif style == "warning":
                    st.warning(caption, icon="⚠️")
                elif style == "error":
                    st.error(caption, icon="❌")
                else:
                    st.caption(caption)

            # 4) 멀티턴 컨텍스트 참조 개수 (있으면)
            history_turns = diagnostics.get("history_user_turns")
            if history_turns:
                st.caption(
                    f"🔗 멀티턴 문맥 {history_turns}개 사용자 발화 참조"
                )
