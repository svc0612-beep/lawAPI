"""Additional live checks for explicit, unknown and malformed legal questions."""
import argparse
import contextlib
import io
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.query_service import process_law_question
from services.generation.response_builder import answer_question

CASES = [
    ("헌법 제1조 제1항 알려줘", "대한민국헌법", 1),
    ("특허법 제29조 알려줘", "특허법", 29),
    ("헌법 제999조 알려줘", None, None),
    ("민법 제750조 알려줘", "민법", 750),
    ("기본권을 침해당했는데 헌법소원은 어떻게 해?", "헌법재판소법", 68),
    ("우주 해적 면허 갱신 수수료를 알려줘", None, None),
]
parser = argparse.ArgumentParser()
parser.add_argument("--output-dir", default="data/verification_20260919")
args = parser.parse_args()
out = Path(args.output_dir)
out.mkdir(parents=True, exist_ok=True)
report = []
for index, (question, expected_law, expected_article) in enumerate(CASES, 1):
    with contextlib.redirect_stdout(io.StringIO()):
        response = answer_question(question)
    result = response["evidence"]
    rows = result.get("verified_laws", [])
    checks = {
        "no_freeform_llm": not response["llm_used"],
        "has_safe_answer": bool(response["answer"]),
        "no_unverified_primary_conclusion": "자동 확정" not in response["answer"],
    }
    if expected_law:
        checks["expected_article"] = any(r["law_name"] == expected_law and r["article_number"] == expected_article for r in rows)
    elif "999" in question:
        checks["nonexistent_article_not_answered"] = not rows
    else:
        checks["no_claim_of_applicability"] = "처벌이나 법적 결론을 제시하지 않습니다" in response["answer"] or "아직 확정하지 않았습니다" in response["answer"]
    report.append(dict(question=question, checks=checks, passed=all(checks.values()), status=response["status"],
                       articles=[(r["law_name"], r["article_number"]) for r in rows]))
    (out / f"extended_{index:02}.json").write_text(json.dumps(response, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "extended_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(index, "PASS" if all(checks.values()) else "FAIL", question, report[-1]["articles"], flush=True)
sys.exit(0 if all(x["passed"] for x in report) else 1)
