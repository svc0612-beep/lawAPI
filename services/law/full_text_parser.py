# ============================================================
# 법령 전체 JSON 파서
# ============================================================

from typing import (
    Any,
    Dict,
    List,
)

from services.law.full_text_utils import (
    normalize_text,
    ensure_list,
)

from services.law.full_article_parser import (
    parse_article_node,
)


# ============================================================
# 법령 루트
# ============================================================

def get_law_root(
    raw_data: Dict[str, Any]
) -> Dict[str, Any]:

    law_root = raw_data.get(
        "법령"
    )

    if isinstance(
        law_root,
        dict
    ):

        return law_root

    return {}


# ============================================================
# 기본정보
# ============================================================

def get_basic_info(
    law_root: Dict[str, Any]
) -> Dict[str, Any]:

    basic = law_root.get(
        "기본정보"
    )

    if isinstance(
        basic,
        dict
    ):

        return basic

    return {}


# ============================================================
# 전체 조문
#
# 전문 = 구조정보
# 조문 = 실제 법령 조문
# ============================================================

def parse_articles(
    law_root: Dict[str, Any]
) -> Dict[str, Any]:

    articles = []

    structural_headers = []

    jo_root = law_root.get(
        "조문"
    )

    if not isinstance(
        jo_root,
        dict
    ):

        return {

            "articles":
                [],

            "structure":
                [],
        }

    nodes = ensure_list(
        jo_root.get(
            "조문단위"
        )
    )

    current_headers = []

    for node in nodes:

        if not isinstance(
            node,
            dict
        ):
            continue

        article_type = normalize_text(
            node.get(
                "조문여부"
            )
        )

        content = normalize_text(
            node.get(
                "조문내용"
            )
        )

        # ====================================================
        # 장 / 절 / 관 등의 구조 정보
        # ====================================================

        if article_type == "전문":

            if content:

                structural_headers.append(
                    content
                )

                # 기존 코드와 동일:
                # 가장 최근 전문 1개를 다음 조문에 연결
                current_headers = [
                    content
                ]

            continue

        # ====================================================
        # 실제 조문만 처리
        # ====================================================

        if article_type != "조문":
            continue

        article = parse_article_node(
            node=node,
            section_headers=current_headers
        )

        if article.get(
            "article_number"
        ) is None:

            continue

        articles.append(
            article
        )

    return {

        "articles":
            articles,

        "structure":
            structural_headers,
    }


# ============================================================
# 중복 조문 제거
# ============================================================

def deduplicate_articles(
    articles: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:

    final_articles = []

    seen = set()

    for article in articles:

        key = (

            article.get(
                "article_number"
            ),

            article.get(
                "sub_article_number",
                0
            ),

            article.get(
                "article_key",
                ""
            ),
        )

        if key in seen:
            continue

        seen.add(
            key
        )

        final_articles.append(
            article
        )

    return final_articles


# ============================================================
# 메타데이터
# ============================================================

def extract_metadata(
    law_root: Dict[str, Any]
) -> Dict[str, Any]:

    basic = get_basic_info(
        law_root
    )

    def get_value(
        *keys
    ):

        for key in keys:

            value = basic.get(
                key
            )

            if isinstance(value, dict):
                value = value.get("content", value.get("#text", ""))

            if value not in (
                None,
                ""
            ):

                return normalize_text(
                    value
                )

        for key in keys:

            value = law_root.get(
                key
            )

            if isinstance(value, dict):
                value = value.get("content", value.get("#text", ""))

            if value not in (
                None,
                ""
            ):

                return normalize_text(
                    value
                )

        return ""

    return {

        "law_name":
            get_value(
                "법령명_한글",
                "법령명한글",
                "법령명"
            ),

        "law_type":
            get_value(
                "법종구분",
                "법령구분명"
            ),

        "ministry":
            get_value(
                "소관부처명",
                "소관부처"
            ),

        "law_id":
            get_value(
                "법령ID"
            ),

        "mst":
            get_value(
                "법령일련번호",
                "MST"
            ),

        "effective_date":
            get_value(
                "시행일자"
            ),

        "promulgation_date":
            get_value(
                "공포일자"
            ),

        "revision_type":
            get_value(
                "제개정구분명",
                "제개정구분"
            ),
    }


# ============================================================
# 전체 JSON → 정규화 결과
# ============================================================

def parse_full_law(
    raw_data: Dict[str, Any]
) -> Dict[str, Any]:

    law_root = get_law_root(
        raw_data
    )

    metadata = extract_metadata(
        law_root
    )

    parsed = parse_articles(
        law_root
    )

    articles = deduplicate_articles(
        parsed.get(
            "articles",
            []
        )
    )

    return {

        **metadata,

        "article_count":
            len(
                articles
            ),

        "structure":
            parsed.get(
                "structure",
                []
            ),

        "articles":
            articles,
    }
