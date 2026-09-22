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
from services.evidence.question_action_matcher import score_question_connection


# ============================================================
# 1. Category
# ============================================================

DIRECT_BASIS = "direct_basis"
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


def get_article_units(
    article: Dict[str, Any]
) -> List[str]:
    """
    full_law의 구조화된 paragraphs를 우선 사용하고,
    없을 때만 기존 full_text 분리 방식으로 fallback한다.
    """

    if not isinstance(
        article,
        dict
    ):
        return []

    paragraphs = (
        article.get(
            "paragraphs"
        )
        or
        []
    )

    units: List[str] = []

    if isinstance(
        paragraphs,
        list
    ):

        for paragraph in paragraphs:

            if not isinstance(
                paragraph,
                dict
            ):
                continue

            paragraph_text = clean_text(
                paragraph.get(
                    "text"
                )
            )

            if (
                paragraph_text
                and
                paragraph_text not in units
            ):
                units.append(
                    paragraph_text
                )

    if units:
        return units

    article_text = get_article_text(
        article
    )

    return split_article_units(
        article_text
    )


def get_action_core_fragments(
    action_token: str
) -> List[str]:
    """
    복합 행동어에서 뒤쪽 행동 핵심을 일반적으로 추출한다.

    예:
    - 음주운전 -> 운전
    - 무단복제 -> 복제

    특정 법률명/조문번호는 사용하지 않는다.
    """

    token = clean_text(
        action_token
    )

    token = re.sub(
        r"[^가-힣A-Za-z0-9]",
        "",
        token
    )

    if len(
        token
    ) < 3:
        return []

    results: List[str] = []

    max_length = min(
        4,
        len(
            token
        )
        - 1
    )

    for length in range(
        2,
        max_length + 1
    ):

        fragment = token[
            -length:
        ]

        if (
            fragment
            and
            fragment != token
            and
            fragment not in results
        ):
            results.append(
                fragment
            )

    return results


def has_action_core_match(
    action_token: str,
    text: str
) -> bool:

    target = clean_text(
        text
    )

    if not target:
        return False

    return any(
        fragment in target

        for fragment in get_action_core_fragments(
            action_token
        )
    )


def has_action_normative_proximity(
    action_token: str,
    unit: str
) -> bool:
    """
    질문 행동 핵심에 금지/의무 규범이 직접 붙는지를 본다.

    단순히 절차의 전제로 언급된 경우보다,
    '... 운전하여서는 아니 된다'처럼
    질문 행위 자체를 직접 규율하는 문장을 우선한다.
    """

    unit = clean_text(
        unit
    )

    if not unit:
        return False

    normative_patterns = (
        r"하여서는\s*아니\s*된다",
        r"해서는\s*아니\s*된다",
        r"하지\s*아니하여야\s*한다",
        r"하여야\s*한다",
        r"해야\s*한다",
    )

    for fragment in get_action_core_fragments(
        action_token
    ):

        escaped = re.escape(
            fragment
        )

        for normative in normative_patterns:

            pattern = (
                escaped
                +
                r".{0,24}?"
                +
                normative
            )

            if re.search(
                pattern,
                unit
            ):
                return True

    return False


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

    # --------------------------------------------------------
    # 직접 근거용 질문 행위/객체 연결도
    #
    # 조문 제목은 모든 항에 공통이므로 body=unit만 사용한다.
    # 즉 "이 항 자체가 질문의 핵심 행위를 설명하는가"를 본다.
    # --------------------------------------------------------
    direct_basis_mode = (
        not effect_category
        or effect_category == DIRECT_BASIS
    )

    unit_connection = {}

    if direct_basis_mode and question:
        try:
            unit_connection = score_question_connection(
                question=question,
                title="",
                body=unit,
            ) or {}
        except Exception:
            unit_connection = {}

        action_token = clean_text(
            unit_connection.get("action_token")
        )

        body_action_match = bool(
            unit_connection.get("body_action_match")
            or unit_connection.get("action_match")
        )

        action_core_match = bool(
            action_token
            and
            has_action_core_match(
                action_token,
                unit
            )
        )

        action_normative_proximity = bool(
            action_token
            and
            has_action_normative_proximity(
                action_token,
                unit
            )
        )

        effective_action_match = bool(
            body_action_match
            or
            action_core_match
        )

        object_tokens = (
            unit_connection.get(
                "object_tokens",
                []
            )
            or
            []
        )

        independent_object_tokens = [
            token
            for token in object_tokens
            if clean_text(token)
            and clean_text(token) != action_token
        ]

        object_match_count = safe_int(
            unit_connection.get("object_match_count"),
            0,
        )

        combined_match = bool(
            unit_connection.get("combined_match")
        )

        # exact 복합어가 없어도 행동 핵심이 있으면 살려 둔다.
        if action_token and not effective_action_match:
            score -= 45.0

        if body_action_match:
            score += 30.0

        elif action_core_match:
            score += 22.0

        # 질문 행위 자체를 직접 금지/의무화하는 항을 강하게 우대한다.
        if action_normative_proximity:
            score += 40.0

        if combined_match:
            score += 10.0

        # action과 같은 토큰이 object로 중복 추출된 경우 과대평가 방지
        if independent_object_tokens:
            score += min(
                object_match_count,
                3,
            ) * 2.0

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
    # D. 직접 근거
    # --------------------------------------------------------
    elif direct_basis_mode:
        score += count_terms(
            unit,
            (
                "하여야 한다",
                "하여서는 아니 된다",
                "해서는 아니 된다",
                "할 수 있다",
                "청구할 수 있다",
                "금지",
                "의무",
            ),
        ) * 2.0

    # --------------------------------------------------------
    # E. 기타 범용
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
    units = get_article_units(
        article
    )
    if not units:
        return ""

    direct_basis_mode = (
        not effect_category
        or effect_category == DIRECT_BASIS
    )

    scored = []

    for index, unit in enumerate(units):
        unit_score = score_unit(
            unit=unit,
            question=question,
            effect_category=effect_category,
            related_article_numbers=related_article_numbers,
            article_title=article_title,
        )

        # 직접 근거 후보가 비슷하면 앞쪽 핵심 항을 약하게 우선한다.
        # 행위 불일치 감점(-45)보다 훨씬 작은 보조값이다.
        if direct_basis_mode:
            unit_score -= index * 1.5

        scored.append(
            (
                unit_score,
                index,
                unit,
            )
        )

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
    units = get_article_units(
        article
    )

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
