# ============================================================
# Ollama 상태 확인
#
# 역할
# - Ollama 서버 연결 확인
# - 설치된 모델 목록 조회
# - 특정 모델 설치 여부 확인
# ============================================================

import requests

from services.generation.ollama_config import (
    OLLAMA_BASE_URL,
)


# ============================================================
# 1. Ollama 연결 확인
# ============================================================

def check_ollama_connection(
    timeout: int = 5
):
    """
    Ollama 서버가 실행 중인지 확인한다.
    """

    try:

        response = requests.get(

            f"{OLLAMA_BASE_URL}/api/tags",

            timeout=timeout
        )

        return (
            response.status_code
            == 200
        )

    except requests.RequestException:

        return False


# ============================================================
# 2. 설치된 모델 목록
# ============================================================

def get_installed_models(
    timeout: int = 5
):
    """
    현재 Ollama에 설치된 모델 목록 반환.
    """

    try:

        response = requests.get(

            f"{OLLAMA_BASE_URL}/api/tags",

            timeout=timeout
        )

        response.raise_for_status()

        data = response.json()

        models = data.get(
            "models",
            []
        )

        result = []

        for item in models:

            if not isinstance(
                item,
                dict
            ):

                continue

            name = str(
                item.get(
                    "name",
                    ""
                )
                or ""
            ).strip()

            if name:

                result.append(
                    name
                )

        return result

    except requests.RequestException:

        return []

    except ValueError:

        return []


# ============================================================
# 3. 모델 설치 여부
# ============================================================

def is_model_installed(
    model: str
):

    models = get_installed_models()

    return model in models