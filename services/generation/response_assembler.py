# ============================================================
# 최종 법률 응답 조립
#
# 역할
# - Python 공식 답변
# - 선택적 LLM 쉬운 설명
# - 공식 Evidence 출처
# - 안내문
#
# 핵심 원칙
# - 법률 사실은 Python + 공식 Evidence가 담당
# - LLM은 선택적 보조 설명만 담당
# ============================================================

from services.generation.response_utils import (
    clean_llm_explanation,
)

from services.generation.response_core import (
    build_core_answer,
)

from services.generation.response_sources import (
    build_source_sections,
)


# ============================================================
# 최종 응답
# ============================================================

def build_final_response(evidence_result: dict, generated_result=None):
    from services.generation.response_sources import build_library_sources
    if not isinstance(evidence_result, dict):
        raise TypeError("evidence_result는 dict여야 합니다.")
    sections = [build_core_answer(evidence_result)]
    library = build_library_sources(evidence_result.get("library_items", []))
    if library:
        sections.append(library)
    # Free-form generated explanations have no claim-level evidence validator.
    # Never publish them as verified legal information.
    return "\n\n".join(sections)
