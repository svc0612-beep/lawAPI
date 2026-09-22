# ============================================================
# summary_focus.py
#
# 역할
# - 절차형 profile summary에서 후속 질문의 초점 명사에 매칭되는
#   섹션만 추려서 반환하기 위한 유틸리티
#
# 배경
# - profile.summary 안에는 "[협의이혼 절차]", "[재판이혼 절차]",
#   "[함께 정할 사항]" 같은 대괄호 섹션 헤더가 들어 있음
# - 첫 질문("이혼하려면 어떻게?")에서는 전체 요약을 보여줘야 유용하지만,
#   follow-up 질문("재판이혼 위자료는?")에서는 관련 섹션만 노출하는 것이
#   사용자가 실제로 원하는 초점 답변
#
# 동작
# - follow_up=False → 원본 그대로 반환 (리그레션 없음)
# - follow_up=True → 질문의 명사와 섹션 헤더/본문 매칭 → 관련 섹션만 반환
# - 매칭 실패 → 원본 그대로 반환 (안전 fallback)
# ============================================================

import re


# ------------------------------------------------------------
# 초점 명사 후보
#
# - 사용자 질문에서 이런 키워드가 있으면 그것이 focus
# - 값은 매칭할 (섹션·문장에서 찾을) 문자열 목록
# - key와 val을 분리해두면, 사용자가 "위자료"라고 하면 summary 안에서
#   "위자료" 또는 "손해배상"이 있는 섹션도 함께 잡힘
# ------------------------------------------------------------

FOCUS_KEYWORDS = {
    # divorce
    "위자료": ("위자료", "손해배상", "정신적 손해"),
    "재산분할": ("재산분할", "재산 분할", "재산의 분할"),
    "양육": ("양육", "친권", "면접교섭"),
    "친권": ("친권", "양육"),
    "협의이혼": ("협의이혼", "협의상 이혼", "협의 이혼"),
    "재판이혼": ("재판이혼", "재판상 이혼", "재판 이혼", "이혼 소송"),
    "숙려": ("숙려", "숙려기간"),
    "조정": ("조정", "조정전치"),
    # inheritance
    "상속포기": ("상속포기", "포기"),
    "한정승인": ("한정승인",),
    "단순승인": ("단순승인",),
    "유류분": ("유류분",),
    "상속세": ("상속세",),
    "상속등기": ("상속등기", "등기"),
    "상속순위": ("상속 순위", "상속순위", "상속인의 순위"),
    "법정상속분": ("법정상속분", "상속분"),
    "유언": ("유언",),
    "분할협의": ("협의분할", "분할 협의", "심판분할"),
    # constitutional_complaint
    "청구기간": ("청구기간", "청구 기간", "90일", "1년"),
    "보충성": ("보충성",),
    "대리인": ("대리인", "변호사", "국선"),
    "사전심사": ("사전심사", "지정재판부"),
    "본안": ("본안", "전원재판부"),
    "인용": ("인용", "위헌", "효력"),
}


# ------------------------------------------------------------
# 섹션 파서
#
# summary는 대괄호 헤더 [xxx] 로 시작하는 블록의 연쇄로 구성됨
# 예:
#   "일반 도입 문장. [협의이혼 절차] (1)... (2)... [재판이혼 절차] (1)..."
#
# 반환: [(intro_text_or_None, [(header, body), ...]), ...] 구조는 복잡하므로
#       intro (헤더 앞 공통 도입부) 는 별도로 반환
# ------------------------------------------------------------

_SECTION_RE = re.compile(r"\[([^\]]+)\]")


def parse_sections(summary):
    """
    summary 문자열을 (intro, [(header, body), ...])로 분해한다.
    - intro: 첫 [헤더] 이전의 공통 도입부 (없으면 "")
    - sections: 각 섹션의 (헤더, 본문)
    - [헤더]가 하나도 없으면 sections=[], intro=summary 전체
    """
    text = str(summary or "").strip()
    if not text:
        return "", []

    matches = list(_SECTION_RE.finditer(text))

    # 섹션 마커가 없으면 전체가 intro
    if not matches:
        return text, []

    # intro = 첫 매치 이전 부분
    intro = text[: matches[0].start()].strip()

    sections = []
    for i, m in enumerate(matches):
        header = m.group(1).strip()
        body_start = m.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[body_start:body_end].strip()
        sections.append((header, body))

    return intro, sections


# ------------------------------------------------------------
# 초점 명사 추출
#
# 사용자 질문 텍스트에서 FOCUS_KEYWORDS의 key가 등장하는 것을 순서대로
# 수집한다. profile.terms 도 동일한 방식으로 힌트로 활용 가능하도록
# 여분의 term 목록도 받는다.
# ------------------------------------------------------------

def extract_focus_terms(question, extra_terms=()):
    """
    question 안에서 FOCUS_KEYWORDS의 key가 발견되면 그 key의 val 튜플들을
    이어붙인 리스트를 반환.
    - 최소 1개라도 매칭되면 focus 모드
    - 매칭이 0개면 빈 리스트 반환 (호출자는 원본을 그대로 유지)
    """
    q = str(question or "")
    focus = []

    # (a) FOCUS_KEYWORDS 스캔
    for key, values in FOCUS_KEYWORDS.items():
        if key in q:
            for v in values:
                if v not in focus:
                    focus.append(v)

    # (b) 추가 힌트로 profile.terms를 그대로 사용
    for term in extra_terms or ():
        term = str(term).strip()
        if term and term in q and term not in focus:
            focus.append(term)

    return focus


# ------------------------------------------------------------
# 배지 표시용 라벨 추출
#
# extract_focus_terms 는 검색·매칭용이라 유사어를 모두 반환하지만,
# 사용자에게 배지로 보여줄 때는 대표 명사(FOCUS_KEYWORDS의 key)만
# 골라 중복 뉘앙스("재산분할 · 재산 분할") 를 없앤다.
# ------------------------------------------------------------

def focus_labels(question, extra_terms=()):
    """
    질문에서 매칭된 FOCUS_KEYWORDS의 key(대표 명사)만 반환.
    extra_terms 중에 다른 key와 substring 관계가 아닌 것도 포함.
    """
    q = str(question or "")
    labels = []

    # (a) FOCUS_KEYWORDS 의 key 만 (대표 명사)
    for key in FOCUS_KEYWORDS.keys():
        if key in q and key not in labels:
            labels.append(key)

    # (b) profile.terms 추가 힌트 — 이미 있는 라벨의 substring 이면 스킵
    for term in extra_terms or ():
        term = str(term).strip()
        if not term or term in q is False:
            continue
        if term not in q:
            continue
        # 이미 있는 라벨 안에 포함되거나, 라벨을 포함하면 중복
        if any(term in existing or existing in term for existing in labels):
            continue
        labels.append(term)

    return labels


# ------------------------------------------------------------
# 초점 섹션 필터
#
# summary + 사용자 질문 + follow_up 여부를 받아 필터링된 summary를 반환.
# - follow_up=False → 원본 그대로 (첫 질문이므로 전체 요약을 봐야 함)
# - follow_up=True + focus 명사 없음 → 원본 그대로 (안전 fallback)
# - follow_up=True + focus 명사 있음 → intro + 매칭되는 섹션(header 또는 body에
#   focus 명사 포함)만 이어붙여 반환
#
# 매칭된 섹션이 0개면 원본 그대로 반환 (사용자가 정보를 잃지 않도록)
# ------------------------------------------------------------

def focus_summary(summary, question, follow_up=False, extra_terms=()):
    """
    Args:
        summary: profile.summary 원본
        question: 사용자의 현재 질문
        follow_up: 이 질문이 후속 질문인지
        extra_terms: profile.terms 등 추가 초점 명사 후보
    Returns:
        필터링된 summary 문자열
    """
    # follow-up이 아니면 원본 유지 (첫 질문은 전체 요약이 답)
    if not follow_up:
        return summary

    intro, sections = parse_sections(summary)

    # 섹션이 없는 profile은 필터링 대상 아님
    if not sections:
        return summary

    focus = extract_focus_terms(question, extra_terms)
    if not focus:
        return summary

    # 매칭되는 섹션만 선택
    picked = []
    for header, body in sections:
        haystack = header + " " + body
        if any(term in haystack for term in focus):
            picked.append((header, body))

    # 안전장치: 매칭 0개면 원본 유지
    if not picked:
        return summary

    # 재조립
    parts = []
    if intro:
        parts.append(intro)
    for header, body in picked:
        parts.append(f"[{header}] " + body)

    return " ".join(parts).strip()
