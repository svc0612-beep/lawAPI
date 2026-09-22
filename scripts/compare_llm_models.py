# ============================================================
# 로컬 LLM 법률 답변 비교 테스트
#
# 목적
# 1. 동일한 Evidence를 사용
# 2. Qwen 1.7B / Gemma 4B 비교
# 3. 검색 결과 차이가 아니라 순수 생성 품질만 비교
#
# 중요:
# - 법률 API 검색은 한 번만 수행한다.
# - 두 모델 모두 동일한 EvidenceBundle을 사용한다.
# ============================================================

import os
import sys
import time


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
# 2. 프로젝트 모듈
# ============================================================

from services.query_service import (
    process_law_question,
)

from services.generation.llm_client import (
    generate_answer,
)

from services.generation.response_builder import (
    build_final_response,
)


# ============================================================
# 3. 비교할 모델
# ============================================================

MODELS = [

    "qwen3:1.7b-q4_K_M",

    "gemma3:4b",
]


# ============================================================
# 4. 테스트 질문
# ============================================================

QUESTION = (
    "특허 침해하면 어떻게 돼?"
)


# ============================================================
# 5. 모델 하나 테스트
# ============================================================

def test_model(
    model: str,
    evidence_result: dict
):

    print()

    print(
        "=" * 80
    )

    print(
        "모델:",
        model
    )

    print(
        "=" * 80
    )


    start_time = time.perf_counter()


    generated = generate_answer(

        result=evidence_result,

        model=model
    )


    end_time = time.perf_counter()


    elapsed = (
        end_time
        - start_time
    )


    final_answer = build_final_response(

        evidence_result=evidence_result,

        generated_result=generated
    )


    print()

    print(
        "상태:",
        generated.get(
            "status"
        )
    )


    print(
        "LLM 호출:",
        generated.get(
            "llm_called"
        )
    )


    print(
        "소요 시간:",
        round(
            elapsed,
            2
        ),
        "초"
    )


    generation_info = generated.get(
        "generation",
        {}
    )


    if generation_info:

        print(
            "입력 토큰:",
            generation_info.get(
                "prompt_eval_count"
            )
        )


        print(
            "생성 토큰:",
            generation_info.get(
                "eval_count"
            )
        )


        print(
            "종료 사유:",
            generation_info.get(
                "done_reason"
            )
        )


    print()

    print(
        "-" * 80
    )

    print(
        "LLM 원본 생성 답변"
    )

    print(
        "-" * 80
    )

    print()

    print(
        generated.get(
            "answer"
        )
    )


    print()

    print(
        "-" * 80
    )

    print(
        "Python 출처 결합 최종 답변"
    )

    print(
        "-" * 80
    )

    print()

    print(
        final_answer
    )


    return {

        "model":
            model,

        "elapsed":
            elapsed,

        "generated":
            generated,

        "final_answer":
            final_answer,
    }


# ============================================================
# 6. 실행
# ============================================================

if __name__ == "__main__":

    print()

    print(
        "=" * 80
    )

    print(
        "로컬 LLM 법률 답변 비교"
    )

    print(
        "=" * 80
    )


    print()

    print(
        "질문:",
        QUESTION
    )


    # ========================================================
    # Evidence는 한 번만 검색
    # ========================================================

    print()

    print(
        "공식 근거 검색 중..."
    )


    evidence_result = process_law_question(
        QUESTION
    )


    print()

    print(
        "근거 존재:",
        evidence_result.get(
            "evidence_found"
        )
    )


    print(
        "관련 법령:",
        len(
            evidence_result.get(
                "laws",
                []
            )
        ),
        "건"
    )


    print(
        "관련 판례:",
        len(
            evidence_result.get(
                "precedents",
                []
            )
        ),
        "건"
    )


    print(
        "법령해석례:",
        len(
            evidence_result.get(
                "interpretations",
                []
            )
        ),
        "건"
    )


    # ========================================================
    # 모델 비교
    # ========================================================

    results = []


    for model in MODELS:

        try:

            result = test_model(

                model=model,

                evidence_result=evidence_result
            )


            results.append(
                result
            )


        except Exception as e:

            print()

            print(
                f"[{model}] 오류:",
                e
            )


    # ========================================================
    # 속도 비교 요약
    # ========================================================

    print()
    print()

    print(
        "=" * 80
    )

    print(
        "비교 요약"
    )

    print(
        "=" * 80
    )


    for result in results:

        print()

        print(
            result.get(
                "model"
            ),
            "→",
            round(
                result.get(
                    "elapsed",
                    0
                ),
                2
            ),
            "초"
        )