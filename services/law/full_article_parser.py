# ============================================================
# 법령 조문 내부 구조 파서
#
# 조
# └─ 항
#    └─ 호
#       └─ 목
#
# 다른 조문으로 재귀 이동하지 않는다.
# ============================================================

from typing import (
    Any,
    Dict,
    List,
)

from services.law.full_text_utils import (
    normalize_text,
    safe_int,
    ensure_list,
)


# ============================================================
# 목
# ============================================================

def parse_mok_items(
    value: Any
) -> List[Dict[str, Any]]:

    items = []

    for raw_item in ensure_list(
        value
    ):

        if not isinstance(
            raw_item,
            dict
        ):
            continue

        item = {

            "number":
                normalize_text(
                    raw_item.get(
                        "목번호"
                    )
                ),

            "text":
                normalize_text(
                    raw_item.get(
                        "목내용"
                    )
                ),
        }

        if (
            item["number"]
            or
            item["text"]
        ):

            items.append(
                item
            )

    return items


# ============================================================
# 호
# ============================================================

def parse_ho_items(
    value: Any
) -> List[Dict[str, Any]]:

    items = []

    for raw_item in ensure_list(
        value
    ):

        if not isinstance(
            raw_item,
            dict
        ):
            continue

        item = {

            "number":
                normalize_text(
                    raw_item.get(
                        "호번호"
                    )
                ),

            "text":
                normalize_text(
                    raw_item.get(
                        "호내용"
                    )
                ),

            "items":
                parse_mok_items(
                    raw_item.get(
                        "목"
                    )
                ),
        }

        if (
            item["number"]
            or
            item["text"]
            or
            item["items"]
        ):

            items.append(
                item
            )

    return items


# ============================================================
# 항
# ============================================================

def parse_paragraphs(
    value: Any
) -> List[Dict[str, Any]]:

    paragraphs = []

    for raw_item in ensure_list(
        value
    ):

        if not isinstance(
            raw_item,
            dict
        ):
            continue

        paragraph = {

            "number":
                normalize_text(
                    raw_item.get(
                        "항번호"
                    )
                ),

            "text":
                normalize_text(
                    raw_item.get(
                        "항내용"
                    )
                ),

            "items":
                parse_ho_items(
                    raw_item.get(
                        "호"
                    )
                ),
        }

        if (
            paragraph["number"]
            or
            paragraph["text"]
            or
            paragraph["items"]
        ):

            paragraphs.append(
                paragraph
            )

    return paragraphs


# ============================================================
# 목 텍스트
# ============================================================

def build_mok_text(
    items: List[Dict[str, Any]]
) -> List[str]:

    lines = []

    for item in items:

        text = normalize_text(
            item.get(
                "text"
            )
        )

        if text:
            lines.append(
                text
            )

    return lines


# ============================================================
# 호 텍스트
# ============================================================

def build_ho_text(
    items: List[Dict[str, Any]]
) -> List[str]:

    lines = []

    for item in items:

        text = normalize_text(
            item.get(
                "text"
            )
        )

        if text:

            lines.append(
                text
            )

        lines.extend(
            build_mok_text(
                item.get(
                    "items",
                    []
                )
            )
        )

    return lines


# ============================================================
# 항 텍스트
# ============================================================

def build_paragraph_text(
    paragraphs: List[Dict[str, Any]]
) -> List[str]:

    lines = []

    for paragraph in paragraphs:

        text = normalize_text(
            paragraph.get(
                "text"
            )
        )

        if text:

            lines.append(
                text
            )

        lines.extend(
            build_ho_text(
                paragraph.get(
                    "items",
                    []
                )
            )
        )

    return lines


# ============================================================
# 실제 조문 하나
# ============================================================

def parse_article_node(
    node: Dict[str, Any],
    section_headers: List[str]
) -> Dict[str, Any]:

    article_number = safe_int(
        node.get(
            "조문번호"
        )
    )

    sub_article_number = (
        safe_int(
            node.get(
                "조문가지번호"
            ),
            0
        )
        or 0
    )

    article_title = normalize_text(
        node.get(
            "조문제목"
        )
    )

    article_content = normalize_text(
        node.get(
            "조문내용"
        )
    )

    paragraphs = parse_paragraphs(
        node.get(
            "항"
        )
    )

    # ========================================================
    # 현재 조문 데이터만 사용해서 full_text 생성
    # ========================================================

    lines = []

    if article_content:

        lines.append(
            article_content
        )

    lines.extend(
        build_paragraph_text(
            paragraphs
        )
    )

    # ========================================================
    # 동일 문자열 중복 제거
    # ========================================================

    deduplicated_lines = []

    for line in lines:

        line = normalize_text(
            line
        )

        if not line:
            continue

        if line not in deduplicated_lines:

            deduplicated_lines.append(
                line
            )

    full_text = "\n".join(
        deduplicated_lines
    )

    return {

        "article_number":
            article_number,

        "sub_article_number":
            sub_article_number,

        "article_title":
            article_title,

        "article_content":
            article_content,

        "effective_date":
            normalize_text(
                node.get(
                    "조문시행일자"
                )
            ),

        "article_key":
            normalize_text(
                node.get(
                    "조문키"
                )
            ),

        "section_headers":
            list(
                section_headers
            ),

        "paragraphs":
            paragraphs,

        "full_text":
            full_text,
    }