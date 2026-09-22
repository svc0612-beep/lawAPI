# ============================================================
# Ollama Chat API 클라이언트
#
# 역할
# - /api/chat 호출
# - 요청 payload 구성
# - 오류 처리
# - 응답 JSON 파싱
# ============================================================

import requests

from services.generation.ollama_config import (
    OLLAMA_CHAT_URL,
    DEFAULT_MODEL,
)


# ============================================================
# Ollama Chat API 호출
# ============================================================

def call_ollama_chat(
    messages: list,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.1,
    num_ctx: int = 4096,
    num_predict: int = 700,
    timeout: int = 180
):
    """
    Ollama /api/chat 호출.

    법률 답변 특성상 temperature를 낮게 유지한다.
    """

    # ========================================================
    # 입력 검증
    # ========================================================

    if not isinstance(
        messages,
        list
    ):

        raise TypeError(
            "messages는 list여야 합니다."
        )

    if not messages:

        raise ValueError(
            "messages가 비어 있습니다."
        )

    # ========================================================
    # 요청 데이터
    # ========================================================

    payload = {

        "model":
            model,

        "messages":
            messages,

        "stream":
            False,

        # Qwen3 별도 thinking 출력을 끄고
        # 최종 답변만 받는다.
        "think":
            False,

        "options": {

            "temperature":
                temperature,

            "num_ctx":
                num_ctx,

            "num_predict":
                num_predict,
        },
    }

    # ========================================================
    # API 호출
    # ========================================================

    try:

        response = requests.post(

            OLLAMA_CHAT_URL,

            json=payload,

            timeout=timeout
        )

    except requests.Timeout:

        raise RuntimeError(
            "Ollama 응답 시간이 초과되었습니다."
        )

    except requests.ConnectionError:

        raise RuntimeError(
            "Ollama 서버에 연결할 수 없습니다."
        )

    except requests.RequestException:

        raise RuntimeError(
            "Ollama 요청 중 오류가 발생했습니다."
        )

    # ========================================================
    # HTTP 상태 확인
    # ========================================================

    if response.status_code != 200:

        raise RuntimeError(

            "Ollama API 오류가 발생했습니다. "
            f"HTTP {response.status_code}"
        )

    # ========================================================
    # JSON 파싱
    # ========================================================

    try:

        data = response.json()

    except ValueError:

        raise RuntimeError(
            "Ollama 응답을 JSON으로 해석할 수 없습니다."
        )

    # ========================================================
    # message 확인
    # ========================================================

    message = data.get(
        "message",
        {}
    )

    if not isinstance(
        message,
        dict
    ):

        raise RuntimeError(
            "Ollama 응답에 message가 없습니다."
        )

    content = str(
        message.get(
            "content",
            ""
        )
        or ""
    ).strip()

    if not content:

        raise RuntimeError(
            "LLM이 빈 답변을 반환했습니다."
        )

    # ========================================================
    # 생성 결과
    # ========================================================

    return {

        "model":
            model,

        "answer":
            content,

        "done":
            data.get(
                "done",
                False
            ),

        "done_reason":
            data.get(
                "done_reason"
            ),

        "total_duration":
            data.get(
                "total_duration"
            ),

        "load_duration":
            data.get(
                "load_duration"
            ),

        "prompt_eval_count":
            data.get(
                "prompt_eval_count"
            ),

        "eval_count":
            data.get(
                "eval_count"
            ),
    }