"""Offline regression checks for the restored Korean question analyzer."""

import unittest
from pathlib import Path

from agents.query_analyzer import analyze_question, make_search_query


class QueryAnalyzerTests(unittest.TestCase):
    def test_explicit_articles(self):
        for question, law, article, sub, paragraph in [
            ("헌법 1조 알려줘", "대한민국헌법", 1, 0, None),
            ("특허법 제29조 알려줘", "특허법", 29, 0, None),
            ("특허법 제10조의2 제3항 알려줘", "특허법", 10, 2, 3),
            ("형법 250조 1항 뭐야?", "형법", 250, 0, 1),
        ]:
            with self.subTest(question=question):
                result = analyze_question(question)
                self.assertEqual(result["law_name"], law)
                self.assertEqual(result["article_number"], article)
                self.assertEqual(result["sub_article_number"], sub)
                self.assertEqual(result["paragraph_number"], paragraph)
                self.assertEqual(result["question_type"], "특정_조문조회")

    def test_topic_is_not_forced_to_a_law(self):
        for question in ["장애인 취업 관련 법 알려줘", "국민의 기본권은 어떤 경우에 제한할 수 있어?"]:
            with self.subTest(question=question):
                result = analyze_question(question)
                self.assertIsNone(result["law_name"])
                self.assertEqual(result["question_type"], "관련_법령탐색")
        self.assertEqual(analyze_question("장애인 취업 관련 법 알려줘")["search_query"], "장애인 취업")

    def test_korean_request_phrases_are_removed(self):
        for phrase in ["알려줘", "알려 줘", "보여줘", "보여 줘", "찾아줘", "찾아 줘", "설명해줘", "설명해 줘"]:
            with self.subTest(phrase=phrase):
                self.assertEqual(make_search_query("임금 체불 " + phrase, None), "임금 체불")

    def test_full_text(self):
        self.assertEqual(analyze_question("장애인복지법 전문 보여줘")["question_type"], "법령_전체조회")

    def test_article_original_text_is_not_whole_statute(self):
        result = analyze_question("형법 제260조 원문을 보여줘")
        self.assertEqual(result["question_type"], "특정_조문조회")
        self.assertEqual(result["article_number"], 260)

    def test_constitutional_complaint_is_not_an_explicit_constitution_name(self):
        self.assertIsNone(analyze_question("기본권 침해 헌법소원 절차")["law_name"])
        self.assertEqual(analyze_question("헌법재판소법 제68조")["law_name"], "헌법재판소법")
        self.assertIsNone(analyze_question("불법 주차 처벌")["law_name"])

    def test_source_is_valid_utf8_without_corrupted_literals(self):
        source = (Path(__file__).resolve().parents[1] / "agents/query_analyzer.py").read_text(encoding="utf-8")
        self.assertNotIn("???", source)
        self.assertNotIn("\ufffd", source)


if __name__ == "__main__":
    unittest.main()
