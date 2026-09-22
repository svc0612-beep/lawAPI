# ============================================================
# Evidence 공통 유틸리티
# ============================================================

import re

from typing import (
    Any,
    Dict,
    Optional,
)

from models.evidence import (
    EvidenceSourceStatus,
)

from utils.query_normalizer import (
    normalize_search_query,
)


# ============================================================
# 문자열 정리
# ============================================================

def normalize_text(
    value: Any
) -> str:

    if value is None:
        return ""

    return re.sub(
        r"\s+",
        " ",
        str(value)
    ).strip()


# ============================================================
# 안전한 int 변환
# ============================================================

def safe_int(
    value: Any,
    default=None
):

    try:
        return int(
            value
        )

    except (
        TypeError,
        ValueError
    ):
        return default


# ============================================================
# Source Status 생성
# ============================================================

def make_status(
    endpoint: str,
    count: int,
    message: str = ""
) -> EvidenceSourceStatus:

    return EvidenceSourceStatus(

        source="법제처",

        endpoint=endpoint,

        status="success",

        result_count=count,

        message=message,
    )


# ============================================================
# 특정 조문용 검색어
# ============================================================

def build_article_query(
    law_name: str,
    article_number: Optional[int],
    sub_article_number: int = 0
) -> str:

    if article_number is None:
        return law_name

    if sub_article_number:

        return (
            f"{law_name} "
            f"제{article_number}조의"
            f"{sub_article_number}"
        )

    return (
        f"{law_name} "
        f"제{article_number}조"
    )


# ============================================================
# 주제 검색어
# ============================================================

def build_topic_query(
    question: str,
    analysis: Dict[str, Any]
) -> str:

    analyzer_query = normalize_text(
        analysis.get(
            "search_query"
        )
    )

    if analyzer_query:

        normalized = normalize_search_query(
            analyzer_query
        )

        if normalized:
            return normalized

    normalized = normalize_search_query(
        question
    )

    if normalized:
        return normalized

    return normalize_text(
        question
    )