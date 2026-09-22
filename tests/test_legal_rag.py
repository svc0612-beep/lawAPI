"""Backend contracts; synthetic text here is NOT legal ground truth."""
import copy
import tempfile
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

from legal_rag.config import Settings
from legal_rag.engine import LegalRAG, literal_facts
from legal_rag.model import ModelError
from legal_rag.store import Store, ConflictError
from legal_rag.types import Document, digest
from legal_rag.verify import verify_draft
from legal_rag.retrieval import Retriever
from legal_rag.evaluation import retrieval_metrics, release_gate, load_gold
from legal_rag.ingest import statute_documents, precedent_documents, OfficialAPIRetriever
from legal_rag.scope import title_anchor
from legal_rag.supplemental import ordinance_documents, administrative_rule_documents
from legal_rag.coverage import hierarchy, domain, corpus_coverage, minimum_coverage_gate
from unittest.mock import patch
import json


def fixture_document(index=1):
    now = datetime.now(timezone.utc)
    text = f"시험용 가상 조문 {index}. 시험 금액은 {index + 100}원이다. 다만 예외 조건은 반드시 함께 읽는다."
    return Document(str(index), "statute", f"시험용 가상법 제{index}조", text,
                    f"https://www.law.go.kr/LSW/lsInfoP.do?lsiSeq={index}", str(index), str(index), digest(text),
                    (now - timedelta(hours=1)).isoformat(), (now + timedelta(hours=1)).isoformat(), "20200101",
                    metadata={"origin": "moleg_api", "unit": "complete_article"})


def draft_for(document):
    return {"status": "answer", "claims": [{"evidence_id": document.id, "text": document.text, "quote": document.text}], "questions": []}


class ScriptedModel:
    def __init__(self):
        self.calls = []
        self.query = None
        self.follow_up = False
        self.needs_clarification = False
        self.mutate = False
        self.broken = False

    def generate(self, task, payload, schema):
        self.calls.append((task, payload))
        if self.broken:
            raise ModelError("SECRET must not leak")
        if task == "plan":
            return {"query": self.query or payload["question"], "follow_up": self.follow_up,
                    "needs_clarification": self.needs_clarification, "questions": []}
        if task == "rerank":
            return {"scores": [3 for c in payload["candidates"]]}
        d = payload["evidence"][0]
        return {"status": "answer", "evidence_indices": [3 if self.mutate else 0]}


class VerificationTests(unittest.TestCase):
    def test_valid_quote_is_not_applicability(self):
        d = fixture_document()
        result = verify_draft(draft_for(d), [d])
        self.assertTrue(result["passed"])
        self.assertEqual(result["legal_applicability"], "not_verified")

    def test_every_corrupted_source_or_claim_is_blocked(self):
        d = fixture_document()
        changes = [dict(kind="bibliography"), dict(url="https://www.law.go.kr.evil.test/LSW/lsInfoP.do?lsiSeq=1"),
                   dict(url="https://www.law.go.kr:bad/LSW/lsInfoP.do?lsiSeq=1"), dict(version="999"),
                   dict(content_hash="0" * 64), dict(valid_from="20990101"), dict(valid_to="20200101"),
                   dict(fresh_until=d.retrieved_at), dict(metadata={"origin": "moleg_api", "unit": "sentence"})]
        for change in changes:
            with self.subTest(change=change):
                result = verify_draft(draft_for(d), [replace(d, **change)])
                self.assertFalse(result["passed"])
                self.assertEqual(result["claims"], [])
        for field, value in [("quote", d.text.split("다만")[0]), ("text", "무죄입니다"), ("evidence_id", "invented")]:
            draft = draft_for(d)
            draft["claims"][0][field] = value
            self.assertFalse(verify_draft(draft, [d])["passed"])

    def test_atomic_gate_and_duplicate(self):
        d = fixture_document()
        draft = draft_for(d)
        draft["claims"] *= 2
        self.assertFalse(verify_draft(draft, [d])["passed"])
        draft["claims"][1] = {"evidence_id": "bad", "quote": "bad", "text": "bad"}
        self.assertEqual(verify_draft(draft, [d])["claims"], [])

    def test_nonanswer_cannot_carry_claim(self):
        d = fixture_document()
        draft = draft_for(d)
        draft["status"] = "abstain"
        self.assertFalse(verify_draft(draft, [d])["passed"])


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / "test.sqlite3")
        self.document = fixture_document()
        self.store.upsert(self.document)
        self.model = ScriptedModel()
        self.rag = LegalRAG(Settings(), self.model, self.store)
        self.session = self.rag.create_session("alice")

    def tearDown(self):
        self.tmp.cleanup()

    def ask(self, question="시험용 가상법", **kwargs):
        return self.rag.ask("alice", self.session, question, **kwargs)

    def test_end_to_end_exact_and_mutated_generation(self):
        self.assertEqual(self.ask()["status"], "grounded_excerpt")
        self.model.mutate = True
        result = self.ask()
        self.assertEqual(result["status"], "verification_failed")
        self.assertNotIn("거짓 결론", str(result))
        self.assertEqual(result["citations"], [])

    def test_idempotency_and_conflicting_reuse(self):
        a = self.ask(request_id="same")
        calls = len(self.model.calls)
        self.assertEqual(a, self.ask(request_id="same"))
        self.assertEqual(len(self.model.calls), calls)
        with self.assertRaises(ConflictError):
            self.ask("다른 질문", request_id="same")
        with self.assertRaises(ConflictError):
            self.ask(request_id="same", new_topic=True)

    def test_tenant_isolation_and_delete(self):
        with self.assertRaises(PermissionError):
            self.rag.ask("bob", self.session, "시험용")
        with self.assertRaises(PermissionError):
            self.store.delete_session("bob", self.session)
        self.store.delete_session("alice", self.session)
        with self.assertRaises(PermissionError):
            self.ask()

    def test_optimistic_concurrent_turn_does_not_overwrite(self):
        self.store.commit_turn("alice", self.session, 0, "a", "a", {})
        with self.assertRaises(ConflictError):
            self.store.commit_turn("alice", self.session, 0, "b", "b", {})
        self.assertEqual(self.store.snapshot("alice", self.session, "c", "c")[1], ["a"])
        self.assertEqual(self.store.latest_turn("alice", self.session)["question"], "a")

    def test_latest_age_correction_and_bad_rewrite(self):
        self.ask("시험용 사건인데 13살이야")
        self.model.follow_up = True
        self.model.query = "시험용 사건 13살"
        result = self.ask("정정할게 15살이야")
        self.assertEqual(result["diagnostics"]["facts"]["age"]["value"], "15")
        self.assertEqual(result["status"], "clarify")

    def test_search_request_and_elliptical_follow_up_do_not_overclarify(self):
        self.model.needs_clarification = True
        first = self.ask("시험용 가상법 관련 조문을 찾아줘")
        self.assertNotEqual(first["status"], "clarify")

        self.model.query = "시험용 가상법 피해자가 원하지 않는 경우"
        second = self.ask("피해자가 원하지 않으면?")
        self.assertTrue(second["diagnostics"]["follow_up"])
        self.assertEqual(
            second["diagnostics"]["follow_up_guard"],
            "deterministic_context_restore",
        )

    def test_validated_online_expansion_reaches_lifestyle_term(self):
        theft = replace(
            self.document,
            title="형법 제329조 절도",
            metadata={
                **self.document.metadata,
                "law_name": "형법",
                "article_number": 329,
                "sub_article_number": 0,
                "article_title": "절도",
            },
        )
        self.store.upsert(theft)
        self.rag.retriever.refresh_exact_index()

        class Online:
            def refresh(inner, query):
                return {
                    "query_terms": ["절도"],
                    "query_term_sources": {
                        "reviewed_hints": ["절도"],
                        "qwen_officially_validated": [],
                    },
                    "sources": [],
                    "ingestion": {},
                }

        self.rag.online = Online()
        result = self.ask("남의 물건을 몰래 가져갔을 때 관련 법을 찾아줘")
        self.assertEqual(result["status"], "grounded_excerpt")
        self.assertEqual(result["diagnostics"]["validated_expansion_terms"], ["절도"])
        self.assertEqual(result["diagnostics"]["trusted_expansion_terms"], ["절도"])
        self.assertEqual(result["diagnostics"]["reranker"], "trusted_term_title_identity")

    def test_qwen_only_expansion_cannot_cross_law_boundary(self):
        theft = replace(
            fixture_document(9),
            title="형법 제329조 절도",
            metadata={
                **self.document.metadata,
                "law_name": "형법",
                "article_number": 329,
                "sub_article_number": 0,
                "article_title": "절도",
            },
        )
        self.store.upsert(theft)

        class Online:
            def refresh(inner, query):
                return {
                    "query_terms": ["절도"],
                    "query_term_sources": {
                        "reviewed_hints": [],
                        "qwen_officially_validated": ["절도"],
                    },
                    "sources": [],
                    "ingestion": {},
                }

        self.rag.online = Online()
        self.model.query = "헌법 기본권 절도"
        result = self.ask("헌법 기본권 관련 조문을 찾아줘")
        self.assertEqual(result["status"], "abstain")
        self.assertEqual(result["diagnostics"]["trusted_expansion_terms"], [])
        self.assertNotIn("형법 제329조", result["answer"])

    def test_excessive_model_rewrite_is_replaced_by_original_question(self):
        self.model.query = "절도" * 50
        result = self.ask("시험용 가상법")
        self.assertEqual(result["diagnostics"]["plan_sanitized"], "excessive_expansion")
        self.assertEqual(result["diagnostics"]["query"], "시험용 가상법")
        self.assertEqual(result["status"], "grounded_excerpt")

    def test_explicit_law_and_article_title_bypass_model_false_negative(self):
        labor = replace(
            self.document,
            title="근로기준법 제26조 해고의 예고",
            metadata={
                **self.document.metadata,
                "law_name": "근로기준법",
                "article_number": 26,
                "sub_article_number": 0,
            },
        )
        self.store.upsert(labor)
        self.rag.retriever.refresh_exact_index()
        original = self.model.generate

        def reject_rank(task, payload, schema):
            if task == "rerank":
                return {"scores": [0 for _ in payload["candidates"]]}
            return original(task, payload, schema)

        self.model.generate = reject_rank
        result = self.ask("근로기준법 해고예고 관련 조문을 찾아줘")
        self.assertEqual(result["status"], "grounded_excerpt")
        self.assertEqual(result["diagnostics"]["reranker"], "explicit_law_title_identity")

    def test_new_topic_persists_and_assistant_is_not_history(self):
        self.ask("13살 시험용 사건")
        self.ask("새 시험용 사건", new_topic=True)
        self.model.follow_up = True
        self.ask("그 시험용 사건은?")
        last_plan = [payload for task, payload in self.model.calls if task == "plan"][-1]
        self.assertEqual(last_plan["user_history"], ["새 시험용 사건"])
        self.assertNotIn("13", str(last_plan))

    def test_historical_and_relative_time_abstain(self):
        for q in ["2020년 시험용 사건", "2020-01-01 시험용 사건", "작년 시험용 사건", "3년 전 시험용 사건"]:
            self.assertEqual(self.ask(q)["status"], "temporal_review_required")

    def test_model_failure_does_not_leak(self):
        self.model.broken = True
        result = self.ask()
        self.assertEqual(result["status"], "model_error")
        self.assertNotIn("SECRET", str(result))

    def test_invalid_plan_and_reranker_id_fail_closed(self):
        original = self.model.generate
        def bad_plan(task, payload, schema):
            return {"query": "missing fields"}
        self.model.generate = bad_plan
        self.assertEqual(self.ask()["status"], "model_error")
        def bad_rank(task, payload, schema):
            return {"rankings": [{"id": "invented", "score": 3}]} if task == "rerank" else original(task, payload, schema)
        self.model.generate = bad_rank
        result = self.ask()
        self.assertEqual(result["status"], "model_error")
        self.assertEqual(result["citations"], [])

    def test_stale_source_not_retrieved(self):
        self.store.upsert(replace(self.document, fresh_until=self.document.retrieved_at))
        self.assertEqual(self.ask()["status"], "abstain")

    def test_immutable_document_and_embedding_dimensions(self):
        with self.assertRaises(ValueError):
            self.store.upsert(replace(self.document, text="changed", content_hash=digest("changed")))
        self.store.put_vector(self.document.id, "test", [1., 0.])
        self.assertEqual(self.store.dense([1., 0.], "test")[0].document.id, self.document.id)
        with self.assertRaises(ValueError):
            self.store.dense([1.], "test")
        with self.assertRaises(ValueError):
            self.store.put_vector(self.document.id, "test", [float("nan")])
        self.assertEqual(self.store.delete_documents([self.document.id, self.document.id]), 1)
        self.assertIsNone(self.store.get(self.document.id))

    def test_exact_law_article_does_not_match_another_law(self):
        correct = replace(self.document, metadata={**self.document.metadata, "law_name": "가상시험법", "article_number": 1, "sub_article_number": 0})
        wrong = replace(fixture_document(2), title="다른법 제1조", metadata={**self.document.metadata, "law_name": "다른법", "article_number": 1, "sub_article_number": 0})
        self.store.upsert(correct)
        self.store.upsert(wrong)
        self.rag.retriever.refresh_exact_index()
        hits, diagnostics = self.rag.retriever.retrieve("가상시험법 제1조")
        self.assertEqual([h.document.id for h in hits], [correct.id])
        self.model.broken = True
        result = self.ask("가상시험법 제1조")
        self.assertEqual(result["status"], "grounded_excerpt")
        self.assertEqual(result["citations"][0]["evidence_id"], correct.id)
        self.assertEqual(self.model.calls, [])
        hits, _ = self.rag.retriever.retrieve("가상시험법 제999조")
        self.assertEqual(hits, [])

    def test_common_law_alias_and_article_without_je_are_exact(self):
        constitution = replace(
            fixture_document(3),
            title="대한민국헌법 제1조",
            metadata={
                **self.document.metadata,
                "law_name": "대한민국헌법",
                "article_number": 1,
                "sub_article_number": 0,
                "article_title": "",
            },
        )
        self.store.upsert(constitution)
        self.rag.retriever.refresh_exact_index()
        self.model.broken = True
        result = self.ask("헌법 1조 1항 뭐야?")
        self.assertEqual(result["status"], "grounded_excerpt")
        self.assertEqual(result["citations"][0]["evidence_id"], constitution.id)
        self.assertEqual(result["diagnostics"]["plan_strategy"], "exact_reference")
        self.assertEqual(self.model.calls, [])

    def test_subordinate_statute_name_beats_parent_alias(self):
        parent = replace(
            fixture_document(4),
            title="근로기준법 제1조 목적",
            metadata={**self.document.metadata, "law_name": "근로기준법", "article_number": 1, "sub_article_number": 0},
        )
        decree = replace(
            fixture_document(5),
            title="근로기준법 시행령 제1조 목적",
            metadata={**self.document.metadata, "law_name": "근로기준법 시행령", "article_number": 1, "sub_article_number": 0},
        )
        self.store.upsert(parent)
        self.store.upsert(decree)
        self.rag.retriever.refresh_exact_index()
        self.model.broken = True
        result = self.ask("근로기준법 시행령 제1조")
        self.assertEqual(result["status"], "grounded_excerpt")
        self.assertEqual(result["citations"][0]["evidence_id"], decree.id)
        self.assertNotEqual(result["citations"][0]["evidence_id"], parent.id)

    def test_topic_gate_rejects_unrelated_purpose_and_confiscation(self):
        d = replace(self.document, title="근로기준법 시행령 제1조 목적", metadata={**self.document.metadata, "law_name": "근로기준법 시행령"})
        self.assertFalse(title_anchor(d, "근로기준법 해고예고 관련 조문을 찾아줘"))
        d = replace(d, title="근로기준법 제26조 해고의 예고", metadata={**d.metadata, "law_name": "근로기준법"})
        self.assertTrue(title_anchor(d, "근로기준법 해고 관련 조문을 찾아줘"))


class EvaluationAndIngestTests(unittest.TestCase):
    def test_online_refresh_prioritizes_explicit_canonical_law_name(self):
        retriever = OfficialAPIRetriever(object())
        with patch("services.law.query_expander.search_with_query_expansion", return_value=[]), \
             patch("services.law.full_text.get_full_law", return_value={"status": "success"}) as full, \
             patch("services.evidence.precedent.search_precedents", return_value=[]), \
             patch("services.library.search.search_library", return_value=[]), \
             patch("legal_rag.ingest.ingest_api_cache", return_value={}):
            result = retriever.refresh("헌법 1조 1항 뭐야?")
        full.assert_called_once_with("대한민국헌법")
        self.assertEqual(result["sources"][0]["query"], "대한민국헌법")

    def test_minimum_coverage_gate_detects_material_source_loss(self):
        coverage = {"documents_valid": 90, "hierarchies": {"precedent": 3}, "domains": {"criminal": 50}}
        manifest = {"baseline_created_at": "fixture", "max_allowed_drop_fraction": .05,
                    "documents_valid": 100, "hierarchies": {"precedent": 50}, "domains": {"criminal": 50}}
        result = minimum_coverage_gate(coverage, manifest)
        self.assertFalse(result["passed"])
        self.assertEqual({x["name"] for x in result["deficits"]}, {"documents_valid", "precedent"})

    def test_metrics_and_absent_gold_gate(self):
        m = retrieval_metrics(["wrong", "right"], {"right": 3})
        self.assertEqual(m["recall"], 1)
        self.assertEqual(m["mrr"], .5)
        self.assertAlmostEqual(m["ndcg"], 1 / __import__("math").log2(3))
        self.assertIsNone(retrieval_metrics(["wrong"], {})["recall"])
        self.assertFalse(release_gate()["production_ready"])

    def test_split_leakage_and_fabricated_gold_structure(self):
        row = {"id": "1", "question": "독립 평가 질문", "domain": "형사", "scenario_group": "same",
               "split": "dev", "relevant_documents": {"fixture": 3}, "reviewer": "test-only", "reviewed_at": "2026-09-19", "answerable": True}
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "gold.jsonl"
            path.write_text(json.dumps(row, ensure_ascii=False), encoding="utf-8")
            self.assertEqual(len(load_gold(path)), 1)
            second = dict(row, id="2", question="다른 표현", split="test")
            path.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in [row, second]), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "split_leakage"):
                load_gold(path)

    def test_statute_response_version_mismatch(self):
        with patch("services.law.full_text_parser.parse_full_law", return_value={"mst": "2"}):
            with self.assertRaisesRegex(ValueError, "source_version_mismatch"):
                statute_documents({}, {"MST": "1"}, "", "")

    def test_statute_effective_date_mismatch(self):
        with patch("services.law.full_text_parser.parse_full_law", return_value={"mst": "1", "effective_date": "20200101"}):
            with self.assertRaisesRegex(ValueError, "source_effective_date_mismatch"):
                statute_documents({}, {"MST": "1", "efYd": "20210101"}, "", "")

    def test_case_requires_matching_detail_identity(self):
        raw = {"PrecService": {"판례정보일련번호": "1", "사건번호": "fixture", "법원명": "fixture", "선고일자": "20200101", "판례내용": "본문", "판시사항": "쟁점"}}
        self.assertEqual(precedent_documents(raw, {"ID": "2"}, "", ""), [])
        self.assertEqual(len(precedent_documents(raw, {"ID": "1"}, "", "")), 1)

    def test_local_ordinance_identity_and_article_parsing(self):
        raw = {"LawService": {"자치법규기본정보": {"자치법규ID": "2", "자치법규명": "가상시 교육 조례",
            "자치법규일련번호": "3", "지자체기관명": "가상시", "시행일자": "20200101", "자치법규종류": "조례"},
            "조문": {"조": {"조문번호": "001002", "조제목": "교육", "조내용": "제10조의2 시험 원문"}}}}
        self.assertEqual(ordinance_documents(raw, "wrong"), [])
        docs = ordinance_documents(raw, "3")
        self.assertEqual((docs[0].metadata["article_number"], docs[0].metadata["sub_article_number"]), (10, 2))
        self.assertEqual(hierarchy(docs[0]), "local_ordinance")
        self.assertEqual(domain(docs[0]), "education")
        self.assertEqual(__import__("legal_rag.verify", fromlist=["document_errors"]).document_errors(docs[0]), [])

    def test_administrative_rule_identity_and_whole_unit(self):
        raw = {"AdmRulService": {"행정규칙기본정보": {"행정규칙ID": "4", "행정규칙일련번호": "5",
            "행정규칙명": "교육 시험 고시", "행정규칙종류": "고시", "소관부처명": "교육부", "시행일자": "20200101"},
            "조문내용": "<b>시험</b> 원문"}}
        self.assertEqual(administrative_rule_documents(raw, "wrong"), [])
        docs = administrative_rule_documents(raw, "5")
        self.assertEqual(docs[0].text, "시험 원문")
        self.assertEqual(hierarchy(docs[0]), "administrative_rule")
        self.assertEqual(__import__("legal_rag.verify", fromlist=["document_errors"]).document_errors(docs[0]), [])


if __name__ == "__main__":
    unittest.main()
