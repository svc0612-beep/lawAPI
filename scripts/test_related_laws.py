# ============================================================
# 공식 법령 관계 단위 / 실 API 테스트
# ============================================================

import json
import os
import sqlite3
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


from services.law.related_laws import (
    get_official_related_laws,
)

from services.law.related_laws_parser import (
    parse_law_system_map,
)


SAMPLE_RESPONSE = {
    "법령체계도": {
        "관련법령": {
            "conlaw": {
                "법령명": "관련 기본법",
                "법령ID": "900000",
                "법령일련번호": "900001",
                "법종구분": {
                    "content": "법률",
                },
            },
        },
        "상하위법": {
            "법률": {
                "기본정보": {
                    "법령명": "테스트법",
                    "법령ID": "100000",
                    "법령일련번호": "100001",
                    "법종구분": {
                        "content": "법률",
                    },
                },
                "시행령": [
                    {
                        "기본정보": {
                            "법령명": "테스트법 시행령",
                            "법령ID": "200000",
                            "법령일련번호": "200001",
                            "법종구분": {
                                "content": "대통령령",
                            },
                        },
                        "시행규칙": {
                            "기본정보": {
                                "법령명": "테스트법 시행규칙",
                                "법령ID": "300000",
                                "법령일련번호": "300001",
                                "법종구분": {
                                    "content": "부령",
                                },
                            },
                        },
                    },
                    {
                        "기본정보": {
                            "법령명": "테스트법 별도 하위규정",
                            "법령ID": "210000",
                            "법령일련번호": "210001",
                            "법종구분": {
                                "content": "대통령령",
                            },
                        },
                    },
                ],
                "행정규칙": {
                    "고시": {
                        "기본정보": {
                            "행정규칙명": "테스트 고시",
                            "행정규칙ID": "400000",
                            "행정규칙일련번호": "400001",
                            "법종구분": {
                                "content": "고시",
                            },
                        },
                    },
                },
            },
        },
    },
}


def test_parser_for_primary_law() -> None:

    result = parse_law_system_map(
        raw_data=SAMPLE_RESPONSE,
        source_law_name="테스트법",
        source_mst="100001",
        source_law_id="100000",
    )

    by_name = {
        item["target_law_name"]: item
        for item in result
    }

    assert "테스트법" not in by_name
    assert "테스트 고시" not in by_name
    assert by_name[
        "테스트법 시행령"
    ]["relation_type"] == "시행령"
    assert by_name[
        "테스트법 시행규칙"
    ]["relation_type"] == "시행규칙"
    assert by_name[
        "테스트법 별도 하위규정"
    ]["relation_type"] == "시행령"
    assert by_name[
        "관련 기본법"
    ]["relation_type"] == "관련법령"


def test_parser_for_subordinate_law() -> None:

    result = parse_law_system_map(
        raw_data=SAMPLE_RESPONSE,
        source_law_name="테스트법 시행령",
        source_mst="200001",
        source_law_id="200000",
    )

    by_name = {
        item["target_law_name"]: item
        for item in result
    }

    assert by_name[
        "테스트법"
    ]["relation_type"] == "상위법령"
    assert by_name[
        "테스트법 시행규칙"
    ]["relation_type"] == "시행규칙"
    assert "테스트법 별도 하위규정" not in by_name


def test_live_patent_law() -> None:

    result = get_official_related_laws(
        law_name="특허법",
        mst="279827",
        law_id="001455",
    )

    assert result["status"] == "success"

    names = {
        item["target_law_name"]
        for item in result["related_laws"]
    }

    assert "특허법 시행령" in names
    assert "특허법 시행규칙" in names

    assert all(
        item["target_law_name"] != "특허법"
        for item in result["related_laws"]
    )

    assert all(
        item["target_law_type"] not in {
            "훈령",
            "예규",
            "고시",
        }
        for item in result["related_laws"]
    )

    print(
        "LIVE_COUNT=",
        result["count"],
    )

    print(
        "LIVE_NAMES=",
        sorted(names),
    )


def test_cache_does_not_store_credentials() -> None:

    db_path = os.path.join(
        PROJECT_ROOT,
        "data",
        "api_cache.db",
    )

    connection = sqlite3.connect(
        db_path
    )

    try:

        rows = connection.execute(
            """
            SELECT request_params
            FROM api_cache
            WHERE endpoint = ?
            """,
            (
                "lawService-lsStmd",
            ),
        ).fetchall()

    finally:
        connection.close()

    assert rows

    sensitive_keys = {
        "oc",
        "servicekey",
        "apikey",
        "api_key",
    }

    for row in rows:

        params = json.loads(
            row[0]
        )

        assert not any(
            str(key).lower() in sensitive_keys
            for key in params
        )

    print(
        "CACHE_SECURITY=PASS"
    )


if __name__ == "__main__":

    test_parser_for_primary_law()
    test_parser_for_subordinate_law()

    print(
        "PARSER_TESTS=PASS"
    )

    test_live_patent_law()

    test_cache_does_not_store_credentials()

    print(
        "LIVE_TEST=PASS"
    )
