# ============================================================
# Evidence 기반 LLM 생성 서비스
#
# 역할
# - answer_generator 결과 확인
# - 근거가 없으면 LLM 호출 차단
# - Ollama 연결 확인
# - 모델 설치 확인
# - 실제 생성 실행
#
# 중요:
# 법률 검색은 LLM이 하지 않는다.
# 공식 근거는 query_service에서 이미 수집한다.
# ============================================================

from services.generation.answer_generator import (
    prepare_answer_generation,
)

from services.generation.ollama_config import (
    DEFAULT_MODEL,
)

from services.generation.ollama_status import (
    check_ollama_connection,
    is_model_installed,
)

from services.generation.ollama_chat import (
    call_ollama_chat,
)


# ============================================================
# Evidence → LLM 쉬운 설명 생성
# ============================================================

def generate_answer(
    result: dict,
    model: str = DEFAULT_MODEL,
    library_toc_limit: int = 20
):
    """
    query_service 결과를 받아
    근거 범위 안에서 자연어 설명을 생성한다.
    """

    # ========================================================
    # 1. LLM 입력 준비
    # ========================================================

    prepared = prepare_answer_generation(

        result=result,

        library_toc_limit=library_toc_limit
    )

    # ========================================================
    # 2. 근거 없음
    #
    # 공식 근거가 없으면 LLM 자체를 호출하지 않는다.
    # ========================================================

    if not prepared.get(
        "should_generate",
        False
    ):

        return {

            "status":
                "fallback",

            "model":
                None,

            "answer":
                prepared.get(
                    "fallback_answer"
                ),

            "llm_called":
                False,
        }

    # ========================================================
    # 3. Ollama 연결 확인
    # ========================================================

    if not check_ollama_connection():

        return {

            "status":
                "error",

            "model":
                model,

            "answer":
                "Ollama 서버에 연결할 수 없습니다.",

            "llm_called":
                False,
        }

    # ========================================================
    # 4. 모델 설치 확인
    # ========================================================

    if not is_model_installed(
        model
    ):

        return {

            "status":
                "error",

            "model":
                model,

            "answer":
                f"설치되지 않은 Ollama 모델입니다: {model}",

            "llm_called":
                False,
        }

    # ========================================================
    # 5. 실제 LLM 호출
    # ========================================================

    generated = call_ollama_chat(

        messages=prepared.get(
            "messages",
            []
        ),

        model=model
    )

    # ========================================================
    # 6. 최종 결과
    # ========================================================

    return {

        "status":
            "success",

        "model":
            generated.get(
                "model"
            ),

        "answer":
            generated.get(
                "answer"
            ),

        "llm_called":
            True,

        "generation": {

            "done":
                generated.get(
                    "done"
                ),

            "done_reason":
                generated.get(
                    "done_reason"
                ),

            "total_duration":
                generated.get(
                    "total_duration"
                ),

            "load_duration":
                generated.get(
                    "load_duration"
                ),

            "prompt_eval_count":
                generated.get(
                    "prompt_eval_count"
                ),

            "eval_count":
                generated.get(
                    "eval_count"
                ),
        },
    }