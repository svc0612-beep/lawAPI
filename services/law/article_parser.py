# ============================================================
# 법령 조문 JSON Parser
#
# 역할
#
# - 조문 목록 찾기
# - 전문 제외
# - 실제 조문 선택
# - 조 / 조의N 라벨 생성
# - 항 추출
# - 사용자 표시용 텍스트 생성
# ============================================================

from services.law.article_utils import (
    ensure_list,
)


# ============================================================
# 실제 조문 목록 찾기
# ============================================================

def find_article_items(
    data: dict
):

    if not isinstance(
        data,
        dict
    ):
        return []

    law = data.get(
        "법령"
    )

    if not isinstance(
        law,
        dict
    ):
        return []

    # ========================================================
    # 일반 구조
    #
    # 법령
    # └─ 조문
    #    └─ 조문단위
    # ========================================================

    article_container = law.get(
        "조문"
    )

    if isinstance(
        article_container,
        dict
    ):

        article_items = (
            article_container.get(
                "조문단위"
            )
        )

        result = ensure_list(
            article_items
        )

        if result:
            return result

    # ========================================================
    # 조문단위가 법령 바로 아래 존재하는 경우
    # ========================================================

    direct_items = law.get(
        "조문단위"
    )

    return ensure_list(
        direct_items
    )


# ============================================================
# 조문 JSON → 표시용 구조
# ============================================================

def extract_article_text(
    article_data: dict
):

    if not isinstance(
        article_data,
        dict
    ):

        return {

            "law_name":
                None,

            "article":
                None,

            "title":
                None,

            "paragraphs":
                [],

            "text":
                "",
        }

    law = article_data.get(
        "법령",
        {}
    )

    if not isinstance(
        law,
        dict
    ):

        law = {}

    # ========================================================
    # 1. 법령명
    # ========================================================

    basic_info = law.get(
        "기본정보",
        {}
    )

    law_name = None

    if isinstance(
        basic_info,
        dict
    ):

        law_name = (

            basic_info.get(
                "법령명_한글"
            )

            or

            basic_info.get(
                "법령명한글"
            )

            or

            basic_info.get(
                "법령명"
            )
        )

    # ========================================================
    # 2. 조문 목록
    # ========================================================

    article_items = find_article_items(
        article_data
    )

    selected_article = None

    for item in article_items:

        if not isinstance(
            item,
            dict
        ):
            continue

        # ====================================================
        # "전문" 구조정보 제외
        # ====================================================

        article_type = str(
            item.get(
                "조문여부",
                ""
            )
        ).strip()

        if article_type == "전문":
            continue

        selected_article = item

        break

    if selected_article is None:

        return {

            "law_name":
                law_name,

            "article":
                None,

            "title":
                None,

            "paragraphs":
                [],

            "text":
                "",
        }

    # ========================================================
    # 3. 조문 기본정보
    # ========================================================

    article_number_text = (
        selected_article.get(
            "조문번호"
        )
    )

    article_sub_number = (
        selected_article.get(
            "조문가지번호"
        )
    )

    article_title = (
        selected_article.get(
            "조문제목"
        )
        or
        ""
    )

    article_content = (
        selected_article.get(
            "조문내용"
        )
        or
        ""
    )

    # ========================================================
    # 4. 제10조 / 제10조의2
    # ========================================================

    article_label = None

    if article_number_text:

        article_label = (
            f"제{article_number_text}조"
        )

        try:

            sub_number_int = int(
                article_sub_number
                or 0
            )

        except (
            ValueError,
            TypeError
        ):

            sub_number_int = 0

        if sub_number_int:

            article_label += (
                f"의{sub_number_int}"
            )

    # ========================================================
    # 5. 항
    # ========================================================

    paragraphs = []

    paragraph_items = ensure_list(
        selected_article.get(
            "항"
        )
    )

    for paragraph in paragraph_items:

        if not isinstance(
            paragraph,
            dict
        ):
            continue

        paragraph_text = (
            paragraph.get(
                "항내용"
            )
            or
            ""
        )

        paragraph_text = str(
            paragraph_text
        ).strip()

        if paragraph_text:

            paragraphs.append(
                paragraph_text
            )

    # ========================================================
    # 6. 최종 텍스트
    # ========================================================

    lines = []

    if law_name:

        lines.append(
            str(
                law_name
            ).strip()
        )

    if law_name:

        lines.append(
            ""
        )

    if article_content:

        lines.append(
            str(
                article_content
            ).strip()
        )

    # ========================================================
    # 조문내용에 항 내용이 이미 포함되어 있다면
    # 중복해서 추가하지 않는다.
    # ========================================================

    base_text = "\n".join(
        lines
    )

    for paragraph_text in paragraphs:

        if paragraph_text not in base_text:

            lines.append(
                paragraph_text
            )

    final_text = "\n".join(
        lines
    ).strip()

    return {

        "law_name":
            law_name,

        "article":
            article_label,

        "title":
            article_title,

        "paragraphs":
            paragraphs,

        "text":
            final_text,
    }