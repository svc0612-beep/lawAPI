# ============================================================
# Python 기반 핵심 법률 답변 생성
#
# 이 파일은 최종 진입점만 담당한다.
#
# 역할 분리:
# - response_article.py    : 특정 조문 질문
# - response_organized.py  : OrganizedEvidence 상세 답변
# - response_fallback.py   : aiSearch fallback
# - response_scoring.py    : fallback 점수/텍스트 선택
#
# 핵심 원칙:
# 1. LLM으로 법률 사실을 생성하지 않는다.
# 2. 공식 Evidence만 사용한다.
# 3. 특정 조문 질문은 공식 조문을 그대로 표시한다.
# 4. 자연어 질문은 OrganizedEvidence를 우선 사용한다.
# ============================================================

from typing import (
    Any,
    Dict,
)

from services.generation.response_utils import (
    clean_text,
)

from services.evidence.organizer import (
    organize_evidence,
)

from services.generation.response_article import (
    build_article_core_answer,
)

from services.generation.response_organized import (
    build_organized_core_answer,
)

from services.generation.response_fallback import (
    build_laws_core_answer,
)


def get_organized_result(
    evidence_result: dict
) -> Dict[str, Any]:

    if not isinstance(
        evidence_result,
        dict
    ):
        return {}

    try:

        organized = organize_evidence(
            evidence_result
        )

        if organized is None:
            return {}

        if not hasattr(
            organized,
            "to_dict"
        ):
            return {}

        result = organized.to_dict()

        if isinstance(
            result,
            dict
        ):
            return result

    except Exception:
        return {}

    return {}


def build_core_answer(evidence_result: dict) -> str:
    from services.generation.verified_answer import build_verified_answer
    if not isinstance(evidence_result, dict):
        return ""
    return build_verified_answer(evidence_result)
