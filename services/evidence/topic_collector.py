# ============================================================
# Topic Collector
#
# 자연어 주제 질문 / ambiguous 법령명 처리
# ============================================================

from typing import (
    Any,
    Dict,
    Optional,
)

from models.evidence import (
    EvidenceBundle,
)

from services.evidence.common import (
    normalize_text,
    build_topic_query,
    make_status,
)

from services.evidence.grouping import (
    build_law_candidates,
)

from services.evidence.source_collectors import (
    collect_related_laws,
    collect_precedents,
    collect_interpretations,
)


def collect_topic_bundle(
    question: str,
    analysis: Dict[str, Any],
    resolver_result: Optional[
        Dict[str, Any]
    ] = None
) -> EvidenceBundle:

    # ========================================================
    # 주제 검색어
    # ========================================================

    topic_query = build_topic_query(

        question=question,

        analysis=analysis
    )


    # ========================================================
    # 관련 조문
    # ========================================================

    laws = collect_related_laws(

        query=topic_query,

        fallback_mode=True,

        top_k=20
    )


    # ========================================================
    # 검색상 관련 법령
    # ========================================================

    law_candidates = build_law_candidates(
        laws
    )


    # ========================================================
    # 판례
    # ========================================================

    precedents = collect_precedents(
        topic_query,
        display=5
    )


    # ========================================================
    # 법령해석례
    # ========================================================

    interpretations = (
        collect_interpretations(
            topic_query,
            display=5
        )
    )


    # ========================================================
    # Resolver 정보
    # ========================================================

    resolver_status = ""

    resolver_confidence = None

    resolver_candidates = []


    if resolver_result:

        resolver_status = normalize_text(
            resolver_result.get(
                "status"
            )
        )


        resolver_confidence = (
            resolver_result.get(
                "confidence"
            )
        )


        resolver_candidates = [

            {
                "law_name":
                    item.get(
                        "law_name"
                    ),

                "abbreviation":
                    item.get(
                        "abbreviation"
                    ),

                "law_type":
                    item.get(
                        "law_type"
                    ),

                "resolver_score":
                    item.get(
                        "resolver_score"
                    ),
            }

            for item in resolver_result.get(
                "candidates",
                []
            )
        ]


    # ========================================================
    # Bundle
    #
    # 특정 법 하나를 확정하지 않았으므로:
    #
    # basic_info = None
    # full_law = None
    # supplementary_provisions = []
    # ========================================================

    return EvidenceBundle(

        status="success",

        question_type="관련_법령탐색",

        original_question=question,

        search_query=topic_query,

        basic_info=None,

        full_law=None,

        laws=laws,

        law_candidates=law_candidates,

        precedents=precedents,

        interpretations=interpretations,

        supplementary_provisions=[],

        source_status=[

            make_status(
                "lawResolver",
                len(
                    resolver_candidates
                ),
                (
                    "특정 법령으로 확정하지 않고 주제 검색"
                    if
                    resolver_status
                    == "ambiguous"
                    else
                    "주제 기반 검색"
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
                "prec",
                len(precedents)
            ),

            make_status(
                "expc",
                len(interpretations)
            ),
        ],

        metadata={

            "search_mode":
                "topic",

            "resolved_law_name":
                "",

            "resolver_status":
                resolver_status,

            "resolver_confidence":
                resolver_confidence,

            "resolver_candidates":
                resolver_candidates,

            "fallback_used":
                True,
        },
    )