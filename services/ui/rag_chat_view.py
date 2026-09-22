"""Render the verified multi-turn RAG conversation."""
import streamlit as st


# ============================================================
# profile id → 사용자용 한국어 라벨
# 답변 상단에 어떤 도메인으로 분류됐는지 chip 형태로 표시
# ============================================================
PROFILE_LABELS = {
    # 헌법
    "constitutional_complaint": "헌법소원",
    "rights": "기본권",
    # 형사
    "drink_driving": "음주운전",
    "unlicensed": "무면허운전",
    "assault": "폭행",
    "online_speech": "온라인 명예훼손",
    "fraud": "사기",
    "theft": "절도",
    "sexual_violence": "성폭력",
    "stalking": "스토킹",
    "child_abuse": "아동학대",
    "school_violence": "학교폭력",
    "drug": "마약",
    "privacy": "개인정보",
    # 노동·사회보험
    "wages": "임금 체불",
    "dismissal": "부당해고",
    "retirement": "퇴직금",
    "minimum_wage": "최저임금",
    "workplace_injury": "산업재해",
    "disability_employment": "장애인 고용",
    "labor_contract": "근로계약",
    "parental_leave": "육아휴직",
    # 민사·소비자
    "refund": "청약철회·환불",
    "housing_deposit": "전세보증금",
    "loan": "대여금",
    "contract_general": "계약 분쟁",
    "debt_collection": "채권추심",
    "real_estate_purchase": "부동산 매매",
    # 가사
    "divorce": "이혼",
    "inheritance": "상속",
    # 행정
    "administrative": "행정심판",
    "tax_default": "세금 체납",
    "traffic_fine": "교통 과태료·범칙금",
    # 특별·신규
    "patent": "특허",
    "trademark": "상표",
    "bankruptcy": "회생·파산",
    "real_estate_auction": "부동산 경매",
    "traffic_accident": "교통사고",
    "medical_malpractice": "의료사고",
    "environmental_pollution": "환경오염",
}


def _status_style(status: str):
    """status → (표시 함수, 캡션 텍스트)"""
    if status == "grounded_excerpt":
        return ("success", "공식 원문 검증 통과 · 법률 적용 여부는 별도 검토 필요")
    if status == "context_carryover":
        return ("info", "직전 대화의 검증된 요약을 이어 보여드립니다 · 새 조문·판례는 이번 답변에 포함되지 않았습니다")
    if status == "advisory_summary":
        return ("warning", "사람이 검토한 정형 요약을 참조로 제시합니다 · 구체 사건 적용은 사실관계 확인 후 판단해야 합니다")
    if status == "temporal_review_required":
        return ("warning", "과거 시점의 시행법·개정 부칙을 확인하기 전에는 결론을 내리지 않습니다.")
    if status in {"clarify", "abstain"}:
        return ("info", "근거가 부족하거나 질문 범위가 불명확하여 답변을 보류했습니다.")
    if status in {"model_error", "verification_failed"}:
        return ("error", "Qwen 또는 원문 검증 단계가 실패하여 내용을 공개하지 않았습니다.")
    return (None, "")


def render_rag_conversation(messages: list[dict]):
    st.subheader("검증형 법률 대화")

    for message in messages:
        role = message.get("role", "assistant")
        with st.chat_message(role):
            st.markdown(message.get("content", ""))

            result = message.get("result") or {}
            if role != "assistant" or not result:
                continue

            status = result.get("status", "")
            diagnostics = result.get("diagnostics", {})
            online = diagnostics.get("online") or {}

            # ---- profile 태그 (답변 상단) ----
            hint_profiles = online.get("hint_profiles") or []
            if hint_profiles:
                labels = [PROFILE_LABELS.get(p, p) for p in hint_profiles[:3]]
                st.caption("🏷️ " + " · ".join(labels))

            # ---- status별 스타일 ----
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

            # ---- 멀티턴 문맥 표시 ----
            if diagnostics.get("history_user_turns"):
                st.caption(
                    f"멀티턴 문맥 {diagnostics['history_user_turns']}개 사용자 발화 참조"
                )
