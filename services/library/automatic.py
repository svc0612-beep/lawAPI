"""Bounded library lookup; bibliographic records are reference material only."""
from services.library.search import search_library
from services.law.search_hints import search_hints
from urllib.parse import quote


def attach_library_search(result):
    meta = result.setdefault("metadata", {})
    meta["library_auto_search_enabled"] = True
    terms = search_hints(result.get("original_question", ""))["terms"]
    keyword = terms[0] if terms else result.get("search_query", "")
    status = dict(source="국회도서관", endpoint="nanet-search-basic", status="not_found", result_count=0, message="")
    try:
        rows = search_library(keyword, display_lines=3) if keyword else []
        items = []
        for row in rows:
            control = row.get("control_no", "")
            if not control or not row.get("title"):
                continue
            items.append({k: v for k, v in row.items() if k != "raw"} | {
                "source": "국회도서관", "evidence_role": "bibliographic_reference",
                "full_text_verified": False,
                "official_link": "https://dl.nanet.go.kr/detail/" + quote(control, safe=""),
            })
        result["library_items"] = items
        status.update(status="success" if items else "not_found", result_count=len(items),
                      message="서지 검색 결과이며 자료 본문은 검증하지 않았습니다.")
    except Exception:
        result.setdefault("library_items", [])
        status.update(status="error", message="검색 API 호출에 실패했습니다. 연결·인증·서비스 이용승인 상태를 확인해야 합니다.")
    result.setdefault("source_status", []).append(status)
    meta["library_item_count"] = len(result.get("library_items", []))
    return result
