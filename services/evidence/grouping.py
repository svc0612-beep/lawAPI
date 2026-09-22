# ============================================================
# 관련 조문 → 관련 법령 후보 그룹화
# ============================================================

from typing import (
    Any,
    Dict,
    List,
)

from models.evidence import (
    LawEvidence,
    LawCandidateEvidence,
)

from services.evidence.common import (
    normalize_text,
)


def build_law_candidates(
    laws: List[LawEvidence]
) -> List[LawCandidateEvidence]:

    grouped: Dict[
        str,
        Dict[str, Any]
    ] = {}


    for law in laws:

        law_name = normalize_text(
            law.law_name
        )

        if not law_name:
            continue


        if law_name not in grouped:

            grouped[law_name] = {

                "law_name":
                    law_name,

                "law_type":
                    law.law_type,

                "ministry":
                    law.ministry,

                "law_id":
                    law.law_id,

                "mst":
                    law.mst,

                "effective_date":
                    law.effective_date,

                "promulgation_date":
                    law.promulgation_date,

                "revision_type":
                    law.revision_type,

                "article_numbers":
                    [],

                "representative_titles":
                    [],

                "representative_articles":
                    [],

                "scores":
                    [],

                "coverages":
                    [],

                "first_rank":
                    (
                        law.final_rank
                        or
                        law.original_rank
                        or
                        999
                    ),
            }


        group = grouped[
            law_name
        ]


        # ====================================================
        # 조문 번호
        # ====================================================

        if law.article_number is not None:

            article_label = (
                f"제{law.article_number}조"
            )

            if law.sub_article_number:

                article_label += (
                    f"의{law.sub_article_number}"
                )

            if (
                article_label
                not in
                group["article_numbers"]
            ):

                group[
                    "article_numbers"
                ].append(
                    article_label
                )


        # ====================================================
        # 대표 제목
        # ====================================================

        title = normalize_text(
            law.article_title
        )

        if (
            title
            and
            title not in group[
                "representative_titles"
            ]
            and
            len(
                group[
                    "representative_titles"
                ]
            ) < 3
        ):

            group[
                "representative_titles"
            ].append(
                title
            )


        # ====================================================
        # 대표 조문
        # ====================================================

        article_text = normalize_text(
            law.article_text
        )

        if (
            article_text
            and
            article_text not in group[
                "representative_articles"
            ]
            and
            len(
                group[
                    "representative_articles"
                ]
            ) < 3
        ):

            group[
                "representative_articles"
            ].append(
                article_text
            )


        # ====================================================
        # 관련도
        # ====================================================

        if law.relevance_score is not None:

            group[
                "scores"
            ].append(
                law.relevance_score
            )


        if law.query_coverage is not None:

            group[
                "coverages"
            ].append(
                law.query_coverage
            )


        current_rank = (
            law.final_rank
            or
            law.original_rank
            or
            999
        )

        group[
            "first_rank"
        ] = min(
            group[
                "first_rank"
            ],
            current_rank
        )


    candidates: List[
        LawCandidateEvidence
    ] = []


    for group in grouped.values():

        best_score = (

            max(
                group["scores"]
            )

            if group["scores"]

            else None
        )


        best_coverage = (

            max(
                group["coverages"]
            )

            if group["coverages"]

            else None
        )


        candidates.append(

            LawCandidateEvidence(

                law_name=group[
                    "law_name"
                ],

                law_type=group[
                    "law_type"
                ],

                ministry=group[
                    "ministry"
                ],

                law_id=group[
                    "law_id"
                ],

                mst=group[
                    "mst"
                ],

                effective_date=group[
                    "effective_date"
                ],

                promulgation_date=group[
                    "promulgation_date"
                ],

                revision_type=group[
                    "revision_type"
                ],

                matched_article_count=len(
                    group[
                        "article_numbers"
                    ]
                ),

                article_numbers=group[
                    "article_numbers"
                ],

                representative_titles=group[
                    "representative_titles"
                ],

                representative_articles=group[
                    "representative_articles"
                ],

                best_relevance_score=(
                    best_score
                ),

                best_query_coverage=(
                    best_coverage
                ),

                rank=group[
                    "first_rank"
                ],
            )
        )


    candidates.sort(

        key=lambda item: (

            -(
                item.best_relevance_score
                if
                item.best_relevance_score
                is not None
                else -1
            ),

            -item.matched_article_count,

            (
                item.rank
                if item.rank is not None
                else 999
            ),
        )
    )


    for index, candidate in enumerate(
        candidates,
        start=1
    ):

        candidate.rank = index


    return candidates