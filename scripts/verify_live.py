"""Live retrieval acceptance checks; emits failures, not unconditional success."""
import argparse
import contextlib
import io
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.query_service import process_law_question
from services.generation.response_core import build_core_answer

CASES = [
    ("국민의 기본권은 어떤 경우에 제한할 수 있어?", "대한민국헌법", 37),
    ("월급을 안 주면 어떻게 돼?", "근로기준법", 43),
    ("직원을 이유 없이 해고하면 어떻게 돼?", "근로기준법", 23),
    ("퇴직금을 안 주면 어떻게 돼?", "근로자퇴직급여 보장법", 9),
    ("음주운전하면 어떻게 돼?", "도로교통법", 44),
    ("무면허 운전하면 어떻게 돼?", "도로교통법", 43),
    ("사람을 때리면 어떻게 돼?", "형법", 260),
    ("인터넷에 다른 사람 욕을 올리면 어떻게 돼?", "형법", 311),
    ("다른 사람 특허를 침해하면 어떻게 돼?", "특허법", 225),
    ("개인정보를 동의 없이 수집하면 어떻게 돼?", "개인정보 보호법", 15),
    ("인터넷 쇼핑몰이 환불을 안 해주면 어떻게 돼?", "전자상거래 등에서의 소비자보호에 관한 법률", 17),
    ("행정처분에 불복하려면 어떻게 해야 해?", "행정심판법", 27),
]

parser = argparse.ArgumentParser()
parser.add_argument("--limit", type=int, default=12)
parser.add_argument("--output-dir", default="data/verification_20260919")
args = parser.parse_args()
out = Path(args.output_dir)
out.mkdir(exist_ok=True)
report = []
for index, (question, law, article) in enumerate(CASES[:args.limit], 1):
    with contextlib.redirect_stdout(io.StringIO()):
        result = process_law_question(question)
        answer = build_core_answer(result)
    rows = result.get("verified_laws", [])
    checks = {
        "expected_original_retrieved": any(r["law_name"] == law and r["article_number"] == article for r in rows),
        "all_originals_cited": all(r.get("official_link") and r.get("text_sha256") and r["article_text"] in answer.replace("> ", "") for r in rows),
        "no_applicability_claim": result.get("metadata", {}).get("legal_applicability_confirmed") is False,
        "library_status_exposed": any(s["source"] == "국회도서관" for s in result.get("source_status", [])),
    }
    entry = dict(index=index, question=question, checks=checks, passed=all(checks.values()),
                 articles=[(r["law_name"], r["article_number"], r["role"]) for r in rows],
                 verified_precedents=sum(bool(p.get("detail_verified")) for p in result.get("precedents", [])),
                 source_status=result.get("source_status", []))
    report.append(entry)
    (out / f"case_{index:02}.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / f"case_{index:02}.md").write_text(answer, encoding="utf-8")
    (out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(index, "PASS" if entry["passed"] else "FAIL", question, entry["articles"], flush=True)
sys.exit(0 if all(r["passed"] for r in report) else 1)
