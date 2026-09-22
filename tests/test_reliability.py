import copy
import unittest
from unittest.mock import patch, Mock

from services.law.search_hints import match_profiles, search_hints
from services.evidence.verified_retrieval import (
    valid_current_law, select_original_articles, collect_verified_topic, references,
    collect_verified_explicit,
)
from services.evidence.reliability import finalize_evidence
from services.evidence.precedent import search_precedents
from services.library.nanet_xml import validate_response_status
from services.library.search import search_library
from services.library.automatic import attach_library_search
from services.generation.response_assembler import build_final_response
from services.generation.response_builder import answer_question
from services.law.query_expander import _is_officially_validated_term, search_with_query_expansion


def article(n, title, text, sub=0):
    return dict(article_number=n, sub_article_number=sub, article_title=title,
                full_text=text, effective_date="20200101", paragraphs=[])


def law(articles):
    return dict(status="success", law_name="테스트법", mst="123", effective_date="20200101", articles=articles)


class SearchHintsTests(unittest.TestCase):
    def test_paraphrases(self):
        for question, expected in [("술 마시고 운전했어요", "도로교통법"),
                                   ("임금이 체불됐어요", "근로기준법"),
                                   ("기본권 제한이 가능한가요", "대한민국헌법")]:
            with self.subTest(question=question):
                self.assertIn(expected, search_hints(question)["law_names"])

    def test_not_just_one_ambiguous_word(self):
        self.assertEqual(match_profiles("술 가격이 얼마야?"), [])
        self.assertEqual(match_profiles("자동차 수리 비용"), [])

    def test_multi_issue_preserved(self):
        hints = search_hints("음주운전하고 사람을 때렸어요")
        self.assertIn("도로교통법", hints["law_names"])
        self.assertIn("형법", hints["law_names"])

    def test_exceptions_are_additional_candidates(self):
        profiles = match_profiles("정당방위로 때렸다는 13살 학생")
        self.assertTrue(any(p["id"] == "criminal_defenses" for p in profiles))
        self.assertTrue(any(p["id"] == "criminal_age" for p in profiles))
        self.assertIn("소년법", search_hints("13살 아이가 폭행했어")["law_names"])

    def test_scope_and_injury_sources_preserved(self):
        self.assertIn("근로기준법 시행령", search_hints("3명 회사 해고") ["law_names"])
        self.assertIn("특정범죄 가중처벌 등에 관한 법률", search_hints("음주운전 사고") ["law_names"])

    def test_age_alone_does_not_add_criminal_law(self):
        self.assertNotIn("형법", search_hints("13살 아이 학교 준비물") ["law_names"])

    def test_no_article_or_sentence_in_hints(self):
        self.assertEqual(set(search_hints("음주운전")), {"profile_ids", "terms", "law_names"})

    @patch("services.law.query_expander._search_official_terms", return_value=("다른 용어",))
    def test_unrelated_official_term_does_not_validate(self, _):
        self.assertFalse(_is_officially_validated_term("가짜용어"))

    @patch("services.law.query_expander._search_official_terms", return_value=("임금 지급",))
    def test_whitespace_normalization(self, _):
        self.assertTrue(_is_officially_validated_term("임금지급"))


class OriginalValidationTests(unittest.TestCase):
    @patch("services.evidence.verified_retrieval.get_full_law")
    def test_nonexistent_exact_article_does_not_fall_back(self, fetch):
        fetch.return_value = law([article(1, "조문", "본문")])
        result = collect_verified_explicit("테스트법 제999조", {"question_type": "특정_조문조회", "law_name": "테스트법", "article_number": 999})
        self.assertEqual(result["laws"], [])
        self.assertEqual(result["source_status"][0]["status"], "not_found")

    @patch("services.evidence.verified_retrieval.get_full_law")
    def test_full_law_without_ancillary_sources(self, fetch):
        fetch.return_value = law([article(1, "조문", "본문")])
        result = finalize_evidence(collect_verified_explicit("테스트법 전문", {"question_type": "법령_전체조회", "law_name": "테스트법"}))
        self.assertEqual(result["status"], "success")
        self.assertIn("전문 1개 조문", build_final_response(result))

    def test_identity_and_date_required(self):
        base = law([article(1, "행위", "원문")])
        self.assertTrue(valid_current_law(base, "테스트법"))
        for change in [dict(law_name="다른법"), dict(mst=""), dict(effective_date="20990101"),
                       dict(effective_date=""), dict(articles=[]), dict(status="error")]:
            with self.subTest(change=change):
                self.assertFalse(valid_current_law(base | change, "테스트법"))

    def test_general_assault_not_special_assault(self):
        data = law([article(1, "특수폭행", "특수 원문"), article(2, "폭행, 존속폭행", "기본 원문"), article(3, "폭행치사상", "결과 원문")])
        selected = select_original_articles(data, (("폭행",),))
        self.assertEqual([x["article_number"] for x in selected], [2])

    def test_same_title_in_different_chapter(self):
        data = law([article(1, "청구기간", "권한쟁의 기간") | {"section_headers": ["권한쟁의심판"]},
                    article(2, "청구기간", "헌법소원 기간") | {"section_headers": ["헌법소원심판"]}])
        selected = select_original_articles(data, (("헌법소원", "청구기간"),))
        self.assertEqual([r["article_number"] for r in selected], [2])

    def test_sanction_must_reference_selected_article(self):
        data = law([article(2, "기본행위", "그 행위의 요건과 예외"),
                    article(8, "벌칙", "제2조제1항을 위반한 경우에만 해당한다."),
                    article(9, "벌칙", "제3조를 위반한 자")])
        selected = select_original_articles(data, (("기본행위",),))
        self.assertEqual([x["article_number"] for x in selected], [2, 8])
        self.assertEqual(selected[1]["article_text"], data["articles"][1]["full_text"])

    def test_sub_article_not_confused(self):
        self.assertEqual(references("제44조의2제1항"), {(44, 2)})

    def test_bounded_reference_range(self):
        self.assertIn((3, 0), references("제2조부터 제4조까지"))
        self.assertNotIn((500, 0), references("제1조부터 제1000조까지"))

    def test_future_article_excluded(self):
        data = law([article(1, "행위", "원문") | {"effective_date": "20990101"}])
        self.assertEqual(select_original_articles(data, (("행위",),)), [])

    @patch("services.evidence.reliability.get_full_law")
    def test_mismatching_version_is_not_replaced(self, fetch):
        fetch.return_value = law([article(1, "조문", "본문")])
        result = finalize_evidence({"laws": [{"law_name": "테스트법", "mst": "999", "article_number": 1}]})
        self.assertEqual(result["verified_laws"], [])
        self.assertEqual(result["status"], "partial")

    @patch("services.evidence.reliability.get_full_law")
    def test_search_snippet_replaced_by_original(self, fetch):
        fetch.return_value = law([article(1, "조문", "조건과 예외를 포함한 원문")])
        result = finalize_evidence({"original_question": "조건과 예외", "laws": [{"law_name": "테스트법", "mst": "123", "article_number": 1, "article_text": "잘못된 검색 요약"}]})
        self.assertEqual(result["verified_laws"][0]["article_text"], "조건과 예외를 포함한 원문")


class FailureTests(unittest.TestCase):
    @patch("services.law.query_expander.search_related_laws", side_effect=RuntimeError("SECRET"))
    def test_general_search_error_not_swallowed(self, _):
        with self.assertRaises(RuntimeError) as error:
            search_with_query_expansion("알 수 없는 일반 질문")
        self.assertNotIn("SECRET", str(error.exception))

    def test_library_errors_not_empty_success(self):
        for data in [{}, {"OpenAPI_ServiceResponse": {"returnReasonCode": "30"}},
                     {"response": {"header": {"resultCode": "30"}}}, {"response": {"header": {}}}]:
            with self.subTest(data=data), self.assertRaises(RuntimeError):
                validate_response_status(data)
        validate_response_status({"response": {"header": {"resultCode": "00"}}})

    @patch("services.library.search.validate_nanet_api_key")
    @patch("services.library.search.get_cache", return_value={"response": {"header": {"resultCode": "30"}}})
    @patch("services.library.search.requests.get")
    def test_cached_error_not_treated_as_no_results(self, request, cache, key):
        with self.assertRaises(RuntimeError):
            search_library("질문")
        request.assert_not_called()

    @patch("services.library.automatic.search_library", side_effect=RuntimeError("SECRET"))
    def test_library_failure_visible_without_secret(self, _):
        result = attach_library_search({"original_question": "음주운전"})
        self.assertEqual(result["source_status"][0]["status"], "error")
        self.assertNotIn("SECRET", str(result))

    @patch("services.evidence.verified_retrieval.search_precedents", return_value=[])
    @patch("services.evidence.verified_retrieval.get_full_law", side_effect=RuntimeError("SECRET"))
    def test_official_failure_cannot_create_evidence(self, fetch, cases):
        result = collect_verified_topic("음주운전")
        self.assertEqual(result["laws"], [])
        self.assertFalse(result["evidence_found"])
        self.assertEqual(result["source_status"][0]["status"], "error")
        self.assertNotIn("SECRET", str(result))

    def test_no_unverified_generated_claim(self):
        text = build_final_response({"laws": [{"article_text": "원문 없는 검색 후보"}]},
                                    {"status": "success", "answer": "벌금 9999만원이 확정됩니다"})
        self.assertNotIn("9999", text)
        self.assertNotIn("원문 없는 검색 후보", text)
        self.assertIn("확인하지 못했습니다", text)

    @patch("services.generation.response_builder.process_law_question", return_value={"status": "error", "source_status": [{"source": "법제처", "endpoint": "collection", "status": "error", "message": "조회 실패"}]})
    @patch("services.generation.response_builder.generate_answer")
    def test_error_status_preserved_and_llm_not_published(self, llm, process):
        result = answer_question("질문", use_llm=True)
        self.assertEqual(result["status"], "error")
        self.assertFalse(result["llm_used"])
        self.assertIn("조회 실패", result["answer"])
        llm.assert_not_called()


class PrecedentTests(unittest.TestCase):
    def setUp(self):
        self.item = {"사건명": "사건", "사건번호": "2020도1", "법원명": "대법원", "선고일자": "20200101", "판례일련번호": "123"}
        self.detail = {"PrecService": {"판례정보일련번호": "123", "사건번호": "2020도1", "법원명": "대법원", "선고일자": "20200101", "판례내용": "판결 원문", "판결요지": "판결 요지"}}

    def run_case(self, detail):
        with patch("services.evidence.precedent.fetch_precedent_search_data", return_value={"prec": [self.item]}), patch("services.evidence.precedent.fetch_precedent_detail_data", return_value=detail):
            return search_precedents("검색")[0]

    def test_verified_identity(self):
        item = self.run_case(self.detail)
        self.assertTrue(item["detail_verified"])
        self.assertEqual(item["full_text"], "판결 원문")
        self.assertIn("precSeq=123", item["official_link"])

    def test_other_case_cannot_be_merged(self):
        self.detail["PrecService"]["사건번호"] = "2021도999"
        item = self.run_case(self.detail)
        self.assertFalse(item["detail_verified"])
        self.assertFalse(item["full_text"])

    def test_missing_body_is_not_verified(self):
        self.detail["PrecService"]["판례내용"] = ""
        self.assertFalse(self.run_case(self.detail)["detail_verified"])

    def test_mismatching_decision_date_is_not_verified(self):
        self.detail["PrecService"]["선고일자"] = "20210101"
        self.assertFalse(self.run_case(self.detail)["detail_verified"])

    def test_title_only_not_used_as_sentence(self):
        text = build_final_response({"precedents": [{"case_name": "징역 10년", "case_number": "2020도1"}]})
        self.assertNotIn("징역 10년", text)


if __name__ == "__main__":
    unittest.main()
