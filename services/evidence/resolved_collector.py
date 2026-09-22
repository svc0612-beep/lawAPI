# ============================================================
# Resolved Law Collector
#
# 특정 공식 법령이 확정된 경우의 Evidence 수집
# ============================================================

from typing import (
    Any,
    Dict,
)

from models.evidence import (
    EvidenceBundle,
)

from services.law.full_text import (
    get_full_law,
)

from services.evidence.builders import (
    build_basic_info,
    build_full_law_evidence,
)

from services.evidence.grouping import (
    build_law_candidates,
)

from services.evidence.source_collectors import (
    collect_related_laws,
    collect_official_related_laws,
    collect_precedents,
    collect_interpretations,
    collect_specific_article,
    collect_supplementary_provisions,
)

from services.evidence.common import (
    normalize_text,
    safe_int,
    make_status,
    build_article_query,
)


def collect_resolved_law_bundle(
    question: str,
    analysis: Dict[str, Any],
    resolved: Dict[str, Any]
) -> EvidenceBundle:

    # ========================================================
    # 확정 공식 법령명
    # ========================================================

    law_name = normalize_text(
        resolved.get(
            "resolved_law_name"
        )
    )


    # ========================================================
    # 기본정보
    # ========================================================

    basic_info = build_basic_info(
        resolved.get(
            "law_info"
        )
    )


    # ========================================================
    # 전체 법령
    # ========================================================

    full_law = build_full_law_evidence(
        get_full_law(
            law_name
        )
    )


    # ========================================================
    # 관련 조문
    # ========================================================

    laws = collect_related_laws(

        query=law_name,

        fallback_mode=False,

        top_k=10
    )


    # ========================================================
    # 검색상 관련 법령
    # ========================================================

    law_candidates = build_law_candidates(
        laws
    )


    # ========================================================
    # 공식 법령 체계 관계
    # ========================================================

    related_laws = collect_official_related_laws(

        law_name=law_name,

        mst=(
            basic_info.mst
            if basic_info
            else ""
        ),

        law_id=(
            basic_info.law_id
            if basic_info
            else ""
        ),
    )


    # ========================================================
    # 판례
    # ========================================================

    precedents = collect_precedents(
        law_name,
        display=5
    )


    # ========================================================
    # 법령해석례
    # ========================================================

    interpretations = collect_interpretations(
        law_name,
        display=5
    )


    # ========================================================
    # 부칙
    # ========================================================

    supplementary_provisions = (
        collect_supplementary_provisions(
            law_name
        )
    )


    # ========================================================
    # 특정 조문 요청
    # ========================================================

    article = None


    article_number = safe_int(
        analysis.get(
            "article_number"
        )
    )


    sub_article_number = (
        safe_int(
            analysis.get(
                "sub_article_number"
            ),
            0
        )
        or 0
    )


    paragraph_number = safe_int(
        analysis.get(
            "paragraph_number"
        )
    )


    evidence_query = law_name


    if article_number is not None:

        article = collect_specific_article(

            law_name=law_name,

            article_number=article_number,

            sub_article_number=(
                sub_article_number
            ),

            paragraph_number=(
                paragraph_number
            )
        )


        evidence_query = build_article_query(

            law_name=law_name,

            article_number=article_number,

            sub_article_number=(
                sub_article_number
            )
        )


        # ----------------------------------------------------
        # 특정 조문 판례
        # ----------------------------------------------------

        article_precedents = (
            collect_precedents(
                evidence_query,
                display=5
            )
        )


        if article_precedents:

            precedents = (
                article_precedents
            )


        # ----------------------------------------------------
        # 특정 조문 법령해석례
        # ----------------------------------------------------

        article_interpretations = (
            collect_interpretations(
                evidence_query,
                display=5
            )
        )


        if article_interpretations:

            interpretations = (
                article_interpretations
            )


    # ========================================================
    # Bundle
    # ========================================================

    return EvidenceBundle(

        status="success",

        question_type=normalize_text(
            analysis.get(
                "question_type"
            )
        ),

        original_question=question,

        search_query=evidence_query,

        article=article,

        laws=laws,

        law_candidates=law_candidates,

        related_laws=related_laws,

        precedents=precedents,

        interpretations=interpretations,

        basic_info=basic_info,

        full_law=full_law,

        supplementary_provisions=(
            supplementary_provisions
        ),

        source_status=[

            make_status(
                "lawResolver",
                len(
                    resolved.get(
                        "candidates",
                        []
                    )
                ),
                "공식 법령 하나로 확인됨"
            ),

            make_status(
                "law/full",
                (
                    full_law.article_count
                    if full_law
                    else 0
                )
            ),

            make_status(
                "aiSearch/articles",
                len(laws)
            ),

            make_status(
                "aiSearch/lawCandidates",
                len(law_candidates)
            ),

            make_status(
                "lsStmd",
                len(related_laws),
                "공식 법령 체계도"
            ),

            make_status(
                "prec",
                len(precedents)
            ),

            make_status(
                "expc",
                len(interpretations)
            ),

            make_status(
                "law/supplementary",
                len(
                    supplementary_provisions
                )
            ),
        ],

        metadata={

            "search_mode":
                "resolved_law",

            "resolved_law_name":
                law_name,

            "resolver_status":
                "resolved",

            "resolver_confidence":
                resolved.get(
                    "confidence"
                ),

            "fallback_used":
                False,
        },
    )
