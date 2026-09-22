# ============================================================
# 국회도서관 detail / toc 파서
# ============================================================

import re

from services.library.nanet_utils import (
    normalize_text,
    split_keywords,
)


# ============================================================
# 1. detail name/value 구조 → dict
# ============================================================

def extract_detail_fields(
    data: dict
):

    response = data.get(
        "response",
        {}
    )

    items = response.get(
        "item",
        []
    )

    if isinstance(
        items,
        dict
    ):

        items = [
            items
        ]

    if not isinstance(
        items,
        list
    ):

        return {}

    fields = {}

    for item in items:

        if not isinstance(
            item,
            dict
        ):

            continue

        name = normalize_text(
            item.get(
                "name"
            )
        )

        value = normalize_text(
            item.get(
                "value"
            )
        )

        if not name:

            continue

        fields[
            name
        ] = value

    return fields


# ============================================================
# 2. detail 결과 정규화
# ============================================================

def normalize_detail_record(
    data: dict,
    control_no: str
):

    fields = extract_detail_fields(
        data
    )

    return {

        "control_no":
            fields.get(
                "제어번호",
                normalize_text(
                    control_no
                )
            ),

        "title":
            fields.get(
                "자료명",
                ""
            ),

        "author":
            fields.get(
                "저자명",
                ""
            ),

        "publisher":
            fields.get(
                "발행자",
                ""
            ),

        "publication_year":
            fields.get(
                "발행년도",
                ""
            ),

        "keywords":
            split_keywords(
                fields.get(
                    "키워드",
                    ""
                )
            ),

        "isbn":
            fields.get(
                "ISBN",
                ""
            ),

        "issn":
            fields.get(
                "ISSN",
                ""
            ),

        "language":
            fields.get(
                "본문언어",
                ""
            ),

        "call_number":
            fields.get(
                "청구기호",
                ""
            ),

        "library_room":
            fields.get(
                "자료실",
                ""
            ),

        "has_original_db":
            fields.get(
                "원문DB유무",
                ""
            ),

        "has_toc":
            fields.get(
                "목차",
                ""
            ),

        "copyright_permission":
            fields.get(
                "저작권허락",
                ""
            ),

        "voice_support":
            fields.get(
                "음성지원유무",
                ""
            ),

        "all_fields":
            fields,

        "raw":
            data,
    }


# ============================================================
# 3. 목차 원문 추출
# ============================================================

def extract_toc_text(
    data: dict
):

    response = data.get(
        "response",
        {}
    )

    if not isinstance(
        response,
        dict
    ):

        return ""

    return normalize_text(
        response.get(
            "toc"
        )
    )


# ============================================================
# 4. 목차 문자열 → 리스트
# ============================================================

def parse_toc_items(
    toc_text: str
):

    toc_text = normalize_text(
        toc_text
    )

    if not toc_text:

        return []

    parts = re.split(
        r"<p\s*/?>",
        toc_text,
        flags=re.IGNORECASE
    )

    results = []

    for part in parts:

        part = re.sub(
            r"\s+",
            " ",
            part
        ).strip()

        if not part:

            continue

        results.append(
            part
        )

    return results


# ============================================================
# 5. toc 결과 정규화
# ============================================================

def normalize_toc_record(
    data: dict,
    control_no: str
):

    toc_text = extract_toc_text(
        data
    )

    toc_items = parse_toc_items(
        toc_text
    )

    return {

        "control_no":
            normalize_text(
                control_no
            ),

        "toc_text":
            toc_text,

        "toc_items":
            toc_items,

        "raw":
            data,
    }