# ============================================================
# 쉬운 법률 설명 생성 프롬프트 빌더
#
# 역할
# 1. EvidenceBundle 결과를 받음
# 2. LLM에 필요한 핵심 Evidence만 선별
# 3. 공식 근거 컨텍스트 생성
# 4. LLM은 "쉽게 설명하면" 부분만 생성
#
# 중요:
# - 핵심 법률 답변은 Python이 생성한다.
# - 법령/판례/해석례/도서관 출처도 Python이 생성한다.
# - LLM은 쉬운 설명만 담당한다.
# - 전체 Evidence를 무조건 LLM에 넘기지 않는다.
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
# 2. 내부 모듈
# ============================================================

from services.generation.context_builder import (
    build_evidence_context,
)


# ============================================================
# 3. LLM Evidence 기본 제한
#
# 이미 query_service / reranker에서 정렬된 결과의
# 앞부분만 사용한다.
#
# 특정 법률명이나 특정 주제를 하드코딩하지 않는다.
# ============================================================

DEFAULT_LAW_LIMIT = 5

DEFAULT_PRECEDENT_LIMIT = 3

DEFAULT_INTERPRETATION_LIMIT = 3

DEFAULT_LIBRARY_LIMIT = 2

MAX_LIBRARY_TOC_LIMIT = 5


# ============================================================
# 4. 시스템 프롬프트
# ============================================================

def build_system_prompt():

    return """
너는 대한민국 법률 정보를 쉽게 풀어 설명하는 보조 AI다.

중요:
법적인 핵심 답변과 공식 출처는 다른 Python 시스템이 작성한다.

너는 오직 사용자가 이해하기 쉽도록 설명하는 역할만 한다.

반드시 다음 규칙을 지켜라.

1. 제공된 근거 안에서만 설명한다.

2. 근거에 없는 사실을 추가하지 않는다.

3. 새로운 법률 효과, 조건, 예외, 절차를 만들지 않는다.

4. 새로운 사례나 예시를 만들지 않는다.

5. 법 조문 번호를 새로 작성하지 않는다.

6. 사건번호를 작성하지 않는다.

7. 판례 목록을 작성하지 않는다.

8. 법령해석례를 작성하지 않는다.

9. 국회도서관 자료를 작성하지 않는다.

10. 벌금이나 형량은 근거에 명시된 경우에만 언급한다.

11. 근거의 의미를 넓히거나 좁히지 않는다.

예:

근거:
"그 물건의 생산에만 사용하는 물건"

잘못된 설명:
"그 물건을 생산하거나 판매하면 침해다."

이처럼 법률 요건을 단순화해서
다른 의미로 만들면 안 된다.

12. 주체를 바꾸지 않는다.

예:

"침해한 자가 처벌된다"

라는 근거를

"특허권자가 처벌된다"

라고 바꾸면 안 된다.

13. 법령에서 추정한다고 되어 있는 내용을
새로운 선행 조건이 필요한 것처럼 설명하지 않는다.

14. 판례 제목만 제공된 경우
판결 이유나 결론을 추측하지 않는다.

15. 사용자의 질문과 직접 관련된 근거를 우선해서 설명한다.

16. 여러 근거가 있더라도
질문과 직접 관계없는 내용을 억지로 설명하지 않는다.

17. 답변은 한국어로 작성한다.

18. 출력에는 제목을 붙이지 않는다.

19. 2~5문장 정도의 짧은 설명만 작성한다.

20. 자신 없는 내용은 추가하지 않는다.
""".strip()


# ============================================================
# 5. 안전한 리스트 제한
# ============================================================

def limit_list(
    value,
    limit: int
):

    if not isinstance(
        value,
        list
    ):

        return []


    try:

        limit = int(
            limit
        )

    except (
        TypeError,
        ValueError
    ):

        return []


    if limit <= 0:

        return []


    return value[
        :limit
    ]


# ============================================================
# 6. LLM 전용 Evidence 생성
#
# 원본 result는 수정하지 않는다.
#
# 특정 조문이 존재하면:
# - 해당 article이 가장 직접적인 근거이므로
# - 일반 aiSearch laws를 LLM에 같이 넣지 않는다.
#
# 일반 주제 질문이면:
# - reranking된 상위 Evidence만 사용한다.
# ============================================================

def build_llm_evidence_view(
    result: dict,
    law_limit: int = DEFAULT_LAW_LIMIT,
    precedent_limit: int = DEFAULT_PRECEDENT_LIMIT,
    interpretation_limit: int = DEFAULT_INTERPRETATION_LIMIT,
    library_limit: int = DEFAULT_LIBRARY_LIMIT
):

    if not isinstance(
        result,
        dict
    ):

        raise TypeError(
            "result는 dict여야 합니다."
        )


    article = result.get(
        "article"
    )


    # ========================================================
    # 공통 필드
    # ========================================================

    selected = {

        "status":
            result.get(
                "status"
            ),

        "question_type":
            result.get(
                "question_type",
                ""
            ),

        "original_question":
            result.get(
                "original_question",
                ""
            ),

        "search_query":
            result.get(
                "search_query",
                ""
            ),

        "evidence_found":
            result.get(
                "evidence_found",
                False
            ),

        "article":
            article,

        "laws":
            [],

        "precedents":
            [],

        "interpretations":
            [],

        "library_items":
            [],
    }


    # ========================================================
    # 특정 조문 질문
    #
    # 직접 조회된 article만 LLM에 전달한다.
    #
    # aiSearch로 함께 수집된 일반 관련 법령이
    # 설명의 초점을 흐리는 것을 방지한다.
    # ========================================================

    if article:

        return selected


    # ========================================================
    # 일반 관련 법령 / 주제 질문
    #
    # 이미 정렬된 순서를 그대로 유지하면서
    # 상위 Evidence만 전달한다.
    # ========================================================

    selected[
        "laws"
    ] = limit_list(

        result.get(
            "laws",
            []
        ),

        law_limit
    )


    selected[
        "precedents"
    ] = limit_list(

        result.get(
            "precedents",
            []
        ),

        precedent_limit
    )


    selected[
        "interpretations"
    ] = limit_list(

        result.get(
            "interpretations",
            []
        ),

        interpretation_limit
    )


    selected[
        "library_items"
    ] = limit_list(

        result.get(
            "library_items",
            []
        ),

        library_limit
    )


    return selected


# ============================================================
# 7. Evidence 존재 여부
# ============================================================

def has_evidence(
    result: dict
):

    if not isinstance(
        result,
        dict
    ):

        return False


    if result.get(
        "article"
    ):

        return True


    if result.get(
        "laws"
    ):

        return True


    if result.get(
        "precedents"
    ):

        return True


    if result.get(
        "interpretations"
    ):

        return True


    if result.get(
        "library_items"
    ):

        return True


    return False


# ============================================================
# 8. 국회도서관 목차 제한 정규화
# ============================================================

def normalize_library_toc_limit(
    value
):

    try:

        value = int(
            value
        )

    except (
        TypeError,
        ValueError
    ):

        return MAX_LIBRARY_TOC_LIMIT


    if value < 0:

        return 0


    return min(
        value,
        MAX_LIBRARY_TOC_LIMIT
    )


# ============================================================
# 9. 사용자 프롬프트
# ============================================================

def build_user_prompt(
    result: dict,
    library_toc_limit: int = MAX_LIBRARY_TOC_LIMIT,
    law_limit: int = DEFAULT_LAW_LIMIT,
    precedent_limit: int = DEFAULT_PRECEDENT_LIMIT,
    interpretation_limit: int = DEFAULT_INTERPRETATION_LIMIT,
    library_limit: int = DEFAULT_LIBRARY_LIMIT
):

    if not isinstance(
        result,
        dict
    ):

        raise TypeError(
            "result는 dict여야 합니다."
        )


    question = str(
        result.get(
            "original_question",
            ""
        )
        or ""
    ).strip()


    # ========================================================
    # LLM에 넘길 Evidence 축소
    # ========================================================

    llm_result = build_llm_evidence_view(

        result=result,

        law_limit=law_limit,

        precedent_limit=precedent_limit,

        interpretation_limit=interpretation_limit,

        library_limit=library_limit
    )


    # ========================================================
    # 국회도서관 목차 제한
    #
    # llm_service에서 더 큰 값을 넘겨도
    # 최대 5개까지만 LLM에 전달한다.
    # ========================================================

    effective_toc_limit = (
        normalize_library_toc_limit(
            library_toc_limit
        )
    )


    context = build_evidence_context(

        result=llm_result,

        include_policy=False,

        library_toc_limit=effective_toc_limit
    )


    return f"""
사용자 질문:
{question}

아래 근거 내용을 벗어나지 않는 범위에서
사용자가 이해하기 쉽게 설명하라.

특히 사용자 질문과 직접 관련된 근거를 먼저 보고,
관련성이 낮은 내용은 설명하지 마라.

==============================
근거
==============================

{context}

==============================
출력 규칙
==============================

쉬운 설명만 작성한다.

제목을 작성하지 않는다.

법령 목록을 작성하지 않는다.

판례 목록을 작성하지 않는다.

법령해석례 목록을 작성하지 않는다.

국회도서관 자료 목록을 작성하지 않는다.

새로운 예시를 만들지 않는다.

근거에 없는 조건을 추가하지 않는다.

근거의 법적 의미를 변경하지 않는다.

질문과 직접 관련되지 않은 근거를 억지로 설명하지 않는다.

2~5문장으로 작성한다.
""".strip()


# ============================================================
# 10. Chat messages
# ============================================================

def build_messages(
    result: dict,
    library_toc_limit: int = MAX_LIBRARY_TOC_LIMIT,
    law_limit: int = DEFAULT_LAW_LIMIT,
    precedent_limit: int = DEFAULT_PRECEDENT_LIMIT,
    interpretation_limit: int = DEFAULT_INTERPRETATION_LIMIT,
    library_limit: int = DEFAULT_LIBRARY_LIMIT
):

    return [

        {
            "role":
                "system",

            "content":
                build_system_prompt(),
        },

        {
            "role":
                "user",

            "content":
                build_user_prompt(

                    result=result,

                    library_toc_limit=library_toc_limit,

                    law_limit=law_limit,

                    precedent_limit=precedent_limit,

                    interpretation_limit=interpretation_limit,

                    library_limit=library_limit
                ),
        },
    ]


# ============================================================
# 11. Fallback
# ============================================================

def build_fallback_answer(
    result: dict
):

    if has_evidence(
        result
    ):

        return None


    return (
        "확인 가능한 근거를 찾지 못했습니다."
    )


# ============================================================
# 12. 생성 준비
# ============================================================

def prepare_answer_generation(
    result: dict,
    library_toc_limit: int = MAX_LIBRARY_TOC_LIMIT,
    law_limit: int = DEFAULT_LAW_LIMIT,
    precedent_limit: int = DEFAULT_PRECEDENT_LIMIT,
    interpretation_limit: int = DEFAULT_INTERPRETATION_LIMIT,
    library_limit: int = DEFAULT_LIBRARY_LIMIT
):

    fallback_answer = (
        build_fallback_answer(
            result
        )
    )


    if fallback_answer:

        return {

            "should_generate":
                False,

            "fallback_answer":
                fallback_answer,

            "messages":
                [],

            "selection":
                {
                    "article":
                        0,

                    "laws":
                        0,

                    "precedents":
                        0,

                    "interpretations":
                        0,

                    "library_items":
                        0,
                },
        }


    # ========================================================
    # 실제 LLM용 Evidence
    # ========================================================

    llm_result = build_llm_evidence_view(

        result=result,

        law_limit=law_limit,

        precedent_limit=precedent_limit,

        interpretation_limit=interpretation_limit,

        library_limit=library_limit
    )


    messages = build_messages(

        result=result,

        library_toc_limit=library_toc_limit,

        law_limit=law_limit,

        precedent_limit=precedent_limit,

        interpretation_limit=interpretation_limit,

        library_limit=library_limit
    )


    # ========================================================
    # 테스트 / 디버깅용 선별 개수
    #
    # API Key나 민감정보는 포함하지 않는다.
    # ========================================================

    selection = {

        "article":
            (
                1
                if llm_result.get(
                    "article"
                )
                else 0
            ),

        "laws":
            len(
                llm_result.get(
                    "laws",
                    []
                )
            ),

        "precedents":
            len(
                llm_result.get(
                    "precedents",
                    []
                )
            ),

        "interpretations":
            len(
                llm_result.get(
                    "interpretations",
                    []
                )
            ),

        "library_items":
            len(
                llm_result.get(
                    "library_items",
                    []
                )
            ),
    }


    return {

        "should_generate":
            True,

        "fallback_answer":
            None,

        "messages":
            messages,

        "selection":
            selection,
    }


# ============================================================
# 13. 테스트
# ============================================================

if __name__ == "__main__":

    from services.query_service import (
        process_law_question,
    )


    question = (
        "특허 침해하면 어떻게 돼?"
    )


    result = process_law_question(
        question
    )


    prepared = prepare_answer_generation(
        result
    )


    print()

    print(
        "=" * 80
    )

    print(
        "쉬운 설명 전용 프롬프트 테스트"
    )

    print(
        "=" * 80
    )


    print(
        "LLM 생성 여부:",
        prepared.get(
            "should_generate"
        )
    )


    print(
        "Fallback:",
        prepared.get(
            "fallback_answer"
        )
    )


    print(
        "선별 Evidence:",
        prepared.get(
            "selection"
        )
    )


    messages = prepared.get(
        "messages",
        []
    )


    print(
        "messages 개수:",
        len(
            messages
        )
    )


    for index, message in enumerate(
        messages,
        start=1
    ):

        print()

        print(
            "=" * 80
        )

        print(
            f"Message {index}"
        )

        print(
            "role:",
            message.get(
                "role"
            )
        )

        print(
            "=" * 80
        )

        print(
            message.get(
                "content"
            )
        )