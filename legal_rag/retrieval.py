# ============================================================
# 검색 및 재정렬 파이프라인
#
# 변경 이력
# - 2026-09-21: trusted_terms 검색 방식 수정
#   기존: " ".join(trusted_terms) 로 한 번에 FTS 검색
#         → FTS5는 phrase 매칭이라 여러 term을 합치면 모든 단어가
#           한 문서에 다 있어야 매칭됨. hint terms 3~4개가 다 있는
#           조문은 거의 없어서 0건이 나옴.
#   수정: 각 term 개별로 FTS 검색 후 결과를 union.
#
# - 2026-09-21 (2차): rerank에서 title_anchor 우회 추가
#   기존: 모든 hit에 title_anchor 필터 적용 → 자연어 질문의
#         "회사에서", "하면" 같은 조사가 조문 title에 없어서
#         관련 조문도 다 걸러짐.
#   수정: "trusted_term_fts5" 채널로 들어온 hit은 title_anchor 우회.
#         (사람이 검토한 매핑을 이미 통과한 hit이라 중복 필터 불필요)
# ============================================================

from .types import Hit
from .schemas import RANK
from .verify import document_errors
from .model import ModelError
import jsonschema
import copy
from .scope import exact_request, title_anchor, build_exact_index, explicit_law_name
import re


def reciprocal_rank_fusion(groups, limit):
    # 여러 검색 채널(BM25, dense, trusted terms 등) 결과를 융합
    combined = {}
    for group in groups:
        for rank, hit in enumerate(group, 1):
            item = combined.setdefault(hit.document.id, Hit(hit.document, 0, []))
            item.score += 1 / (60 + rank)
            item.channels = list(dict.fromkeys(item.channels + hit.channels))
    return sorted(combined.values(), key=lambda h: (-h.score, h.document.id))[:limit]


class Retriever:
    def __init__(self, store, settings, model, embedder=None):
        self.store, self.settings, self.model, self.embedder = store, settings, model, embedder
        self.refresh_exact_index()

    def refresh_exact_index(self):
        self.exact_index = build_exact_index(self.store.documents())

    def retrieve(self, query, trusted_terms=None):
        # 정확 조문 요청 (예: "형법 260조") 은 즉시 반환
        exact = exact_request(query, index=self.exact_index)
        if exact is not None:
            valid = [Hit(d, 1., ["exact_law_article"]) for d in exact if not document_errors(d)]
            return valid, {"lexical_count": len(valid), "dense_enabled": False, "exact_request": True,
                           "rejected_sources": [{"id": d.id, "errors": document_errors(d)} for d in exact if document_errors(d)]}

        # 일반 BM25 검색 (사용자 자연어 쿼리 전체)
        lexical = self.store.lexical(query, self.settings.retrieval_k)
        diagnostics = {"lexical_count": len(lexical), "dense_enabled": self.embedder is not None}
        groups = [lexical]

        # trusted_terms = search_hints가 반환한 사람 검토 매핑 용어
        trusted_terms = [
            term for term in (trusted_terms or [])
            if isinstance(term, str) and term.strip()
        ]

        if trusted_terms:

            # ---------------------------------------------------------
            # 각 term 개별 검색 후 union (FTS5 phrase 매칭 제약 우회)
            # ---------------------------------------------------------
            trusted_hits = []
            seen_ids = set()

            for term in trusted_terms:

                # 개별 term FTS 검색
                per_term_hits = self.store.lexical(
                    term,
                    self.settings.retrieval_k
                )

                # 중복 제거하며 union
                for hit in per_term_hits:
                    if hit.document.id in seen_ids:
                        continue
                    seen_ids.add(hit.document.id)
                    trusted_hits.append(hit)

            # 상위 retrieval_k 개만 유지
            trusted_hits = trusted_hits[:self.settings.retrieval_k]

            # 채널 표시: 이 hit은 trusted term FTS로 들어왔음
            # (rerank 단계에서 title_anchor 필터 우회 판정에 사용)
            for hit in trusted_hits:
                hit.channels = list(dict.fromkeys(hit.channels + ["trusted_term_fts5"]))

            groups.append(trusted_hits)
            diagnostics["trusted_term_lexical_count"] = len(trusted_hits)

        # dense embedding 검색 (설정된 경우)
        if self.embedder:
            vector = self.embedder.embed([query])[0]
            groups.append(self.store.dense(vector, self.settings.embedding_model, self.settings.retrieval_k))
            diagnostics["dense_count"] = len(groups[-1])

        # Reciprocal Rank Fusion 으로 다중 채널 결과 융합
        hits = reciprocal_rank_fusion(groups, self.settings.retrieval_k)

        # 무효 문서 (해시 불일치·만료 등) 필터
        valid, rejected = [], []
        for hit in hits:
            errors = document_errors(hit.document)
            if errors:
                rejected.append({"id": hit.document.id, "errors": errors})
            else:
                valid.append(hit)
        diagnostics["rejected_sources"] = rejected
        return valid, diagnostics

    def rerank(self, query, hits, original_question=None, planned_query=None, trusted_terms=None):
        # 재정렬용 후보 뷰 (전체 원문은 생성 단계에서 붙임)
        candidates, remaining = [], self.settings.max_context_chars
        expected_law = explicit_law_name(original_question or "", self.exact_index.keys())

        for hit in hits:

            document_law = hit.document.metadata.get("law_name", "")

            # 명시 법령명이 있을 때 다른 법령 문서는 거절
            if expected_law and document_law and document_law != expected_law:
                continue

            # ---------------------------------------------------------
            # title_anchor 필터
            #
            # 원칙: 자연어 질문의 이슈 단어가 조문 title에 있어야만 통과
            # 예외 1) exact_law_article 채널: 사용자가 조문 번호 명시
            # 예외 2) trusted_term_fts5 채널: 사람이 검토한 매핑을 통과
            #        → 자연어 질문의 조사("회사에서", "하면") 때문에 필터 실패하는 상황을 방지
            # ---------------------------------------------------------
            bypass_channels = {"exact_law_article", "trusted_term_fts5"}

            if original_question and not (bypass_channels & set(hit.channels)):
                original_match = title_anchor(hit.document, original_question)
                planned_match = bool(planned_query) and title_anchor(hit.document, planned_query)
                if not (original_match or planned_match):
                    continue

            text = hit.document.text[:350]
            if len(text) > remaining:
                break
            candidates.append({"id": hit.document.id, "title": hit.document.title,
                               "headings": hit.document.metadata.get("headings", []), "text": text,
                               "ranking_view_truncated": len(text) < len(hit.document.text)})
            remaining -= len(text)
            if len(candidates) >= 6:
                break

        if not candidates:
            return [], {"reranker": "not_run", "reason": "no_valid_candidates"}

        by_id = {h.document.id: h for h in hits}

        def normalized_title_parts(document):
            article_title = document.metadata.get("article_title", "")
            return {
                re.sub(r"\s+|의", "", part)
                for part in re.split(r"[,·/]", article_title)
                if part.strip()
            }

        trusted = {
            re.sub(r"\s+|의", "", term)
            for term in (trusted_terms or [])
            if isinstance(term, str) and term.strip()
        }
        if trusted:
            matched = []
            for candidate in candidates:
                document = by_id[candidate["id"]].document
                if trusted & normalized_title_parts(document):
                    matched.append(document)
            if matched:
                selected, remaining = [], self.settings.max_context_chars
                for document in matched:
                    if len(document.text) <= remaining:
                        selected.append(document)
                        remaining -= len(document.text)
                    if len(selected) >= self.settings.evidence_k:
                        break
                return selected, {
                    "reranker": "trusted_term_title_identity",
                    "candidate_count": len(candidates),
                    "selected_count": len(selected),
                    "relevance_is_not_applicability": True,
                }

        # 사용자가 법령명 명시 + 조문 title 매칭 → 그 조문 우선
        if original_question:
            strong = []
            for candidate in candidates:
                document = by_id[candidate["id"]].document
                law_name = document.metadata.get("law_name", "")
                if expected_law and law_name == expected_law and title_anchor(document, original_question):
                    strong.append(document)
            if strong:
                selected, remaining = [], self.settings.max_context_chars
                for document in strong:
                    if len(document.text) <= remaining:
                        selected.append(document)
                        remaining -= len(document.text)
                    if len(selected) >= self.settings.evidence_k:
                        break
                return selected, {
                    "reranker": "explicit_law_title_identity",
                    "candidate_count": len(candidates),
                    "selected_count": len(selected),
                    "relevance_is_not_applicability": True,
                }

        # 마지막 fallback: Qwen 관련성 재정렬
        schema = copy.deepcopy(RANK)
        schema["properties"]["scores"].update(minItems=len(candidates), maxItems=len(candidates))
        scores = self.model.generate("rerank", {"query": query, "candidates": candidates}, schema)
        jsonschema.validate(scores, schema)
        if len(scores["scores"]) != len(candidates):
            raise ModelError("invalid_reranker_citation")
        ranked = []
        for candidate, score in zip(candidates, scores["scores"]):
            if score >= 2:
                ranked.append((score, by_id[candidate["id"]]))
        ranked.sort(key=lambda pair: (-pair[0], -pair[1].score))
        selected, remaining = [], self.settings.max_context_chars
        for _, hit in ranked:
            if len(hit.document.text) <= remaining:
                selected.append(hit.document)
                remaining -= len(hit.document.text)
            if len(selected) >= self.settings.evidence_k:
                break
        return selected, {"reranker": "llm_relevance", "candidate_count": len(candidates),
                          "selected_count": len(selected), "relevance_is_not_applicability": True}
