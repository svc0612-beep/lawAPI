import json
import os
import re
from collections import Counter
from functools import lru_cache
from typing import Any, Dict, List, Tuple
import requests
from core.config import (
    LAW_API_KEY,
    LAW_SEARCH_URL,
    validate_law_api_key,
)
from services.generation.ollama_chat import call_ollama_chat
from services.generation.ollama_status import (
    check_ollama_connection,
    is_model_installed,
)
from services.law.ai_search import search_related_laws
from services.law.reranker import rerank_law_results
from services.law.query_expansion_family_search import (
    prefer_family_root_items,
    search_combined_family_results,
)
QUERY_EXPANSION_ENABLED = (
    os.getenv("LAW_QUERY_EXPANSION_ENABLED", "1").strip().lower()
    not in {"0", "false", "off", "no"}
)
QUERY_EXPANSION_DEBUG = (
    os.getenv("LAW_QUERY_EXPANSION_DEBUG", "0").strip().lower()
    in {"1", "true", "on", "yes"}
)
QUERY_EXPANSION_MODEL = (
    os.getenv(
        "LAW_QUERY_EXPANSION_MODEL",
        os.getenv("LEGAL_RAG_MODEL", "qwen3:1.7b-q4_K_M"),
    ).strip()
    or "qwen3:1.7b-q4_K_M"
)
BASE_LOCK_MIN_RESULT_COUNT = 10
BASE_LOCK_MIN_TOP_SHARE = 0.60
BASE_LOCK_MAX_TOP5_UNIQUE = 2
EXPANSION_MIN_TOP_SHARE = 0.40
EXPANSION_MAX_UNIQUE_LAWS = 10
EXPANSION_MAX_TOP5_UNIQUE = 4
CROSS_FAMILY_MIN_TOP_SHARE = 0.70
CROSS_FAMILY_MAX_UNIQUE_LAWS = 6
CROSS_FAMILY_MAX_TOP5_UNIQUE = 2
SYSTEM_PROMPT = """
너의 역할은 대한민국 법령 검색을 위한 '법률 검색어 정규화기'다.
법률 상담이나 답변을 작성하지 마라.
처벌, 손해배상액, 과태료, 구제결과를 추측하지 마라.
특정 법률명을 추측해서 만들지 마라.
사용자의 일상 표현을 법령에서 실제로 사용될 가능성이 높은
짧고 일반적인 법률 개념어로 바꿔라.
규칙:
1. 반드시 JSON 배열만 출력한다.
2. 문자열은 1개 또는 2개만 출력한다.
3. 각 문자열은 가능한 한 짧은 독립 법률용어로 만든다.
4. 질문보다 더 특수한 제도나 예외 상황으로 좁히지 않는다.
5. '범죄', '책임', '위반결과'처럼 지나치게 넓은 단어만 출력하지 않는다.
6. 어색한 새 합성어를 만들지 않는다.
7. 질문의 핵심 행위와 객체는 유지한다.
8. 법령 검색에 도움이 되는 표준적인 법률 용어가 있으면 그것을 우선한다.
9. 확신이 낮으면 원문의 핵심 명사/행위를 그대로 사용한다.
10. 설명, 이유, 마크다운, 코드블록은 출력하지 않는다.
출력 형식:
["용어1", "용어2"]
""".strip()
RECOVERY_SYSTEM_PROMPT = """
너의 역할은 대한민국 법령 검색을 위한 '보수적 검색어 복구기'다.
앞선 검색어 후보가 공식 법령용어 검증 또는 검색 선택성 검사를
통과하지 못했을 때만 호출된다.
법률 상담이나 답변을 작성하지 마라.
처벌 수위, 손해배상 결과, 범죄 의도, 구제수단을 추측하지 마라.
특정 법률명을 추측해서 만들지 마라.
사용자 질문에 없는 사실이나 의도를 추가하지 마라.
규칙:
1. 반드시 JSON 배열만 출력한다.
2. 문자열은 1개 또는 2개만 출력한다.
3. 질문 속 구체적인 대상 명사를 최대한 보존한다.
4. 특별한 제도명, 지원제도명, 청구절차명보다 더 기본적인 법률 개념어를 우선한다.
5. 질문이 '안 하다', '안 주다', '못 받다' 같은 미이행/미지급 상황이면
   원래 대상 개념을 보존하고 직접적인 상태 표현을 사용한다.
6. 질문보다 더 좁은 예외 상황이나 특수 제도로 바꾸지 않는다.
7. '범죄', '책임', '처벌', '손해'처럼 너무 넓은 단어만 단독으로 출력하지 않는다.
8. 어색한 새 합성어를 만들지 않는다.
9. 법률명을 출력하지 않는다.
10. 설명, 이유, 마크다운, 코드블록을 출력하지 않는다.
출력 형식:
["기본개념", "직접상태"]
""".strip()
def _debug(*values) -> None:
    if QUERY_EXPANSION_DEBUG:
        print("[QUERY EXPANSION]", *values)
def _clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()
def _compact_text(value: Any) -> str:
    return re.sub(r"\s+", "", _clean_text(value))
def _normalize_search_input(value: Any) -> str:
    text = _clean_text(value)
    text = re.sub(r"[?？!！.。]+$", "", text).strip()
    return text
def _normalize_law_family_name(law_name: str) -> str:
    law_name = _clean_text(law_name)
    for suffix in (" 시행규칙", " 시행령"):
        if law_name.endswith(suffix):
            return law_name[:-len(suffix)].strip()
    return law_name
def _make_result_key(item: dict) -> Tuple:
    return (
        _clean_text(item.get("law_name")),
        item.get("article_number"),
        item.get("sub_article_number", 0),
        _clean_text(item.get("article_title")),
    )
def _merge_results(result_groups: List[List[dict]]) -> List[dict]:
    merged = []
    seen = set()
    for group in result_groups:
        if not isinstance(group, list):
            continue
        for item in group:
            if not isinstance(item, dict):
                continue
            key = _make_result_key(item)
            if key in seen:
                continue
            seen.add(key)
            merged.append(item)
    return merged


def _attach_query_expansion_terms(
    results: List[dict],
    terms: List[str],
) -> List[dict]:
    """
    Query Expansion은 법률 사실을 만드는 단계가 아니라
    검색 의미를 보완하는 단계다.

    Direct Basis 단계가 "월급 → 임금/지급",
    "욕을 올림 → 명예훼손"처럼 검색 단계에서 이미 확보한
    의미 보조어를 다시 잃지 않도록 결과 메타데이터에 보존한다.

    법령명/조문번호/분야별 synonym 하드코딩은 사용하지 않는다.
    """

    clean_terms = []

    for term in terms or []:

        term = _clean_text(
            term
        )

        if (
            term
            and
            term not in clean_terms
        ):

            clean_terms.append(
                term
            )

    attached = []

    for item in results or []:

        if not isinstance(
            item,
            dict
        ):
            continue

        updated = dict(
            item
        )

        updated[
            "query_expansion_terms"
        ] = list(
            clean_terms
        )

        attached.append(
            updated
        )

    return attached
def _summarize_results(results: List[dict]) -> Dict[str, Any]:
    law_names = [
        _clean_text(item.get("law_name"))
        for item in results
        if isinstance(item, dict) and _clean_text(item.get("law_name"))
    ]
    counter = Counter(law_names)
    total = len(results)
    top_law = ""
    top_law_count = 0
    if counter:
        top_law, top_law_count = counter.most_common(1)[0]
    top5_laws = []
    for item in results[:5]:
        if not isinstance(item, dict):
            continue
        law_name = _clean_text(item.get("law_name"))
        if law_name and law_name not in top5_laws:
            top5_laws.append(law_name)
    return {
        "result_count": total,
        "unique_law_count": len(counter),
        "top_law": top_law,
        "top_law_family": _normalize_law_family_name(top_law),
        "top_law_count": top_law_count,
        "top_law_share": round(top_law_count / total, 3) if total else 0.0,
        "top5_unique_laws": len(top5_laws),
        "top5_laws": top5_laws,
    }
def _should_lock_base_family(summary: Dict[str, Any]) -> bool:
    return (
        summary.get("result_count", 0) >= BASE_LOCK_MIN_RESULT_COUNT
        and summary.get("top_law_share", 0.0) >= BASE_LOCK_MIN_TOP_SHARE
        and summary.get("top5_unique_laws", 999) <= BASE_LOCK_MAX_TOP5_UNIQUE
        and bool(summary.get("top_law_family"))
    )
def _is_standard_selective(summary: Dict[str, Any]) -> bool:
    return (
        summary.get("top_law_share", 0.0) >= EXPANSION_MIN_TOP_SHARE
        and summary.get("unique_law_count", 999) <= EXPANSION_MAX_UNIQUE_LAWS
        and summary.get("top5_unique_laws", 999) <= EXPANSION_MAX_TOP5_UNIQUE
    )
def _is_cross_family_selective(summary: Dict[str, Any]) -> bool:
    return (
        summary.get("top_law_share", 0.0) >= CROSS_FAMILY_MIN_TOP_SHARE
        and summary.get("unique_law_count", 999) <= CROSS_FAMILY_MAX_UNIQUE_LAWS
        and summary.get("top5_unique_laws", 999) <= CROSS_FAMILY_MAX_TOP5_UNIQUE
    )
def _expansion_score(summary: Dict[str, Any]) -> float:
    share = float(summary.get("top_law_share", 0.0))
    unique_count = int(summary.get("unique_law_count", 20))
    top5_unique = int(summary.get("top5_unique_laws", 5))
    uniqueness_bonus = max(0.0, (20 - unique_count) / 20)
    top5_focus_bonus = max(0.0, (5 - top5_unique) / 5)
    return round(
        share * 0.60
        + uniqueness_bonus * 0.25
        + top5_focus_bonus * 0.15,
        4,
    )
def _parse_json_array(text: str) -> List[str]:
    text = _clean_text(text)
    if not text:
        return []
    candidates = [text]
    match = re.search(r"\[[\s\S]*\]", text)
    if match and match.group(0) not in candidates:
        candidates.append(match.group(0))
    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if not isinstance(parsed, list):
            continue
        terms = []
        for item in parsed:
            if not isinstance(item, str):
                continue
            term = _clean_text(item)
            if term and term not in terms:
                terms.append(term)
            if len(terms) >= 2:
                break
        return terms
    return []
@lru_cache(maxsize=256)
def _generate_expansion_terms(query: str) -> Tuple[str, ...]:
    if not QUERY_EXPANSION_ENABLED:
        return tuple()
    query = _clean_text(query)
    if not query:
        return tuple()
    try:
        if not check_ollama_connection():
            return tuple()
        if not is_model_installed(QUERY_EXPANSION_MODEL):
            return tuple()
        generated = call_ollama_chat(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": query},
            ],
            model=QUERY_EXPANSION_MODEL,
            temperature=0.0,
            num_ctx=2048,
            num_predict=80,
            timeout=180,
        )
    except Exception:
        return tuple()
    terms = _parse_json_array(generated.get("answer", ""))
    _debug("generated terms:", terms)
    return tuple(terms)
@lru_cache(maxsize=256)
def _generate_recovery_terms(query: str) -> Tuple[str, ...]:
    if not QUERY_EXPANSION_ENABLED:
        return tuple()
    query = _clean_text(query)
    if not query:
        return tuple()
    try:
        if not check_ollama_connection():
            return tuple()
        if not is_model_installed(QUERY_EXPANSION_MODEL):
            return tuple()
        generated = call_ollama_chat(
            messages=[
                {"role": "system", "content": RECOVERY_SYSTEM_PROMPT},
                {"role": "user", "content": query},
            ],
            model=QUERY_EXPANSION_MODEL,
            temperature=0.0,
            num_ctx=2048,
            num_predict=80,
            timeout=180,
        )
    except Exception:
        return tuple()
    terms = _parse_json_array(generated.get("answer", ""))
    _debug("recovery generated terms:", terms)
    return tuple(terms)
def _extract_lstrm_terms(data: Any) -> List[str]:
    results = []
    def walk(value: Any) -> None:
        if isinstance(value, dict):
            term = value.get("법령용어명") or value.get("법령용어명_한글")
            term = _clean_text(term)
            if term and term not in results:
                results.append(term)
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)
    walk(data)
    return results
@lru_cache(maxsize=512)
def _search_official_terms(query: str) -> Tuple[str, ...]:
    query = _clean_text(query)
    if not query:
        return tuple()
    try:
        validate_law_api_key()
        response = requests.get(
            LAW_SEARCH_URL,
            params={
                "OC": LAW_API_KEY,
                "target": "lstrmAI",
                "type": "JSON",
                "query": query,
                "display": 20,
                "page": 1,
            },
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError, RuntimeError):
        return tuple()
    return tuple(_extract_lstrm_terms(data))
def _is_officially_validated_term(term: str) -> bool:
    term = _clean_text(term)
    if not term:
        return False
    official_terms = _search_official_terms(term)
    if not official_terms:
        return False
    target = _compact_text(term)
    for official_term in official_terms:
        if _compact_text(official_term) == target:
            return True
    return False
def _validate_generated_terms(
    terms: Tuple[str, ...],
    label: str = "primary",
) -> List[str]:
    validated = []
    for term in terms:
        if _is_officially_validated_term(term):
            if term not in validated:
                validated.append(term)
        else:
            _debug(f"{label} official term rejected:", term)
    _debug(f"{label} validated terms:", validated)
    return validated
def _validated_terms(query: str) -> List[str]:
    return _validate_generated_terms(
        _generate_expansion_terms(query),
        label="primary",
    )
def _validated_recovery_terms(
    query: str,
    exclude_terms: List[str] = None,
) -> List[str]:
    exclude = {
        _compact_text(term)
        for term in (exclude_terms or [])
        if _clean_text(term)
    }
    generated = tuple(
        term
        for term in _generate_recovery_terms(query)
        if _compact_text(term) not in exclude
    )
    return _validate_generated_terms(
        generated,
        label="recovery",
    )
def _same_law_family(law_name: str, family_name: str) -> bool:
    return _normalize_law_family_name(law_name) == family_name
def _locked_family_expansion_results(
    terms: List[str],
    locked_family: str,
) -> Tuple[List[dict], List[str]]:
    added_results = []
    accepted_terms = []
    for term in terms:
        try:
            term_results = search_related_laws(query=term, display=20)
        except Exception:
            continue
        family_results = [
            item
            for item in term_results
            if isinstance(item, dict)
            and _same_law_family(item.get("law_name", ""), locked_family)
        ]
        family_in_top5 = any(
            isinstance(item, dict)
            and _same_law_family(item.get("law_name", ""), locked_family)
            for item in term_results[:5]
        )
        if len(family_results) < 2 or not family_in_top5:
            _debug("locked-family term rejected:", term)
            continue
        accepted_terms.append(term)
        added_results.extend(family_results)
    return added_results, accepted_terms
def _get_family_support(
    results: List[dict],
) -> Tuple[Counter, set]:
    counts = Counter()
    top5_families = set()
    for index, item in enumerate(results):
        if not isinstance(item, dict):
            continue
        family = _normalize_law_family_name(
            item.get("law_name", "")
        )
        if not family:
            continue
        counts[family] += 1
        if index < 5:
            top5_families.add(family)
    return counts, top5_families
def _filter_family_results(
    results: List[dict],
    family: str,
) -> List[dict]:
    return [
        item
        for item in results
        if isinstance(item, dict)
        and _same_law_family(
            item.get("law_name", ""),
            family,
        )
    ]
def _select_family_consensus(
    terms: List[str],
    base_results: List[dict],
    base_summary: Dict[str, Any],
) -> Tuple[List[dict], List[str], str]:
    if not terms:
        return [], [], ""
    base_family = _clean_text(
        base_summary.get("top_law_family")
    )
    base_count = int(
        base_summary.get("top_law_count", 0)
        or 0
    )
    base_share = float(
        base_summary.get("top_law_share", 0.0)
        or 0.0
    )
    base_supported = bool(
        base_family
        and base_count >= 4
        and base_share >= 0.20
    )
    profiles = []
    for term in terms:
        try:
            term_results = search_related_laws(
                query=term,
                display=20,
            )
        except Exception:
            continue
        if not term_results:
            continue
        counts, top5_families = _get_family_support(
            term_results
        )
        supported_families = {
            family
            for family, count in counts.items()
            if count >= 2
            or family in top5_families
        }
        profiles.append(
            {
                "term": term,
                "results": term_results,
                "counts": counts,
                "top5_families": top5_families,
                "supported_families": supported_families,
            }
        )
    if not profiles:
        return [], [], ""
    family_votes = Counter()
    family_counts = Counter()
    family_top5_hits = Counter()
    for profile in profiles:
        for family in profile["supported_families"]:
            family_votes[family] += 1
            family_counts[family] += int(
                profile["counts"].get(family, 0)
            )
            if family in profile["top5_families"]:
                family_top5_hits[family] += 1
    candidates = []
    for family, term_votes in family_votes.items():
        same_as_base = bool(
            base_family
            and family == base_family
        )
        if same_as_base:
            accepted = bool(
                base_supported
                and term_votes >= 1
            )
        else:
            accepted = term_votes >= 2
        if not accepted:
            continue
        candidates.append(
            (
                term_votes,
                family_top5_hits[family],
                family_counts[family],
                family,
            )
        )
    if not candidates:
        return [], [], ""
    candidates.sort(reverse=True)
    _, _, _, selected_family = candidates[0]
    accepted_terms = []
    selected_groups = []
    if (
        base_supported
        and selected_family == base_family
    ):
        selected_groups.append(
            _filter_family_results(
                base_results,
                selected_family,
            )
        )
    for profile in profiles:
        if selected_family not in profile["supported_families"]:
            continue
        accepted_terms.append(
            profile["term"]
        )
        selected_groups.append(
            _filter_family_results(
                profile["results"],
                selected_family,
            )
        )
    selected_results = _merge_results(
        selected_groups
    )
    if not selected_results:
        return [], [], ""
    _debug(
        "family consensus:",
        selected_family,
        "terms:",
        accepted_terms,
        "votes:",
        family_votes[selected_family],
    )
    return (
        selected_results,
        accepted_terms,
        selected_family,
    )
def _select_weak_base_expansion(
    terms: List[str],
    base_summary: Dict[str, Any],
) -> Tuple[List[dict], List[str], str]:
    base_family = _clean_text(base_summary.get("top_law_family"))
    candidates = []
    for term in terms:
        try:
            term_results = search_related_laws(query=term, display=20)
        except Exception:
            continue
        if not term_results:
            continue
        summary = _summarize_results(term_results)
        term_family = _clean_text(summary.get("top_law_family"))
        same_family = bool(
            base_family
            and term_family
            and base_family == term_family
        )
        if same_family or not base_family:
            accepted = _is_standard_selective(summary)
        else:
            accepted = _is_cross_family_selective(summary)
        _debug(
            "term:", term,
            "summary:", summary,
            "accepted:", accepted,
        )
        if not accepted:
            continue
        selected_results = term_results
        if term_family:
            family_results = [
                item
                for item in term_results
                if isinstance(item, dict)
                and _same_law_family(
                    item.get("law_name", ""),
                    term_family,
                )
            ]
            if family_results:
                selected_results = family_results
        candidates.append(
            {
                "term": term,
                "results": selected_results,
                "target_family": term_family,
                "score": _expansion_score(summary),
            }
        )
    if not candidates:
        return [], [], ""
    candidates.sort(
        key=lambda item: (
            -item["score"],
            item["term"],
        )
    )
    best = candidates[0]
    return (
        best["results"],
        [best["term"]],
        best["target_family"],
    )
def search_with_query_expansion(
    query: str,
    fallback_mode: bool = False,
    top_k: int = 10,
) -> List[dict]:
    query = _normalize_search_input(query)
    if not query:
        return []
    try:
        base_results = search_related_laws(query=query, display=20)
    except Exception:
        raise RuntimeError("법제처 기본 검색에 실패했습니다. 검색 결과 0건으로 처리하지 않습니다.") from None
    base_reranked = rerank_law_results(
        query=query,
        results=base_results,
        top_k=top_k,
        fallback_mode=fallback_mode,
    )
    if not QUERY_EXPANSION_ENABLED:
        return base_reranked
    base_summary = _summarize_results(base_results)
    base_locked = _should_lock_base_family(base_summary)
    _debug("base summary:", base_summary)
    top_coverage = 0.0
    if base_reranked:
        try:
            top_coverage = float(
                base_reranked[0].get("query_coverage", 0.0)
            )
        except (TypeError, ValueError):
            top_coverage = 0.0
    if base_locked and top_coverage >= 0.75:
        _debug(
            "mode: BASE_FAMILY_LOCK_NO_EXPANSION",
            base_summary.get("top_law"),
        )
        return base_reranked
    terms = _validated_terms(query)
    if not terms:
        terms = _validated_recovery_terms(query)
        if not terms:
            _debug("mode: KEEP_BASE_NO_VALID_TERM")
            return base_reranked
    if base_locked:
        locked_family = _clean_text(
            base_summary.get("top_law_family")
        )
        expansion_results, accepted_terms = (
            _locked_family_expansion_results(
                terms=terms,
                locked_family=locked_family,
            )
        )
        if not expansion_results:
            recovery_terms = _validated_recovery_terms(
                query,
                exclude_terms=terms,
            )
            if recovery_terms:
                expansion_results, accepted_terms = (
                    _locked_family_expansion_results(
                        terms=recovery_terms,
                        locked_family=locked_family,
                    )
                )
        if not expansion_results:
            _debug("mode: BASE_FAMILY_LOCK_KEEP_BASE")
            return base_reranked

        combined_results = search_combined_family_results(
            accepted_terms, locked_family, _debug)
        expansion_results = _merge_results(
            [expansion_results, combined_results]
        )

        locked_base_results = [
            item
            for item in base_results
            if isinstance(item, dict)
            and _same_law_family(
                item.get("law_name", ""),
                locked_family,
            )
        ]
        merged = _merge_results(
            [
                locked_base_results,
                expansion_results,
            ]
        )
        rerank_query = _clean_text(
            " ".join([query, *accepted_terms])
        )
        _debug(
            "mode: BASE_FAMILY_LOCK_AUGMENT",
            "family:", locked_family,
            "terms:", accepted_terms,
        )
        reranked = rerank_law_results(
            query=rerank_query,
            results=merged,
            top_k=top_k,
            fallback_mode=(
                fallback_mode
                or len(accepted_terms) >= 2
            ),
        )
        return _attach_query_expansion_terms(
            prefer_family_root_items(
                reranked,
                locked_family,
            ),
            accepted_terms,
        )
    (
        expansion_results,
        accepted_terms,
        target_family,
    ) = _select_family_consensus(
        terms=terms,
        base_results=base_results,
        base_summary=base_summary,
    )
    if not expansion_results:
        (
            expansion_results,
            accepted_terms,
            target_family,
        ) = _select_weak_base_expansion(
            terms=terms,
            base_summary=base_summary,
        )
    if not expansion_results:
        recovery_terms = _validated_recovery_terms(
            query,
            exclude_terms=terms,
        )
        if recovery_terms:
            (
                expansion_results,
                accepted_terms,
                target_family,
            ) = _select_family_consensus(
                terms=recovery_terms,
                base_results=base_results,
                base_summary=base_summary,
            )
            if not expansion_results:
                (
                    expansion_results,
                    accepted_terms,
                    target_family,
                ) = _select_weak_base_expansion(
                    terms=recovery_terms,
                    base_summary=base_summary,
                )
    if not expansion_results:
        _debug("mode: KEEP_BASE_NO_SELECTIVE_TERM")
        return base_reranked

    combined_results = search_combined_family_results(
        accepted_terms, target_family, _debug)
    expansion_results = _merge_results(
        [expansion_results, combined_results]
    )

    filtered_base_results = base_results
    if target_family:
        filtered_base_results = [
            item
            for item in base_results
            if isinstance(item, dict)
            and _same_law_family(
                item.get("law_name", ""),
                target_family,
            )
        ]
    merged = _merge_results(
        [
            filtered_base_results,
            expansion_results,
        ]
    )
    rerank_query = _clean_text(
        " ".join([query, *accepted_terms])
    )
    _debug(
        "mode: EXPAND_CANDIDATES",
        "family:", target_family,
        "terms:", accepted_terms,
    )
    reranked = rerank_law_results(
        query=rerank_query,
        results=merged,
        top_k=top_k,
        fallback_mode=(
            fallback_mode
            or len(accepted_terms) >= 2
        ),
    )
    return _attach_query_expansion_terms(
        prefer_family_root_items(
            reranked,
            target_family,
        ),
        accepted_terms,
    )
