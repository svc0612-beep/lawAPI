"""Exercise Streamlit's actual widget and rendering path with a saved API result."""
import json
import unittest
from pathlib import Path
from unittest.mock import patch
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


class StreamlitTests(unittest.TestCase):
    @staticmethod
    def rag_result(question, answer, status="grounded_excerpt", history=0):
        return {
            "status": status,
            "question_type": "검증형_RAG_대화",
            "original_question": question,
            "answer": answer,
            "citations": [],
            "verification": {"passed": status == "grounded_excerpt"},
            "diagnostics": {"history_user_turns": history},
        }

    def test_partial_result_still_renders_verified_full_law(self):
        result = {
            "status": "partial",
            "question_type": "법령_전체조회",
            "original_question": "민법 전체 보여줘",
            "search_query": "민법",
            "metadata": {"full_law_verified": True},
            "full_law": {
                "status": "success",
                "law_name": "민법",
                "law_type": "법률",
                "ministry": "법무부",
                "effective_date": "20260317",
                "article_count": 1,
                "articles": [{
                    "article_number": 1,
                    "sub_article_number": 0,
                    "article_title": "법원",
                    "section_headers": ["제1장 통칙"],
                    "full_text": "제1조(법원) 민사에 관하여 법률에 규정이 없으면 관습법에 의한다.",
                }],
            },
        }
        with patch("services.ui.search_panel.process_law_question", return_value=result):
            app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=15).run()
            app.text_input(key="question_input").set_value(result["original_question"])
            next(b for b in app.button if b.label == "검색").click().run()
            self.assertEqual(len(app.exception), 0)
            rendered = "\n".join(m.value for m in app.markdown)
            self.assertIn("법령 전문", rendered)
            self.assertNotIn("법령 전체 원문을 찾지 못했습니다", [x.value for x in app.warning])

    def test_initial_page_and_submitted_result(self):
        question = "국민의 기본권은 어떤 경우에 제한할 수 있어?"
        result = self.rag_result(
            question,
            "대한민국헌법 제37조 공식 원문입니다.\n\n[국가법령정보센터 원문](https://www.law.go.kr)",
        )
        with patch("services.ui.search_panel.create_legal_session", return_value="session-1"), \
             patch("services.ui.search_panel.ask_legal_question", return_value=result):
            app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=15).run()
            self.assertEqual(len(app.exception), 0)
            app.text_input(key="question_input").set_value(question)
            next(b for b in app.button if b.label == "검색").click().run()
            self.assertEqual(len(app.exception), 0)
            rendered = "\n".join(m.value for m in app.markdown)
            self.assertIn("대한민국헌법 제37조", rendered)
            self.assertIn("국가법령정보센터 원문", rendered)

    def test_multiturn_reuses_session_and_renders_context_count(self):
        calls = []

        def fake_ask(user_id, session_id, question, new_topic=False):
            calls.append((user_id, session_id, question, new_topic))
            return self.rag_result(
                question,
                f"공식 원문 응답: {question}",
                history=max(0, len(calls) - 1),
            )

        with patch("services.ui.search_panel.create_legal_session", return_value="session-1") as create, \
             patch("services.ui.search_panel.ask_legal_question", side_effect=fake_ask):
            app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=15).run()
            app.text_input(key="question_input").set_value("첫 질문")
            next(b for b in app.button if b.label == "검색").click().run()
            app.text_input(key="question_input").set_value("그 경우에는?")
            next(b for b in app.button if b.label == "검색").click().run()

            self.assertEqual(len(app.exception), 0)
            self.assertEqual(create.call_count, 1)
            self.assertEqual([call[1] for call in calls], ["session-1", "session-1"])
            self.assertIn("멀티턴 문맥 1개", "\n".join(x.value for x in app.caption))

    def test_error_page(self):
        result = self.rag_result("검색 질문", "공식 조회 실패", status="model_error")
        with patch("services.ui.search_panel.create_legal_session", return_value="session-1"), \
             patch("services.ui.search_panel.ask_legal_question", return_value=result):
            app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=15).run()
            app.text_input(key="question_input").set_value("검색 질문")
            next(b for b in app.button if b.label == "검색").click().run()
            self.assertEqual(len(app.exception), 0)
            self.assertIn("공식 조회 실패", "\n".join(x.value for x in app.markdown))
