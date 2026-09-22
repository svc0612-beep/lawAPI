# ============================================================
# 법률 Evidence → LLM용 컨텍스트 변환기
#
# 역할
# 1. EvidenceBundle dict를 입력받음
# 2. 각 Evidence 변환 모듈 호출
# 3. LLM에 전달할 하나의 컨텍스트 문자열 생성
#
# 중요:
# - 새로운 법률 사실을 만들지 않는다.
# - Evidence에 있는 내용만 사용한다.
# - 법령 근거를 가장 우선한다.
# - 기존 공개 함수 import 호환성을 유지한다.
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
# 2. 공통 유틸
# ============================================================

from services.generation.context_utils import (
    normalize_text,
    has_text,
    make_article_label,
)


# ============================================================
# 3. 법령
# ============================================================

from services.generation.context_law import (
    build_article_context,
    build_laws_context,
)


# ============================================================
# 4. 판례 / 법령해석례
# ============================================================

from services.generation.context_case import (
    build_precedents_context,
    build_interpretations_context,
)


# ============================================================
# 5. 국회도서관
# ============================================================

from services.generation.context_library import (
    build_library_context,
)


# ============================================================
# 6. 근거 정책
# ============================================================

from services.generation.context_policy import (
    build_source_policy,
)


# ============================================================
# 7. EvidenceBundle 전체 → LLM 컨텍스트
# ============================================================

def build_evidence_context(
    result: dict,
    include_policy: bool = True,
    library_toc_limit: int = 20
):
    """
    process_law_question() 결과를 받아
    LLM에 전달할 하나의 문자열로 변환한다.
    """

    if not isinstance(
        result,
        dict
    ):

        raise TypeError(
            "result는 dict여야 합니다."
        )

    sections = []

    # ========================================================
    # 질문 정보
    # ========================================================

    original_question = normalize_text(
        result.get(
            "original_question"
        )
    )

    search_query = normalize_text(
        result.get(
            "search_query"
        )
    )

    question_type = normalize_text(
        result.get(
            "question_type"
        )
    )

    question_lines = [
        "[질문 정보]",
    ]

    if original_question:

        question_lines.append(
            f"사용자 질문: "
            f"{original_question}"
        )

    if search_query:

        question_lines.append(
            f"정규화 검색어: "
            f"{search_query}"
        )

    if question_type:

        question_lines.append(
            f"질문 유형: "
            f"{question_type}"
        )

    sections.append(
        "\n".join(
            question_lines
        )
    )

    # ========================================================
    # 근거 사용 원칙
    # ========================================================

    if include_policy:

        sections.append(
            build_source_policy()
        )

    # ========================================================
    # 특정 조문
    # ========================================================

    article_context = build_article_context(
        result.get(
            "article"
        )
    )

    if article_context:

        sections.append(
            article_context
        )

    # ========================================================
    # 관련 법령
    # ========================================================

    laws_context = build_laws_context(
        result.get(
            "laws",
            []
        )
    )

    if laws_context:

        sections.append(
            laws_context
        )

    # ========================================================
    # 법령해석례
    #
    # 기존 순서를 유지한다.
    # 판례보다 먼저 둔다.
    # ========================================================

    interpretations_context = (
        build_interpretations_context(
            result.get(
                "interpretations",
                []
            )
        )
    )

    if interpretations_context:

        sections.append(
            interpretations_context
        )

    # ========================================================
    # 판례
    # ========================================================

    precedents_context = (
        build_precedents_context(
            result.get(
                "precedents",
                []
            )
        )
    )

    if precedents_context:

        sections.append(
            precedents_context
        )

    # ========================================================
    # 국회도서관
    # ========================================================

    library_context = build_library_context(

        result.get(
            "library_items",
            []
        ),

        toc_limit=library_toc_limit
    )

    if library_context:

        sections.append(
            library_context
        )

    # ========================================================
    # 근거 없음
    # ========================================================

    evidence_found = result.get(
        "evidence_found",
        False
    )

    if not evidence_found:

        sections.append(

            "\n".join(
                [

                    "[근거 확인 결과]",

                    "확인 가능한 공식 근거를 "
                    "찾지 못했습니다.",
                ]
            )
        )

    return "\n\n".join(
        sections
    ).strip()


# ============================================================
# 8. 기존 공개 API 호환
# ============================================================

__all__ = [

    "normalize_text",

    "has_text",

    "make_article_label",

    "build_article_context",

    "build_laws_context",

    "build_precedents_context",

    "build_interpretations_context",

    "build_library_context",

    "build_source_policy",

    "build_evidence_context",
]


# ============================================================
# 9. 단독 테스트
# ============================================================

if __name__ == "__main__":

    from services.query_service import (
        process_law_question,
    )

    print()

    print(
        "=" * 80
    )

    print(
        "Evidence → LLM Context 테스트"
    )

    print(
        "=" * 80
    )

    test_question = (
        "특허 침해하면 어떻게 돼?"
    )

    try:

        result = process_law_question(
            test_question
        )

        context = build_evidence_context(
            result
        )

        print()

        print(
            context
        )

        print()

        print(
            "=" * 80
        )

        print(
            "컨텍스트 길이:",
            len(
                context
            ),
            "문자"
        )

    except Exception as e:

        print()

        print(
            "오류:",
            e
        )