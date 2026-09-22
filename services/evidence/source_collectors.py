# ============================================================
# Evidence Source Collectors
#
# 실제 API / 서비스 호출 담당
# ============================================================

from typing import (
    List,
    Optional,
)

from models.evidence import (
    ArticleEvidence,
    LawEvidence,
    PrecedentEvidence,
    InterpretationEvidence,
    RelatedLawEvidence,
    SupplementaryProvisionEvidence,
)

from services.law.article import (
    search_law_article,
    extract_article_text,
)

from services.law.query_expander import (
    search_with_query_expansion,
)

from services.law.supplementary import (
    get_supplementary_provisions,
)

from services.law.related_laws import (
    get_official_related_laws,
)

from services.evidence.precedent import (
    search_precedents,
)

from services.evidence.interpretation import (
    search_interpretations,
)

from services.evidence.builders import (
    build_law_evidence,
    build_precedent_evidence,
    build_interpretation_evidence,
    build_related_law_evidence,
    build_supplementary_evidence,
)

from services.evidence.common import (
    normalize_text,
)


# ============================================================
# aiSearch 관련 조문
# ============================================================

def collect_related_laws(
    query: str,
    fallback_mode: bool = False,
    top_k: int = 10
) -> List[LawEvidence]:

    query = normalize_text(
        query
    )

    if not query:
        return []


    reranked = search_with_query_expansion(

        query=query,

        fallback_mode=fallback_mode,

        top_k=top_k
    )


    return [

        build_law_evidence(
            item
        )

        for item in reranked
    ]


# ============================================================
# 공식 법령 체계 관계
#
# 주의:
# collect_related_laws()는 aiSearch 관련 조문 수집 함수다.
# 이 함수는 lsStmd 공식 체계도 전용 경로다.
# ============================================================

def collect_official_related_laws(
    law_name: str,
    mst: str,
    law_id: str = "",
) -> List[RelatedLawEvidence]:

    law_name = normalize_text(
        law_name
    )

    mst = normalize_text(
        mst
    )

    law_id = normalize_text(
        law_id
    )

    if not law_name or not mst:
        return []

    try:

        result = get_official_related_laws(
            law_name=law_name,
            mst=mst,
            law_id=law_id,
        )

    except (
        RuntimeError,
        ValueError,
    ):

        # 공식 관계 수집 실패가 기존 법령·판례·해석례
        # Evidence 전체를 무효화하지 않도록 격리한다.
        return []

    if result.get("status") != "success":
        return []

    return [
        build_related_law_evidence(item)
        for item in result.get(
            "related_laws",
            [],
        )
        if isinstance(item, dict)
    ]


# ============================================================
# 판례
# ============================================================

def collect_precedents(
    query: str,
    display: int = 5
) -> List[PrecedentEvidence]:

    query = normalize_text(
        query
    )

    if not query:
        return []


    raw_results = search_precedents(
        query=query,
        display=display
    )


    return [

        build_precedent_evidence(
            item
        )

        for item in raw_results
    ]


# ============================================================
# 법령해석례
# ============================================================

def collect_interpretations(
    query: str,
    display: int = 5
) -> List[InterpretationEvidence]:

    query = normalize_text(
        query
    )

    if not query:
        return []


    raw_results = search_interpretations(
        query=query,
        display=display
    )


    return [

        build_interpretation_evidence(
            item
        )

        for item in raw_results
    ]


# ============================================================
# 부칙
# ============================================================

def collect_supplementary_provisions(
    law_name: str
) -> List[SupplementaryProvisionEvidence]:

    law_name = normalize_text(
        law_name
    )

    if not law_name:
        return []


    result = get_supplementary_provisions(
        law_name
    )


    if result.get(
        "status"
    ) != "success":

        return []


    return [

        build_supplementary_evidence(
            item
        )

        for item in result.get(
            "supplementary_provisions",
            []
        )

        if isinstance(
            item,
            dict
        )
    ]


# ============================================================
# 특정 조문
# ============================================================

def collect_specific_article(
    law_name: str,
    article_number: int,
    sub_article_number: int = 0,
    paragraph_number: Optional[int] = None
) -> Optional[ArticleEvidence]:

    result = search_law_article(

        law_name=law_name,

        article_number=article_number,

        sub_article_number=sub_article_number
    )


    law_info = result.get(
        "law_info",
        {}
    )


    clean_article = extract_article_text(
        result.get(
            "article_data",
            {}
        )
    )


    paragraphs = clean_article.get(
        "paragraphs",
        []
    ) or []


    specific_paragraph = None


    if (
        paragraph_number is not None
        and
        1 <= paragraph_number <= len(
            paragraphs
        )
    ):

        specific_paragraph = paragraphs[
            paragraph_number - 1
        ]


    return ArticleEvidence(

        law_name=normalize_text(
            law_info.get(
                "법령명한글"
            )
        ),

        law_type=normalize_text(
            law_info.get(
                "법령구분명"
            )
        ),

        law_id=normalize_text(
            law_info.get(
                "법령ID"
            )
        ),

        mst=normalize_text(
            law_info.get(
                "법령일련번호"
            )
        ),

        effective_date=normalize_text(
            law_info.get(
                "시행일자"
            )
        ),

        article=normalize_text(
            clean_article.get(
                "article"
            )
        ),

        article_title=normalize_text(
            clean_article.get(
                "title"
            )
        ),

        paragraph_number=(
            paragraph_number
        ),

        specific_paragraph=(
            specific_paragraph
        ),

        paragraphs=paragraphs,

        full_article_text=normalize_text(
            clean_article.get(
                "text"
            )
        ),
    )