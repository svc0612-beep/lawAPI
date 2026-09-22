"""Official administrative-rule and local-ordinance retrieval and parsing."""
import re
from datetime import datetime, timedelta, timezone
from html import unescape
import requests

from core.config import LAW_API_KEY, LAW_SEARCH_URL, LAW_SERVICE_URL
from core.cache import get_cache, save_cache, record_api_call, make_cache_key
from core.cache_db import get_connection
from .types import Document, digest


def _text(value):
    value = unescape(str(value or ""))
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _request(endpoint, url, params):
    cached = get_cache(source="법제처", endpoint=endpoint, params=params)
    if cached is not None:
        return cached
    if not LAW_API_KEY:
        raise RuntimeError("law_api_key_missing")
    try:
        response = requests.get(url, params={**params, "OC": LAW_API_KEY}, timeout=(5, 30))
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError):
        raise RuntimeError("moleg_supplemental_api_error") from None
    if not isinstance(data, dict):
        raise RuntimeError("moleg_supplemental_schema_error")
    record_api_call(source="법제처", endpoint=endpoint)
    save_cache(source="법제처", endpoint=endpoint, params=params, response_data=data, ttl_hours=24)
    return data


def _as_list(value):
    if isinstance(value, list):
        return value
    return [value] if isinstance(value, dict) else []


def search_official(target, query, display=3):
    if target not in {"admrul", "ordin"} or not query.strip():
        raise ValueError("invalid_supplemental_search")
    params = {"target": target, "type": "JSON", "query": query.strip(), "display": min(max(display, 1), 10), "nw": 1}
    data = _request(f"lawSearch-{target}-v1", LAW_SEARCH_URL, params)
    root_key, item_key = ("AdmRulSearch", "admrul") if target == "admrul" else ("OrdinSearch", "law")
    root = data.get(root_key, {})
    if str(root.get("resultCode", "")) != "00":
        raise RuntimeError("moleg_supplemental_result_error")
    return _as_list(root.get(item_key))


def fetch_official(target, identity):
    field = "ID" if target == "admrul" else "MST"
    params = {"target": target, "type": "JSON", field: str(identity)}
    endpoint = f"lawService-{target}-v1"
    data = _request(endpoint, LAW_SERVICE_URL, params)
    key = make_cache_key("법제처", endpoint, params)
    with get_connection() as db:
        row = db.execute("SELECT fetched_at,expires_at FROM api_cache WHERE cache_key=?", (key,)).fetchone()
    if not row:
        raise RuntimeError("moleg_supplemental_cache_identity_missing")
    return data, row["fetched_at"], row["expires_at"]


def _times(now=None, retrieved_at=None, fresh_until=None):
    if retrieved_at and fresh_until:
        return retrieved_at, fresh_until
    now = now or datetime.now(timezone.utc)
    return now.isoformat(), (now + timedelta(hours=24)).isoformat()


def ordinance_documents(raw, expected_mst, now=None, retrieved_at=None, fresh_until=None):
    root = raw.get("LawService", {})
    info = root.get("자치법규기본정보", {})
    mst = str(info.get("자치법규일련번호") or "")
    if mst != str(expected_mst) or not all(info.get(k) for k in ("자치법규ID", "자치법규명", "지자체기관명", "시행일자")):
        return []
    fetched, expires = _times(now, retrieved_at, fresh_until)
    nodes = _as_list(root.get("조문", {}).get("조"))
    documents = []
    for position, node in enumerate(nodes, 1):
        if node.get("조문여부") not in (None, "", "Y"):
            continue
        content = _text(node.get("조내용"))
        raw_number = node.get("조문번호")
        raw_number = raw_number[0] if isinstance(raw_number, list) and raw_number else raw_number
        digits = re.sub(r"\D", "", str(raw_number or ""))
        number = int(digits)//100 if digits else position
        sub = int(digits)%100 if digits else 0
        if not content or number <= 0:
            continue
        key = f"ordin:{info['자치법규ID']}:{mst}:{number}:{sub}"
        label = f"제{number}조" + (f"의{sub}" if sub else "")
        documents.append(Document(key, "local_ordinance", f"{info['자치법규명']} {label} {_text(node.get('조제목'))}", content,
            f"https://www.law.go.kr/LSW/ordinInfoP.do?ordinSeq={mst}", str(info["자치법규ID"]), mst, digest(content), fetched, expires,
            str(info["시행일자"]), metadata={"origin": "moleg_api", "unit": "complete_article", "law_name": info["자치법규명"],
                "article_number": number, "sub_article_number": sub, "law_type": "자치법규", "rule_type": _text(info.get("자치법규종류")) or "자치법규",
                "local_government": info["지자체기관명"], "promulgation_date": _text(info.get("공포일자")), "promulgation_number": _text(info.get("공포번호"))}))
    return documents


def administrative_rule_documents(raw, expected_seq, now=None, retrieved_at=None, fresh_until=None):
    root = raw.get("AdmRulService", {})
    info = root.get("행정규칙기본정보", {})
    seq = str(info.get("행정규칙일련번호") or "")
    if seq != str(expected_seq) or not all(info.get(k) for k in ("행정규칙ID", "행정규칙명", "행정규칙종류", "소관부처명", "시행일자")):
        return []
    parts = []
    body = root.get("조문내용")
    if isinstance(body, str):
        parts.append(_text(body))
    elif isinstance(body, dict):
        for value in body.values():
            for item in value if isinstance(value, list) else [value]:
                if isinstance(item, dict):
                    parts.append(_text(item.get("조문내용") or item.get("조내용")))
                elif isinstance(item, str):
                    parts.append(_text(item))
    content = "\n".join(x for x in parts if x)
    if not content:
        return []
    fetched, expires = _times(now, retrieved_at, fresh_until)
    document = Document(f"admrul:{info['행정규칙ID']}:{seq}", "administrative_rule", info["행정규칙명"], content,
        f"https://www.law.go.kr/LSW/admRulInfoP.do?admRulSeq={seq}", str(info["행정규칙ID"]), seq, digest(content), fetched, expires,
        str(info["시행일자"]), metadata={"origin": "moleg_api", "unit": "complete_document", "law_name": info["행정규칙명"],
            "law_type": "행정규칙", "rule_type": info["행정규칙종류"], "issuing_authority": info["소관부처명"],
            "issue_date": _text(info.get("발령일자")), "issue_number": _text(info.get("발령번호"))})
    return [document]


def refresh_supplemental(store, target, queries, per_query=1):
    stats = {"target": target, "queries": len(queries), "search_hits": 0, "documents": 0, "empty_details": 0, "errors": 0}
    seen = set()
    pending = []
    for query in queries:
        try:
            for item in search_official(target, query, per_query):
                identity = str(item.get("행정규칙일련번호") if target == "admrul" else item.get("자치법규일련번호") or "")
                if not identity or identity in seen:
                    continue
                seen.add(identity)
                stats["search_hits"] += 1
                raw, fetched_at, expires_at = fetch_official(target, identity)
                docs = (administrative_rule_documents(raw, identity, retrieved_at=fetched_at, fresh_until=expires_at)
                        if target == "admrul" else ordinance_documents(raw, identity, retrieved_at=fetched_at, fresh_until=expires_at))
                if not docs:
                    stats["empty_details"] += 1
                pending.extend(docs)
                stats["documents"] += len(docs)
        except (RuntimeError, ValueError, KeyError, TypeError):
            stats["errors"] += 1
    stats["changed_documents"] = store.upsert_many(pending)["changed"] if pending else 0
    return stats
