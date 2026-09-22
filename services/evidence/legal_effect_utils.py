# ============================================================
# Legal Effect Utils
#
# 역할
#
# legal_effect_analyzer 계열에서 공통으로 사용하는
# 문자열 / 질문 / 조문 / 역할 / 효과 관련 유틸 함수.
#
# 중요
#
# - 특정 법령명 하드코딩 금지
# - 특정 조문번호 하드코딩 금지
# - 분석 흐름 자체는 넣지 않는다.
# - 재사용 가능한 공통 함수만 관리한다.
# ============================================================

import re

from typing import (
    Any,
    Dict,
    List,
    Optional,
    Set,
)


from services.evidence.legal_effect_constants import (
    QUESTION_STOP_WORDS,
    LEGAL_ROLE_ALIASES,
    KNOWN_LEGAL_SUBJECTS,
    TITLE_DIRECT_TERMS,
    NORMATIVE_TERMS,
    LEGAL_EFFECT_TERMS,
    STRONG_CONSEQUENCE_TERMS,
    CONSEQUENCE_TITLE_TERMS,
    CONCEPT_STOP_WORDS,
)


# ============================================================
# 1. 문자열 정리
# ============================================================

def clean_text(
    value: Any
) -> str:

    if value is None:

        return ""

    text = str(
        value
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# ============================================================
# 2. 비교용 정규화
# ============================================================

def normalize_for_match(
    value: Any
) -> str:

    return clean_text(
        value
    ).lower()


# ============================================================
# 3. 법령명 정규화
# ============================================================

def normalize_law_name(
    value: Any
) -> str:

    return "".join(
        clean_text(
            value
        ).split()
    )


# ============================================================
# 4. 안전한 정수 변환
# ============================================================

def safe_int(
    value: Any,
    default: int = 0
) -> int:

    try:

        return int(
            value
        )

    except (
        TypeError,
        ValueError,
    ):

        return default


# ============================================================
# 5. 조문 Key
#
# 예:
#
# 제28조
# → 28:0
#
# 제28조의2
# → 28:2
# ============================================================

def make_article_key(
    article_number: Any,
    sub_article_number: Any = 0
) -> str:

    try:

        article_number = int(
            article_number
        )

    except (
        TypeError,
        ValueError,
    ):

        return ""

    try:

        sub_article_number = int(
            sub_article_number
            or 0
        )

    except (
        TypeError,
        ValueError,
    ):

        sub_article_number = 0

    return (
        f"{article_number}:"
        f"{sub_article_number}"
    )


# ============================================================
# 6. 질문 Token
# ============================================================

def extract_question_tokens(
    question: str
) -> List[str]:

    question = normalize_for_match(
        question
    )

    raw_tokens = re.findall(
        r"[가-힣A-Za-z0-9]+",
        question
    )

    results = []

    for token in raw_tokens:

        token = token.strip()

        if len(
            token
        ) < 2:

            continue

        if token in QUESTION_STOP_WORDS:

            continue

        if token not in results:

            results.append(
                token
            )

    return results


# ============================================================
# 7. 질문의 법률상 주체
#
# 예:
#
# 회사
# → 사업주 / 사용자 / 법인 / 사업자
# ============================================================

def extract_question_roles(
    question: str
) -> Set[str]:

    question = normalize_for_match(
        question
    )

    results = set()

    for (
        user_term,
        legal_terms
    ) in LEGAL_ROLE_ALIASES.items():

        if user_term not in question:

            continue

        for legal_term in legal_terms:

            results.add(
                legal_term
            )

    return results


# ============================================================
# 8. 조문 전체 Text
# ============================================================

def get_article_text(
    article: Dict[str, Any]
) -> str:

    if not isinstance(
        article,
        dict
    ):

        return ""

    title = clean_text(
        article.get(
            "article_title"
        )
    )

    full_text = clean_text(
        article.get(
            "full_text"
        )
    )

    if not full_text:

        full_text = clean_text(
            article.get(
                "article_content"
            )
        )

    return (
        f"{title} {full_text}"
    ).strip()


# ============================================================
# 9. 조문 앞부분
#
# direct 분석 시 지나치게 긴 조문 전체를
# 매번 비교하지 않도록 앞부분만 사용.
# ============================================================

def get_article_lead_text(
    article: Dict[str, Any],
    max_length: int = 700
) -> str:

    if not isinstance(
        article,
        dict
    ):

        return ""

    full_text = clean_text(
        article.get(
            "full_text"
        )
    )

    if not full_text:

        full_text = clean_text(
            article.get(
                "article_content"
            )
        )

    return full_text[
        :max_length
    ]


# ============================================================
# 10. Token Match 수
# ============================================================

def count_matches(
    tokens,
    text: str
) -> int:

    text = normalize_for_match(
        text
    )

    return sum(
        1
        for token in tokens
        if token in text
    )


# ============================================================
# 11. 제목의 규범 역할
# ============================================================

def detect_title_roles(
    title: str
) -> List[str]:

    title = normalize_for_match(
        title
    )

    results = []

    for (
        role,
        terms
    ) in TITLE_DIRECT_TERMS.items():

        if any(
            term in title
            for term in terms
        ):

            results.append(
                role
            )

    return results


# ============================================================
# 12. 본문의 규범 역할
# ============================================================

def detect_normative_roles(
    text: str
) -> List[str]:

    text = normalize_for_match(
        text
    )

    results = []

    for (
        role,
        terms
    ) in NORMATIVE_TERMS.items():

        if any(
            term in text
            for term in terms
        ):

            results.append(
                role
            )

    return results


# ============================================================
# 13. 법적 효과 유형 감지
# ============================================================

def detect_effect_types(
    text: str
) -> List[str]:

    text = normalize_for_match(
        text
    )

    results = []

    for (
        effect_type,
        terms
    ) in LEGAL_EFFECT_TERMS.items():

        if any(
            term in text
            for term in terms
        ):

            results.append(
                effect_type
            )

    return results


# ============================================================
# 14. 강한 법적 효과 Signal
# ============================================================

def has_strong_consequence_signal(
    article: Dict[str, Any]
) -> bool:

    if not isinstance(
        article,
        dict
    ):

        return False

    title = normalize_for_match(
        article.get(
            "article_title"
        )
    )

    text = normalize_for_match(
        get_article_text(
            article
        )
    )

    if any(
        term in title
        for term in CONSEQUENCE_TITLE_TERMS
    ):

        return True

    if any(
        term in text
        for term in STRONG_CONSEQUENCE_TERMS
    ):

        return True

    return False


# ============================================================
# 15. 조문 참조 번호 추출
#
# 예:
#
# 제33조제5항
# → 33
#
# 여기서는 상위 연결 분석에 필요한
# article_number만 반환한다.
#
# 세부 항/호 분석은 legal_reference_parser가 담당.
# ============================================================

def extract_article_references(
    text: str,
    own_article_number: Optional[int] = None
) -> Set[int]:

    text = clean_text(
        text
    )

    matches = re.findall(
        r"제\s*(\d+)\s*조",
        text
    )

    results = set()

    for value in matches:

        try:

            number = int(
                value
            )

        except (
            TypeError,
            ValueError,
        ):

            continue

        if (
            own_article_number is not None
            and
            number == own_article_number
        ):

            continue

        results.add(
            number
        )

    return results


# ============================================================
# 16. 개념 Token
#
# 조문 간 연결성을 계산할 때 사용하는
# 일반적인 의미 Token.
# ============================================================

def extract_concept_tokens(
    text: str
) -> Set[str]:

    text = normalize_for_match(
        text
    )

    raw_tokens = re.findall(
        r"[가-힣A-Za-z0-9]+",
        text
    )

    results = set()

    for token in raw_tokens:

        token = token.strip()

        if len(
            token
        ) < 2:

            continue

        if token in CONCEPT_STOP_WORDS:

            continue

        results.add(
            token
        )

    return results


# ============================================================
# 17. 제목의 법률 주체
# ============================================================

def get_title_subjects(
    title: str
) -> Set[str]:

    title = normalize_for_match(
        title
    )

    return {

        subject

        for subject in KNOWN_LEGAL_SUBJECTS

        if subject in title
    }


# ============================================================
# 18. 질문 주체 ↔ 제목 주체 충돌
#
# 예:
#
# 질문 = 회사
# 제목 = 공무원의 ...
#
# 이런 경우 direct 후보에서 제외할 수 있다.
# ============================================================

def has_subject_conflict(
    article: Dict[str, Any],
    question_roles: Set[str]
) -> bool:

    if not question_roles:

        return False

    if not isinstance(
        article,
        dict
    ):

        return False

    title = clean_text(
        article.get(
            "article_title"
        )
    )

    title_subjects = get_title_subjects(
        title
    )

    if not title_subjects:

        return False

    if (
        title_subjects
        &
        question_roles
    ):

        return False

    return True