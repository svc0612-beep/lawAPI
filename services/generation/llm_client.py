# ============================================================
# Ollama 로컬 LLM 통합 클라이언트
#
# 기존 import 호환성 유지:
#
# from services.generation.llm_client import (
#     generate_answer,
#     call_ollama_chat,
#     check_ollama_connection,
#     get_installed_models,
#     is_model_installed,
# )
#
# 실제 구현은 역할별 모듈로 분리되어 있다.
#
# 중요:
# - 법률 검색은 LLM이 하지 않는다.
# - 공식 근거는 query_service에서 수집한다.
# - LLM은 선택적 보조 설명만 담당한다.
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
# 2. Ollama 설정
# ============================================================

from services.generation.ollama_config import (
    OLLAMA_BASE_URL,
    OLLAMA_CHAT_URL,
    DEFAULT_MODEL,
)


# ============================================================
# 3. Ollama 상태
# ============================================================

from services.generation.ollama_status import (
    check_ollama_connection,
    get_installed_models,
    is_model_installed,
)


# ============================================================
# 4. Ollama Chat
# ============================================================

from services.generation.ollama_chat import (
    call_ollama_chat,
)


# ============================================================
# 5. LLM 생성 서비스
# ============================================================

from services.generation.llm_service import (
    generate_answer,
)


# ============================================================
# 6. 공개 API
# ============================================================

__all__ = [

    "OLLAMA_BASE_URL",

    "OLLAMA_CHAT_URL",

    "DEFAULT_MODEL",

    "check_ollama_connection",

    "get_installed_models",

    "is_model_installed",

    "call_ollama_chat",

    "generate_answer",
]


# ============================================================
# 7. 단독 테스트
#
# 주의:
# 이 파일을 직접 실행하면 명시적으로 LLM을 테스트한다.
#
# response_builder의 기본값은 use_llm=False이므로
# 일반 사용자 응답에서는 자동으로 실행되지 않는다.
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
        "Ollama 법률 보조설명 생성 테스트"
    )

    print(
        "=" * 80
    )

    print(
        "기본 모델:",
        DEFAULT_MODEL
    )

    print()

    print(
        "Ollama 연결:",
        check_ollama_connection()
    )

    installed_models = (
        get_installed_models()
    )

    print(
        "설치된 모델:",
        installed_models
    )

    question = (
        "특허 침해하면 어떻게 돼?"
    )

    print()

    print(
        "=" * 80
    )

    print(
        "사용자 질문:",
        question
    )

    print(
        "=" * 80
    )

    try:

        # ====================================================
        # 1. 공식 근거 검색
        # ====================================================

        evidence_result = (
            process_law_question(
                question
            )
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

        # ====================================================
        # 2. 명시적 LLM 테스트
        # ====================================================

        print()

        print(
            "LLM 보조설명 생성 중..."
        )

        generated = generate_answer(
            result=evidence_result
        )

        print()

        print(
            "=" * 80
        )

        print(
            "생성 결과"
        )

        print(
            "=" * 80
        )

        print(
            "상태:",
            generated.get(
                "status"
            )
        )

        print(
            "모델:",
            generated.get(
                "model"
            )
        )

        print(
            "LLM 호출:",
            generated.get(
                "llm_called"
            )
        )

        print()

        print(
            generated.get(
                "answer"
            )
        )

        generation = generated.get(
            "generation",
            {}
        )

        if generation:

            print()

            print(
                "-" * 80
            )

            print(
                "생성 정보"
            )

            print(
                "-" * 80
            )

            print(
                "종료 사유:",
                generation.get(
                    "done_reason"
                )
            )

            print(
                "입력 토큰:",
                generation.get(
                    "prompt_eval_count"
                )
            )

            print(
                "생성 토큰:",
                generation.get(
                    "eval_count"
                )
            )

    except Exception as e:

        print()

        print(
            "오류:",
            e
        )