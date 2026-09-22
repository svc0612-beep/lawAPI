# ============================================================
# Legal Statement Selector
#
# 역할:
# - 이미 선택된 조문 안에서 사용자에게 보여줄 핵심 항/문장을 선택
# - 특정 법령명/조문번호 하드코딩 금지
# - 공식 조문 원문만 사용
# - 구조화된 조문 참조와 질문 관련성을 함께 사용
# ============================================================

import re
from typing import Any, Dict, Iterable, List, Optional, Set

from services.evidence.legal_reference_parser import extract_legal_references


# ============================================================
# 1. Category
# ============================================================

DIRECT_CONSEQUENCE = "direct_consequence"
DOWNSTREAM_CONSEQUENCE = "downstream_consequence"
CONDITIONAL_SANCTION = "conditional_sanction"


# ============================================================
# 2. 점수용 표현
# ============================================================

DIRECT_TRIGGER_TERMS = (
    "못 미치는", "미달", "충족하지",
    "위반한", "위반하는", "위반하여",
    "침해한", "침해하는", "침해하여", "침해하였",
    "하지 아니한", "하지 아니하였", "하지 않은",
)

DIRECT_EFFECT_TERMS = (
    "부담금을 납부하여야", "부담금을 납부해야",
    "손해를 배상하여야", "손해배상",
    "손해의 배상을 청구할 수 있다", "배상을 청구할 수 있다",
    "배상하여야", "반환하여야", "지급하여야",
    "징역", "벌금", "처한다",
)

DIRECT_SCOPE_TERMS = (
    "사업주", "사용자", "근로자", "사업자", "법인",
    "제외한다", "미만", "이상",
)

DIRECT_PROCEDURE_TERMS = (
    "신고하고", "신고하여야", "신고해야", "신고를 하여야",
    "산출에 필요한", "다음 연도", "납부 기한", "납부기한",
    "수정신고", "징수 통지서", "통지하여야",
)

DOWNSTREAM_EFFECT_TERMS = (
    "가산금", "연체금", "독촉", "체납처분",
    "압류", "공매", "징수할 수 있다",
)

DOWNSTREAM_POSITIVE_TERMS = (
    "징수한다", "징수하여야", "징수할 수 있다",
    "가산하여", "가산한 금액", "연체금을 징수",
    "독촉하여야", "납부 기한", "체납처분의 예에 따라 징수",
    "부과할 수 있다", "부과한다",
)

PRIMARY_ADVERSE_EFFECT_TERMS = (
    "과징금", "과태료", "부담금",
    "손해배상", "배상을 청구", "징역", "벌금",
)

COLLECTION_ONLY_TERMS = (
    "독촉", "체납", "강제징수", "가산금", "연체금", "환급",
)

EXCEPTION_TERMS = (
    "징수하지 아니한다", "부과하지 아니한다", "적용하지 아니한다",
    "납부하지 아니하여도", "면제한다", "면제할 수 있다",
    "예외로 한다", "소액이거나", "징수가 적절하지 아니하다고",
)

SANCTION_TERMS = ("과태료", "벌금", "징역", "처한다")

PROCEDURAL_SANCTION_TERMS = (
    "부과ㆍ징수한다", "부과·징수한다", "부과하고 징수한다",
    "대통령령으로 정하는 바에 따라", "과태료는",
)


# ============================================================
# 3. 기본 유틸
# ============================================================

def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def get_article_text(article: Dict[str, Any]) -> str:
    if not isinstance(article, dict):
        return ""
    return clean_text(
        article.get("full_text")
        or article.get("article_text")
        or article.get("article_content")
    )


def get_article_title(article: Dict[str, Any]) -> str:
    if not isinstance(article, dict):
        return ""
    return clean_text(article.get("article_title"))


# ============================================================
# 4. 조문 단위 분리
# ============================================================

PARAGRAPH_MARKS = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳"


def split_article_units(article_text: str) -> List[str]:
    article_text = clean_text(article_text)
    if not article_text:
        return []

    marked = re.sub(rf"(?=[{PARAGRAPH_MARKS}])", "\n", article_text)
    parts = [clean_text(item) for item in marked.split("\n") if clean_text(item)]

    if any(re.match(rf"^[{PARAGRAPH_MARKS}]", item) for item in parts):
        return parts

    sentence_parts = re.split(r"(?<=[.!?])\s+", article_text)
    results: List[str] = []
    for item in sentence_parts:
        item = clean_text(item)
        if item and item not in results:
            results.append(item)
    return results


def is_header_only_unit(unit: str, article_title: str = "") -> bool:
    unit = clean_text(unit)
    title = clean_text(article_title)
    if not unit:
        return True

    if len(unit) <= 25 and "제" in unit and "조" in unit:
        return True

    if re.fullmatch(r"제\s*\d+\s*조(?:의\s*\d+)?\s*\([^)]*\)", unit):
        return True

    if title:
        normalized_unit = re.sub(r"\s+", "", unit)
        normalized_title = re.sub(r"\s+", "", title)
        if (
            normalized_title
            and normalized_title in normalized_unit
            and len(normalized_unit) <= len(normalized_title) + 15
        ):
            return True

    return False


# ============================================================
# 5. 표현/참조 유틸
# ============================================================

def count_terms(text: str, terms: Iterable[str]) -> int:
    text = clean_text(text)
    return sum(1 for term in terms if term in text)


def extract_reference_numbers(text: str) -> Set[int]:
    results: Set[int] = set()
    for reference in extract_legal_references(text=text):
        number = safe_int(reference.get("article_number"), 0)
        if number > 0:
            results.add(number)
    return results


def has_specific_reference(text: str) -> bool:
    for reference in extract_legal_references(text=text):
        if (
            safe_int(reference.get("sub_article_number"), 0) > 0
            or safe_int(reference.get("paragraph_number"), 0) > 0
            or safe_int(reference.get("item_number"), 0) > 0
        ):
            return True
    return False


# ============================================================
# 6. 질문 관련성
# ============================================================

QUESTION_STOP_WORDS = {
    "관련", "대한", "대해", "알려줘", "뭐야",
    "하면", "안하면", "안", "어떻게", "어떻게돼",
    "회사", "회사에서", "경우",
}


def extract_question_tokens(question: str) -> List[str]:
    raw_tokens = re.findall(r"[가-힣A-Za-z0-9]+", clean_text(question).lower())
    results: List[str] = []
    for token in raw_tokens:
        if len(token) < 2 or token in QUESTION_STOP_WORDS:
            continue
        if token not in results:
            results.append(token)
    return results


def count_question_matches(question: str, text: str) -> int:
    target = clean_text(text).lower()
    return sum(1 for token in extract_question_tokens(question) if token in target)


# ============================================================
# 7. Unit 점수
# ============================================================

def score_unit(
    unit: str,
    question: str = "",
    effect_category: str = "",
    related_article_numbers: Optional[Iterable[int]] = None,
    article_title: str = "",
) -> float:
    unit = clean_text(unit)

    if not unit:
        return -1000.0

    if is_header_only_unit(unit=unit, article_title=article_title):
        return -500.0

    score = 0.0

    target_numbers = {
        safe_int(number, 0)
        for number in (related_article_numbers or [])
        if safe_int(number, 0) > 0
    }
    unit_references = extract_reference_numbers(unit)
    matched_related_refs = target_numbers & unit_references

    # 질문의 실제 행위/객체가 들어간 항을 우선한다.
    score += count_question_matches(question, unit) * 5.0

    # 지나치게 짧은 단위는 대표 설명으로 약간 불리하게 한다.
    if len(unit) < 30:
        score -= 5.0

    # 면제/비적용 중심 문장은 대표 결과보다 후순위.
    exception_count = count_terms(unit, EXCEPTION_TERMS)
    if exception_count:
        score -= exception_count * 25.0

    # --------------------------------------------------------
    # A. 직접 효과
    # --------------------------------------------------------
    if effect_category == DIRECT_CONSEQUENCE:
        trigger_count = count_terms(unit, DIRECT_TRIGGER_TERMS)
        effect_count = count_terms(unit, DIRECT_EFFECT_TERMS)
        scope_count = count_terms(unit, DIRECT_SCOPE_TERMS)
        procedure_count = count_terms(unit, DIRECT_PROCEDURE_TERMS)

        score += trigger_count * 14.0
        score += effect_count * 10.0
        score += min(scope_count, 3) * 3.0

        if trigger_count > 0 and effect_count > 0:
            score += 30.0

        if matched_related_refs:
            score += 35.0

        if procedure_count:
            score -= procedure_count * 7.0

    # --------------------------------------------------------
    # B. 후속 불이익
    # --------------------------------------------------------
    elif effect_category == DOWNSTREAM_CONSEQUENCE:
        downstream_count = count_terms(unit, DOWNSTREAM_EFFECT_TERMS)
        positive_count = count_terms(unit, DOWNSTREAM_POSITIVE_TERMS)
        primary_effect_count = count_terms(unit, PRIMARY_ADVERSE_EFFECT_TERMS)
        collection_count = count_terms(unit, COLLECTION_ONLY_TERMS)

        score += downstream_count * 8.0
        score += positive_count * 12.0
        score += primary_effect_count * 10.0

        # 직접 근거 조문을 실제로 참조하는 항을 강하게 우선.
        if matched_related_refs:
            score += 45.0

        # 직접 연결 없이 독촉/체납/환급만 설명하는 항은 후순위.
        if collection_count and not matched_related_refs:
            score -= collection_count * 8.0

    # --------------------------------------------------------
    # C. 조건부 제재
    # --------------------------------------------------------
    elif effect_category == CONDITIONAL_SANCTION:
        score += count_terms(unit, SANCTION_TERMS) * 8.0

        if has_specific_reference(unit):
            score += 8.0

        if matched_related_refs:
            score += 35.0

        procedure_count = count_terms(unit, PROCEDURAL_SANCTION_TERMS)
        if procedure_count:
            score -= procedure_count * 8.0

    # --------------------------------------------------------
    # D. 범용
    # --------------------------------------------------------
    else:
        score += count_terms(
            unit,
            DIRECT_EFFECT_TERMS + DOWNSTREAM_EFFECT_TERMS + SANCTION_TERMS,
        ) * 4.0

    return score


# ============================================================
# 8. 가장 좋은 Unit 선택
# ============================================================

def select_best_statement(
    article: Dict[str, Any],
    question: str = "",
    effect_category: str = "",
    related_article_numbers: Optional[Iterable[int]] = None,
    text_limit: int = 700,
) -> str:
    if not isinstance(article, dict):
        return ""

    article_text = get_article_text(article)
    if not article_text:
        return ""

    article_title = get_article_title(article)
    units = split_article_units(article_text)
    if not units:
        return ""

    scored = [
        (
            score_unit(
                unit=unit,
                question=question,
                effect_category=effect_category,
                related_article_numbers=related_article_numbers,
                article_title=article_title,
            ),
            index,
            unit,
        )
        for index, unit in enumerate(units)
    ]

    scored.sort(key=lambda item: (-item[0], item[1]))
    best = clean_text(scored[0][2])

    if len(best) > text_limit:
        best = best[:text_limit].rstrip() + "..."

    return best


# ============================================================
# 9. 디버그 Ranking
# ============================================================

def rank_article_statements(
    article: Dict[str, Any],
    question: str = "",
    effect_category: str = "",
    related_article_numbers: Optional[Iterable[int]] = None,
) -> List[Dict[str, Any]]:
    article_text = get_article_text(article)
    article_title = get_article_title(article)
    units = split_article_units(article_text)

    results = [
        {
            "rank_source_index": index,
            "score": score_unit(
                unit=unit,
                question=question,
                effect_category=effect_category,
                related_article_numbers=related_article_numbers,
                article_title=article_title,
            ),
            "text": unit,
        }
        for index, unit in enumerate(units)
    ]

    results.sort(
        key=lambda item: (
            -item.get("score", 0),
            item.get("rank_source_index", 0),
        )
    )
    return results
