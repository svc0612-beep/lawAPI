# ============================================================
# 공식 법령 관계 query_service 회귀 테스트
# ============================================================

import os
import sys


CURRENT_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

PROJECT_ROOT = os.path.dirname(
    CURRENT_DIR
)

if PROJECT_ROOT not in sys.path:
    sys.path.append(
        PROJECT_ROOT
    )


from services.query_service import (
    process_law_question,
)


def test_constitution_article() -> None:

    result = process_law_question(
        "헌법 1조 1항 뭐야?"
    )

    assert result["status"] == "success"
    assert result["evidence_found"] is True
    assert result["article"] is not None
    assert (
        "대한민국은 민주공화국이다"
        in result["article"]["full_article_text"]
    )

    print(
        "CONSTITUTION=PASS"
    )


def test_patent_law_relations() -> None:

    result = process_law_question(
        "특허법 알려줘"
    )

    assert result["status"] == "success"
    assert result["evidence_found"] is True

    related_laws = result.get(
        "related_laws",
        [],
    )

    by_name = {
        item["target_law_name"]: item
        for item in related_laws
    }

    assert by_name[
        "특허법 시행령"
    ]["relation_type"] == "시행령"
    assert by_name[
        "특허법 시행규칙"
    ]["relation_type"] == "시행규칙"

    ls_stmd_status = next(
        item
        for item in result["source_status"]
        if item["endpoint"] == "lsStmd"
    )

    assert ls_stmd_status[
        "result_count"
    ] == len(related_laws)

    print(
        "PATENT_RELATED_COUNT=",
        len(related_laws),
    )

    print(
        "PATENT_RELATED_NAMES=",
        sorted(by_name),
    )

    print(
        "PATENT=PASS"
    )


if __name__ == "__main__":

    test_constitution_article()
    test_patent_law_relations()

    print(
        "QUERY_SERVICE_REGRESSION=PASS"
    )
