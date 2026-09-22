# ============================================================
# 최종 법률 응답 서비스
#
# 흐름
#
# 사용자 질문
#   ↓
# 공식 Evidence 검색
#   ↓
# Python 핵심 법률 답변
#   ↓
# 공식 출처
#   ↓
# 최종 답변
#
# 선택적으로 use_llm=True일 때만
# LLM 쉬운 설명을 추가한다.
#
# 핵심 원칙
# - 법률 사실은 공식 Evidence 기반
# - 기본값은 LLM 사용 안 함
# - LLM은 보조 설명 전용
# ============================================================

import os
import sys


# ============================================================
# 1. 프로젝트 루트 등록
# ============================================================

CURRENT_DIR = os.path.dirname(
    os.path.abspath(__file__)
)


PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        CURRENT_DIR
    )
)


if PROJECT_ROOT not in sys.path:

    sys.path.append(
        PROJECT_ROOT
    )


# ============================================================
# 2. 프로젝트 서비스
# ============================================================

from services.query_service import (
    process_law_question,
)


from services.generation.llm_client import (
    generate_answer,
)


# ============================================================
# 3. 기존 함수 호환성 재노출
# ============================================================

from services.generation.response_utils import (
    clean_text,
    format_date,
    make_article_label,
    clean_llm_explanation,
)


from services.generation.response_core import (
    build_article_core_answer,
    build_laws_core_answer,
    build_core_answer,
)


from services.generation.response_sources import (
    build_article_source,
    build_law_sources,
    build_precedent_sources,
    build_interpretation_sources,
    build_library_sources,
    build_source_sections,
)


from services.generation.response_assembler import (
    build_final_response,
)


# ============================================================
# 4. 질문 → 검색 → 선택적 LLM → 최종 답변
# ============================================================

def answer_question(question: str, model: str = None, control_numbers=None, use_llm: bool = False):
    evidence = process_law_question(question=question, control_numbers=control_numbers)
    return {
        "status": evidence.get("status", "partial"), "question": question,
        "evidence": evidence, "generation": None,
        "answer": build_final_response(evidence), "llm_used": False,
        "generation_status": "disabled_pending_claim_validation" if use_llm else "not_requested",
    }


# ============================================================
# 5. 공개 API
# ============================================================

__all__ = [

    "clean_text",

    "format_date",

    "make_article_label",

    "clean_llm_explanation",

    "build_article_core_answer",

    "build_laws_core_answer",

    "build_core_answer",

    "build_article_source",

    "build_law_sources",

    "build_precedent_sources",

    "build_interpretation_sources",

    "build_library_sources",

    "build_source_sections",

    "build_final_response",

    "answer_question",
]


# ============================================================
# 6. 단독 테스트
#
# 기본 테스트에서는 LLM을 사용하지 않는다.
# ============================================================

if __name__ == "__main__":

    print()

    print(
        "=" * 80
    )

    print(
        "Python 공식 Evidence 기반 법률답변 테스트"
    )

    print(
        "=" * 80
    )


    question = (
        "특허 침해하면 어떻게 돼?"
    )


    print()

    print(
        "사용자 질문:",
        question
    )


    print()

    print(
        "답변 생성 중..."
    )


    try:

        # ====================================================
        # 기본값:
        # use_llm=False
        #
        # LLM을 호출하지 않는다.
        # ====================================================

        result = answer_question(
            question=question
        )


        print()

        print(
            "=" * 80
        )

        print(
            "최종 답변"
        )

        print(
            "=" * 80
        )


        print()

        print(
            result.get(
                "answer"
            )
        )


        print()

        print(
            "=" * 80
        )

        print(
            "응답 정보"
        )

        print(
            "=" * 80
        )


        print(
            "상태:",
            result.get(
                "status"
            )
        )


        print(
            "LLM 사용:",
            result.get(
                "llm_used"
            )
        )


        generation = result.get(
            "generation"
        )


        print(
            "generation:",
            (
                "있음"
                if generation
                else "없음"
            )
        )


    except Exception as e:

        print()

        print(
            "오류:",
            e
        )