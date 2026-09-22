"""Trusted ingestion of recorded official API responses (not generated answers).

Change log
- 2026-09-21: OfficialAPIRetriever.refresh() 반환 확장
  * hint_summaries — 사람 검토 요약 문구 리스트 (search_hints의 summary 필드)
  * precedents — 검증된 판례 (detail_verified=True) 만 통과
  이 두 필드를 legal_rag/engine.py 가 답변 렌더링에 사용한다.
"""
import json
from urllib.parse import urlencode, quote
from .types import Document, digest


def statute_documents(raw, params, retrieved_at, fresh_until):
    from services.law.full_text_parser import parse_full_law
    law = parse_full_law(raw)
    mst = str(params.get("MST") or law.get("mst") or "")
    if law.get("mst") and str(law["mst"]) != mst:
        raise ValueError("source_version_mismatch")
    requested_date = str(params.get("efYd") or "")
    if requested_date and str(law.get("effective_date") or "") != requested_date:
        raise ValueError("source_effective_date_mismatch")
    if not law.get("law_name") or not mst.isdigit() or not law.get("effective_date"):
        return []
    result = []
    for article in law["articles"]:
        text = article.get("full_text", "").strip()
        if not text:
            continue
        number, sub = article["article_number"], article.get("sub_article_number", 0)
        content_hash = digest(text)
        key = f"law:{law.get('law_id', '')}:{mst}:{law['effective_date']}:{content_hash[:16]}:{number}:{sub}"
        label = f"제{number}조" + (f"의{sub}" if sub else "")
        result.append(Document(id=key, kind="statute", title=f"{law['law_name']} {label} {article.get('article_title', '')}",
                               text=text, url="https://www.law.go.kr/LSW/lsInfoP.do?" + urlencode({"lsiSeq": mst, "efYd": law["effective_date"]}),
                               source_id=str(law.get("law_id") or mst), version=mst, content_hash=content_hash,
                               retrieved_at=retrieved_at, fresh_until=fresh_until,
                               valid_from=article.get("effective_date") or law["effective_date"],
                               metadata={"law_name": law["law_name"], "article_number": number, "sub_article_number": sub,
                                         "article_title": article.get("article_title", ""),
                                         "law_type": law.get("law_type", ""), "ministry": law.get("ministry", ""),
                                         "headings": article.get("section_headers", []), "unit": "complete_article",
                                         "origin": "moleg_api"}))
    return result


def precedent_documents(raw, params, retrieved_at, fresh_until):
    case = raw.get("PrecService", {})
    pid = str(case.get("판례정보일련번호") or case.get("판례일련번호") or "")
    if not pid.isdigit() or str(params.get("ID", "")) != pid:
        return []
    if not all(case.get(k) for k in ("사건번호", "법원명", "선고일자", "판례내용")):
        return []
    result = []
    for field in ("판시사항", "판결요지"):
        text = case.get(field, "").strip()
        if not text:
            continue
        result.append(Document(id=f"case:{pid}:{field}", kind="precedent", title=f"{case['법원명']} {case['사건번호']} {case.get('사건명', '')} {field}",
                               text=text, url=f"https://www.law.go.kr/LSW/precInfoP.do?precSeq={pid}", source_id=pid, version=pid,
                               content_hash=digest(text), retrieved_at=retrieved_at, fresh_until=fresh_until,
                               metadata={"case_number": case["사건번호"], "court": case["법원명"], "decision_date": str(case["선고일자"]),
                                         "unit": field, "origin": "moleg_api", "subsequent_history_checked": False,
                                         "case_type": case.get("사건종류명", "")}))
    return result


def ingest_api_cache(store):
    from core.cache_db import get_connection
    count, rejected, empty = 0, 0, 0
    pending = []
    with get_connection() as db:
        rows = db.execute("SELECT endpoint,request_params,response_json,fetched_at,expires_at FROM api_cache WHERE endpoint IN ('lawService-full-law-v4','lawService-prec')").fetchall()
    for row in rows:
        parser = statute_documents if row["endpoint"] == "lawService-full-law-v4" else precedent_documents
        try:
            docs = parser(json.loads(row["response_json"]), json.loads(row["request_params"]), row["fetched_at"], row["expires_at"])
            if not docs:
                empty += 1
            pending.extend(docs)
            count += len(docs)
        except (ValueError, KeyError, TypeError):
            rejected += 1
    batch = store.upsert_many(pending)
    current_ids = {d.id for d in pending if d.kind == "statute"}
    refreshed_prefixes = {tuple(key.split(":")[1:3]) for key in current_ids}
    superseded = []
    for old in store.documents():
        parts = old.id.split(":")
        if old.kind == "statute" and tuple(parts[1:3]) in refreshed_prefixes and old.id not in current_ids:
            superseded.append(old.id)
    removed = store.delete_documents(superseded)
    return {"imported_documents": count, "changed_documents": batch["changed"], "superseded_documents_removed": removed,
            "rejected_responses": rejected, "responses_without_indexable_units": empty, "source_responses": len(rows)}


class OfficialAPIRetriever:
    """Bounded on-demand retrieval from official sources.

    General/Qwen search is supplemented by narrowly reviewed lexical hints.
    Hints can only request official source text; they cannot create a claim or
    bypass the publication verifier.
    """
    def __init__(self, store, max_laws=3):
        self.store, self.max_laws = store, max_laws

    def refresh_exact(self, query):
        """Refresh one explicitly named statute without unrelated services."""
        from .scope import explicit_law_name
        from services.law.full_text import get_full_law

        name = explicit_law_name(query)
        statuses = []
        if name:
            try:
                result = get_full_law(name)
                statuses.append({"source": "moleg_statute", "status": result.get("status", "error"), "query": name})
            except Exception:
                statuses.append({"source": "moleg_statute", "status": "error", "query": name})
        else:
            statuses.append({"source": "moleg_statute", "status": "not_found"})
        return {
            "sources": statuses,
            "bibliography": [],
            "ingestion": ingest_api_cache(self.store),
            "query_terms": [],
            "hint_profiles": [],
            "hint_summaries": [],
            "precedents": [],
            "query_term_sources": {"reviewed_hints": [], "qwen_officially_validated": []},
        }

    def refresh(self, query, current_question=None):
        from .scope import explicit_law_name
        from services.law.query_expander import search_with_query_expansion
        from services.law.search_hints import search_hints
        from services.law.full_text import get_full_law
        from services.evidence.precedent import search_precedents
        from services.library.search import search_library

        statuses = []
        candidates = []
        # 힌트 매칭은 현재 질문만 대상으로 (멀티턴에서 이전 질문 요약이 딸려오는 문제 방지)
        hints_query = current_question if isinstance(current_question, str) and current_question.strip() else query
        hints = search_hints(hints_query)
        named_law = explicit_law_name(query)
        names = []

        # 명시 법령명 → 해당 법령 우선 갱신
        if named_law:
            names.append(named_law)
            try:
                result = get_full_law(named_law)
                statuses.append({"source": "moleg_statute", "status": result.get("status", "error"), "query": named_law})
            except Exception:
                statuses.append({"source": "moleg_statute", "status": "error", "query": named_law})

        # 힌트 + Qwen 확장 으로 후보 법령 최대 max_laws 개 갱신
        try:
            candidates = search_with_query_expansion(query, top_k=20)
            expanded_names = list(dict.fromkeys(
                list(hints.get("law_names", []))
                + [x["law_name"] for x in candidates if x.get("law_name")]
            ))
            names.extend(name for name in expanded_names if name not in names)
            names = names[:self.max_laws]
            if not names:
                statuses.append({"source": "moleg_search", "status": "not_found"})
            for name in names:
                if name == named_law:
                    continue
                try:
                    result = get_full_law(name)
                    statuses.append({"source": "moleg_statute", "status": result.get("status", "error"), "query": name})
                except Exception:
                    statuses.append({"source": "moleg_statute", "status": "error"})
        except Exception:
            statuses.append({"source": "moleg_search", "status": "error"})

        # ---------------------------------------------------------
        # 판례 검색 — 검증된 판례를 답변 렌더용으로 반환
        # (기존: 카운트만. 이제 실제 리스트를 통과)
        # ---------------------------------------------------------
        verified_precedents = []
        # 판례 검색어 정제 — 자연어 그대로 보내면 조사·특수문자 때문에 0건
        # 우선순위: profile.precedent_query > hints.terms 첫 번째 > 정제된 현재 질문
        import re as _re
        _prec_qs = hints.get("precedent_queries", [])
        _hint_terms = hints.get("terms", [])
        if _prec_qs:
            _prec_query = _prec_qs[0]
        elif _hint_terms:
            _prec_query = _hint_terms[0]
        else:
            _base = current_question if isinstance(current_question, str) and current_question.strip() else query
            # 조사·특수문자 제거, 공백 정리
            _prec_query = _re.sub(r"[?!,./·\\]", " ", _base)
            _prec_query = _re.sub(r"\s+", " ", _prec_query).strip()

        try:
            cases = search_precedents(_prec_query, display=3, detail_limit=2)
            verified_count = sum(bool(c.get("detail_verified")) for c in cases)
            statuses.append({"source": "moleg_precedent",
                             "status": "success" if verified_count else "no_verified_details",
                             "verified_count": verified_count})

            # detail_verified=True 만 통과. 렌더에 필요한 필드만 뽑음.
            for c in cases:
                if not c.get("detail_verified"):
                    continue
                verified_precedents.append({
                    "case_number": c.get("case_number", ""),
                    "court_name": c.get("court_name", ""),
                    "decision_date": c.get("decision_date", ""),
                    "case_type": c.get("case_type", ""),
                    "case_name": c.get("case_name", ""),
                    # 요지/사항 중 있는 걸 선택 (렌더는 짧게 자를 것)
                    "summary": c.get("summary", "") or c.get("holding", ""),
                    "official_link": c.get("official_link", ""),
                })

            # ---------------------------------------------------------
            # 판례 정렬: profile의 preferred_case_types와 매칭되는 것을 상위로
            #  - 매칭 없으면 원래 순서 유지 (판례를 잃지 않음)
            #  - preferred_case_types에서 앞에 있을수록 우선 (rank 낮음)
            # ---------------------------------------------------------
            _preferred_cts = hints.get("preferred_case_types", []) or []
            if _preferred_cts and verified_precedents:
                _rank = {ct: i for i, ct in enumerate(_preferred_cts)}
                # 매칭 안 되는 case_type은 큰 값(999)으로 밀어냄
                verified_precedents.sort(
                    key=lambda p: _rank.get(p.get("case_type", ""), 999)
                )
        except Exception:
            statuses.append({"source": "moleg_precedent", "status": "error"})

        # ---------------------------------------------------------
        # 국회도서관 자료검색 (참고문헌)
        # ---------------------------------------------------------
        # 국회도서관도 자연어 그대로 보내면 조사·특수문자 때문에 0건.
        # 1차: 판례 검색어(_prec_query) 재사용
        # 2차 (fallback): profile.terms 를 순차 시도. 판례 검색어가 좁아
        #   자료가 안 잡히는 경우 더 넓은 term 으로 커버.
        bibliography = []
        _library_query_used = _prec_query
        try:
            bibliography = search_library(_prec_query, display_lines=3)
            if not bibliography:
                # fallback: profile.terms 순차 시도
                _hint_terms_local = hints.get("terms", []) or []
                for _t in _hint_terms_local[:4]:
                    if not _t or _t == _prec_query:
                        continue
                    try:
                        bibliography = search_library(_t, display_lines=3)
                        if bibliography:
                            _library_query_used = _t
                            break
                    except Exception:
                        continue
            statuses.append({
                "source": "nanet",
                "status": "success" if bibliography else "not_found",
                "query_used": _library_query_used,
            })
        except Exception:
            statuses.append({"source": "nanet", "status": "error", "message": "자료검색 인증 또는 연결 상태 확인 필요"})

        # 참고문헌은 답변 근거로 쓰지 않고 링크만 표시
        # 제목이 빈 자료는 사용자 화면에 보여도 무의미하므로 제외
        references = [{"title": x.get("title", ""), "control_no": x["control_no"],
                       "url": "https://dl.nanet.go.kr/detail/" + quote(x["control_no"], safe=""),
                       "role": "bibliography_only"}
                      for x in bibliography
                      if x.get("control_no") and str(x.get("title", "") or "").strip()]

        model_terms = list(dict.fromkeys(
            term
            for item in candidates if isinstance(item, dict)
            for term in item.get("query_expansion_terms", [])
            if isinstance(term, str) and term.strip()
        ))[:4]
        hint_terms = [term for term in hints.get("terms", []) if isinstance(term, str) and term.strip()]
        query_terms = list(dict.fromkeys(hint_terms + model_terms))[:4]

        # 사람 검토 요약 (search_hints의 summary 필드가 있는 profile만)
        hint_summaries = [
            s for s in hints.get("summaries", [])
            if isinstance(s, str) and s.strip()
        ]

        ingested = ingest_api_cache(self.store)
        return {
            "sources": statuses,
            "bibliography": references,
            "precedents": verified_precedents,
            "ingestion": ingested,
            "query_terms": query_terms,
            "hint_profiles": hints.get("profile_ids", []),
            "hint_summaries": hint_summaries,
            "query_term_sources": {"reviewed_hints": hint_terms, "qwen_officially_validated": model_terms},
        }
