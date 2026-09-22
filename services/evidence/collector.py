# ============================================================
# Evidence Collector
#
# 역할:
#
# 질문 분석 결과
#      ↓
# Law Resolver
#      ↓
# resolved / ambiguous / topic 판단
#      ↓
# 실제 Collector로 전달
#
# 세부 API 호출이나 Evidence 생성은
# 이 파일에서 하지 않는다.
# ============================================================

from typing import (
    Any,
    Dict,
)

from services.law.resolver import (
    resolve_law_name,
)

from utils.query_normalizer import (
    normalize_search_query,
)

from services.evidence.common import (
    normalize_text,
)

from services.evidence.resolved_collector import (
    collect_resolved_law_bundle,
)

from services.evidence.topic_collector import (
    collect_topic_bundle,
)


# ============================================================
# Resolver 실행
# ============================================================

def resolve_from_analysis(
    question: str,
    analysis: Dict[str, Any]
) -> Dict[str, Any]:

    law_hint = normalize_text(
        analysis.get(
            "law_name"
        )
    )


    search_query = (
        normalize_search_query(
            question
        )
    )


    resolver_input = (
        law_hint
        or
        question
    )


    return resolve_law_name(

        user_expression=resolver_input,

        search_query=search_query
    )


# ============================================================
# 최종 Evidence 수집 진입점
# ============================================================

def collect_evidence(
    question: str,
    analysis: Dict[str, Any]
):

    question = normalize_text(
        question
    )


    question_type = normalize_text(
        analysis.get(
            "question_type"
        )
    )


    law_hint = normalize_text(
        analysis.get(
            "law_name"
        )
    )


    # ========================================================
    # Resolver를 사용할지 판단
    # ========================================================

    should_try_resolver = bool(
        law_hint
    )


    if question_type in {

        "특정_조문조회",

        "법령_전체조회",

        "법령_검색",

    }:

        should_try_resolver = True


    resolver_result = None


    # ========================================================
    # Resolver
    # ========================================================

    if should_try_resolver:

        resolver_result = (
            resolve_from_analysis(

                question=question,

                analysis=analysis
            )
        )


        resolver_status = normalize_text(
            resolver_result.get(
                "status"
            )
        )


        # ----------------------------------------------------
        # 특정 공식 법령 확정
        # ----------------------------------------------------

        if resolver_status == "resolved":

            return (
                collect_resolved_law_bundle(

                    question=question,

                    analysis=analysis,

                    resolved=resolver_result
                )
            )


        # ----------------------------------------------------
        # 여러 법령으로 해석 가능
        # ----------------------------------------------------

        if resolver_status == "ambiguous":

            return collect_topic_bundle(

                question=question,

                analysis=analysis,

                resolver_result=(
                    resolver_result
                )
            )


    # ========================================================
    # 자연어 / unresolved
    # ========================================================

    return collect_topic_bundle(

        question=question,

        analysis=analysis,

        resolver_result=resolver_result
    )