# ============================================================
# 통합 법률 Query Service
#
# 역할
# 1. 사용자 질문 입력
# 2. 질문 분석
# 3. 통합 Evidence Collector 호출
# 4. 국회도서관 수동 Evidence 연결
# 5. Evidence Organizer를 통해 주 법령 확인
# 6. 주 법령이 확정되면 공식 법령체계 연결
# 7. 주 법령이 확정되면 전체 법령 원문 연결
# 8. 최종 dict 반환
#
# 중요:
# - 실제 기본 Evidence 수집은
#   services/evidence/collector.py가 담당한다.
#
# - 기존 related_laws / full_law가 이미 있으면
#   중복 API 호출하지 않는다.
#
# - Organizer가 topic 질문을
#   topic_family_confirmed로 확정한 상태는
#   full_law 연결 이후에도 metadata에 그대로 유지한다.
# ============================================================

import os
import sys

from dataclasses import (
    asdict,
    is_dataclass,
)


# ============================================================
# 1. 프로젝트 루트 등록
# ============================================================

CURRENT_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

PROJECT_ROOT = os.path.dirname(
    CURRENT_DIR
)

if PROJECT_ROOT not in sys.path:

    sys.path.append(
        PROJECT_ROOT
    )


# ============================================================
# 2. 질문 분석
# ============================================================

from agents.query_analyzer import (
    analyze_question,
)


# ============================================================
# 3. 통합 Evidence Collector
# ============================================================

from services.evidence.collector import (
    collect_evidence,
)


# ============================================================
# 4. Evidence Organizer
# ============================================================

from services.evidence.organizer import (
    organize_evidence,
)


# ============================================================
# 5. 공식 법령체계 Collector
# ============================================================

from services.evidence.source_collectors import (
    collect_official_related_laws,
)


# ============================================================
# 6. 전체 법령 조회
# ============================================================

from services.law.full_text import (
    get_full_law,
)


# ============================================================
# 7. 국회도서관 Evidence 연결
# ============================================================

from services.library.integration import (
    attach_library_items,
)


# ============================================================
# 8. evidence_found 재계산
# ============================================================

def recompute_evidence_found(
    result: dict
) -> bool:

    if not isinstance(
        result,
        dict
    ):

        return False


    evidence_found = any(
        [
            result.get(
                "article"
            )
            is not None,

            bool(
                result.get(
                    "laws",
                    []
                )
            ),

            bool(
                result.get(
                    "law_candidates",
                    []
                )
            ),

            bool(
                result.get(
                    "precedents",
                    []
                )
            ),

            bool(
                result.get(
                    "interpretations",
                    []
                )
            ),

            bool(
                result.get(
                    "library_items",
                    []
                )
            ),

            result.get(
                "basic_info"
            )
            is not None,

            result.get(
                "full_law"
            )
            is not None,

            bool(
                result.get(
                    "histories",
                    []
                )
            ),

            bool(
                result.get(
                    "related_laws",
                    []
                )
            ),

            bool(
                result.get(
                    "supplementary_provisions",
                    []
                )
            ),

            bool(
                result.get(
                    "attachments",
                    []
                )
            ),
        ]
    )


    result[
        "evidence_found"
    ] = evidence_found


    return evidence_found


# ============================================================
# 9. 국회도서관 Evidence 연결
# ============================================================

def attach_optional_library_evidence(
    result: dict,
    control_numbers=None
) -> dict:

    if not control_numbers:

        metadata = result.setdefault(
            "metadata",
            {}
        )


        metadata[
            "library_auto_search_enabled"
        ] = False


        recompute_evidence_found(
            result
        )


        return result


    result = attach_library_items(

        result=result,

        control_numbers=control_numbers
    )


    recompute_evidence_found(
        result
    )


    return result


# ============================================================
# 10. dataclass Evidence → dict 변환
# ============================================================

def serialize_evidence_item(
    item
):

    if is_dataclass(
        item
    ):

        return asdict(
            item
        )


    if isinstance(
        item,
        dict
    ):

        return item


    return None


# ============================================================
# 11. 주 법령 + 공식 법령체계 연결
#
# Organizer는 항상 먼저 실행한다.
#
# 그 이유:
# - resolved 질문
# - topic 질문
# 모두 동일하게 primary_law metadata를 남기기 위함.
#
# 기존 related_laws가 이미 있으면
# Organizer metadata만 저장하고 API 재호출은 생략한다.
# ============================================================

def attach_confirmed_primary_related_laws(
    result: dict
) -> dict:

    if not isinstance(
        result,
        dict
    ):

        return result


    metadata = result.setdefault(
        "metadata",
        {}
    )


    # ========================================================
    # A. Organizer 실행
    # ========================================================

    try:

        organized = organize_evidence(
            result
        )

    except Exception:

        metadata[
            "official_related_laws_attached"
        ] = False

        metadata[
            "official_related_laws_reason"
        ] = "organizer_error"

        return result


    # ========================================================
    # B. Organizer 결과 metadata 저장
    # ========================================================

    metadata[
        "primary_law_confirmed"
    ] = bool(
        organized.primary_law_confirmed
    )


    metadata[
        "primary_law_selection_mode"
    ] = organized.metadata.get(
        "selection_mode",
        ""
    )


    metadata[
        "primary_law_ambiguous"
    ] = bool(
        organized.ambiguous
    )


    primary_law = organized.get_primary_law()


    if primary_law is not None:

        law_name = (
            primary_law.law_name
            or ""
        ).strip()

        law_id = (
            primary_law.law_id
            or ""
        ).strip()

        mst = (
            primary_law.mst
            or ""
        ).strip()


        metadata[
            "primary_law_name"
        ] = law_name


        metadata[
            "primary_law_id"
        ] = law_id


        metadata[
            "primary_law_mst"
        ] = mst


        metadata[
            "primary_law_confidence"
        ] = primary_law.confidence


    else:

        law_name = ""
        law_id = ""
        mst = ""


    # ========================================================
    # C. 기존 공식 법령 관계 존재 시
    # API 재호출 생략
    # ========================================================

    existing_related_laws = result.get(
        "related_laws",
        []
    )


    if existing_related_laws:

        metadata[
            "official_related_laws_attached"
        ] = True

        metadata[
            "official_related_laws_source"
        ] = "existing"

        metadata[
            "official_related_laws_count"
        ] = len(
            existing_related_laws
        )


        recompute_evidence_found(
            result
        )


        return result


    # ========================================================
    # D. 주 법령 확정되지 않음
    # ========================================================

    if not organized.primary_law_confirmed:

        metadata[
            "official_related_laws_attached"
        ] = False

        metadata[
            "official_related_laws_reason"
        ] = "primary_law_not_confirmed"

        return result


    # ========================================================
    # E. 주 법령 객체 없음
    # ========================================================

    if primary_law is None:

        metadata[
            "official_related_laws_attached"
        ] = False

        metadata[
            "official_related_laws_reason"
        ] = "primary_law_missing"

        return result


    # ========================================================
    # F. 공식 관계 조회용 식별자 확인
    # ========================================================

    if not law_name or not mst:

        metadata[
            "official_related_laws_attached"
        ] = False

        metadata[
            "official_related_laws_reason"
        ] = "primary_law_identifier_missing"

        return result


    # ========================================================
    # G. 공식 법령체계 조회
    # ========================================================

    try:

        related_laws = (
            collect_official_related_laws(

                law_name=law_name,

                mst=mst,

                law_id=law_id,
            )
        )

    except Exception:

        metadata[
            "official_related_laws_attached"
        ] = False

        metadata[
            "official_related_laws_reason"
        ] = "official_relation_collection_error"

        return result


    # ========================================================
    # H. dataclass → dict
    # ========================================================

    serialized_items = []


    for item in related_laws:

        serialized = serialize_evidence_item(
            item
        )


        if serialized is None:

            continue


        serialized_items.append(
            serialized
        )


    result[
        "related_laws"
    ] = serialized_items


    metadata[
        "official_related_laws_attached"
    ] = bool(
        serialized_items
    )


    metadata[
        "official_related_laws_source"
    ] = "confirmed_primary_law"


    metadata[
        "official_related_laws_count"
    ] = len(
        serialized_items
    )


    if not serialized_items:

        metadata[
            "official_related_laws_reason"
        ] = "no_official_relations_found"


    recompute_evidence_found(
        result
    )


    return result


# ============================================================
# 12. 확정된 주 법령 전체 원문 연결
#
# 자연어 topic 질문에서는 기존 Collector가
# full_law를 조회하지 않는다.
#
# Organizer에서 주 법령이 안전하게 확정된 뒤
# 기존 get_full_law() 서비스를 재사용하여
# 전체 조문을 추가한다.
#
# 중요:
# 이 함수에서는 Organizer를 다시 실행하지 않는다.
#
# 이유:
# topic_family_confirmed 상태에서 full_law를 붙인 뒤
# Organizer를 다시 실행하면 basic/full_law 때문에
# selection_mode가 resolved처럼 보일 수 있기 때문이다.
#
# 따라서 앞 단계에서 metadata에 저장된
# primary_law 정보를 그대로 사용한다.
# ============================================================

def attach_confirmed_primary_full_law(
    result: dict
) -> dict:

    if not isinstance(
        result,
        dict
    ):

        return result


    metadata = result.setdefault(
        "metadata",
        {}
    )


    # ========================================================
    # A. 이미 전체 법령이 있으면 재조회하지 않는다.
    # ========================================================

    existing_full_law = result.get(
        "full_law"
    )


    if existing_full_law:

        metadata[
            "primary_full_law_attached"
        ] = True

        metadata[
            "primary_full_law_source"
        ] = "existing"

        if isinstance(
            existing_full_law,
            dict
        ):

            metadata[
                "primary_full_law_article_count"
            ] = existing_full_law.get(
                "article_count",
                0
            )


        return result


    # ========================================================
    # B. 앞 단계에서 확정된 주 법령인지 확인
    # ========================================================

    confirmed = bool(
        metadata.get(
            "primary_law_confirmed"
        )
    )


    if not confirmed:

        metadata[
            "primary_full_law_attached"
        ] = False

        metadata[
            "primary_full_law_reason"
        ] = "primary_law_not_confirmed"

        return result


    # ========================================================
    # C. 주 법령명
    # ========================================================

    law_name = (
        metadata.get(
            "primary_law_name"
        )
        or ""
    ).strip()


    if not law_name:

        metadata[
            "primary_full_law_attached"
        ] = False

        metadata[
            "primary_full_law_reason"
        ] = "primary_law_name_missing"

        return result


    # ========================================================
    # D. 기존 Full Text 서비스 재사용
    # ========================================================

    try:

        full_law = get_full_law(
            law_name
        )

    except Exception:

        metadata[
            "primary_full_law_attached"
        ] = False

        metadata[
            "primary_full_law_reason"
        ] = "full_law_collection_error"

        return result


    # ========================================================
    # E. 조회 결과 확인
    # ========================================================

    if (
        not isinstance(
            full_law,
            dict
        )
        or
        full_law.get(
            "status"
        ) != "success"
    ):

        metadata[
            "primary_full_law_attached"
        ] = False

        metadata[
            "primary_full_law_reason"
        ] = "full_law_not_found"

        return result


    # ========================================================
    # F. 전체 법령 Evidence 연결
    # ========================================================

    result[
        "full_law"
    ] = full_law


    metadata[
        "primary_full_law_attached"
    ] = True


    metadata[
        "primary_full_law_source"
    ] = "confirmed_primary_law"


    metadata[
        "primary_full_law_article_count"
    ] = full_law.get(
        "article_count",
        0
    )


    recompute_evidence_found(
        result
    )


    return result


# ============================================================
# 13. 빈 질문 결과
# ============================================================

def build_empty_result():

    return {

        "status":
            "error",

        "question_type":
            "",

        "original_question":
            "",

        "search_query":
            "",

        "evidence_found":
            False,

        "article":
            None,

        "laws":
            [],

        "law_candidates":
            [],

        "precedents":
            [],

        "interpretations":
            [],

        "library_items":
            [],

        "basic_info":
            None,

        "full_law":
            None,

        "histories":
            [],

        "related_laws":
            [],

        "supplementary_provisions":
            [],

        "attachments":
            [],

        "source_status":
            [],

        "metadata": {

            "library_auto_search_enabled":
                False,
        },

        "message":
            "질문이 비어 있습니다.",
    }


# ============================================================
# 14. 최종 진입점
# ============================================================

def process_law_question(question: str, control_numbers=None):
    from services.evidence.verified_retrieval import collect_verified_topic, collect_verified_explicit
    from services.evidence.reliability import finalize_evidence
    from services.library.automatic import attach_library_search
    question = (question or "").strip()
    if not question:
        return build_empty_result()
    analysis = analyze_question(question)
    result = None
    if analysis.get("question_type") in {"특정_조문조회", "법령_전체조회"}:
        result = collect_verified_explicit(question, analysis)
    else:
        result = collect_verified_topic(question)
    if result is None:
        try:
            result = collect_evidence(question=question, analysis=analysis).to_dict()
            result = attach_confirmed_primary_related_laws(result)
            result = attach_confirmed_primary_full_law(result)
        except Exception:
            result = build_empty_result()
            result.update(status="error", original_question=question,
                          question_type=analysis.get("question_type", ""),
                          search_query=analysis.get("search_query", ""),
                          message="공식 법률정보 수집에 실패했습니다. 검색 결과가 없다는 뜻이 아닙니다.")
            result["source_status"] = [dict(source="법제처", endpoint="collection", status="error", result_count=0, message="법률정보 수집 실패")]
    result.setdefault("metadata", {})["analysis"] = analysis
    if control_numbers:
        result = attach_optional_library_evidence(result, control_numbers)
    else:
        result = attach_library_search(result)
    result = finalize_evidence(result)
    recompute_evidence_found(result)
    return result
