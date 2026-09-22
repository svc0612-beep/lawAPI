# ============================================================
# 법령 Evidence → LLM 컨텍스트
#
# 역할
# - 특정 조문 Evidence 변환
# - 관련 법령 Evidence 변환
# ============================================================

from services.generation.context_utils import (
    normalize_text,
    make_article_label,
)


# ============================================================
# 1. 특정 조문 Evidence
# ============================================================

def build_article_context(
    article: dict
):

    if not isinstance(
        article,
        dict
    ):

        return ""

    lines = []

    law_name = normalize_text(
        article.get(
            "law_name"
        )
    )

    article_label = normalize_text(
        article.get(
            "article"
        )
    )

    article_title = normalize_text(
        article.get(
            "article_title"
        )
    )

    specific_paragraph = normalize_text(
        article.get(
            "specific_paragraph"
        )
    )

    full_article_text = normalize_text(
        article.get(
            "full_article_text"
        )
    )

    lines.append(
        "[공식 법령 근거]"
    )

    if law_name:

        lines.append(
            f"법령명: {law_name}"
        )

    if article_label:

        lines.append(
            f"조문: {article_label}"
        )

    if article_title:

        lines.append(
            f"조문 제목: {article_title}"
        )

    if specific_paragraph:

        lines.append(
            f"요청한 항: {specific_paragraph}"
        )

    if full_article_text:

        lines.append(
            "조문 전문:"
        )

        lines.append(
            full_article_text
        )

    return "\n".join(
        lines
    )


# ============================================================
# 2. 관련 법령 목록
# ============================================================

def build_laws_context(
    laws: list
):

    if not isinstance(
        laws,
        list
    ):

        return ""

    if not laws:

        return ""

    lines = [
        "[관련 법령]",
    ]

    for index, item in enumerate(
        laws,
        start=1
    ):

        if not isinstance(
            item,
            dict
        ):

            continue

        law_name = normalize_text(
            item.get(
                "law_name"
            )
        )

        article_label = make_article_label(

            item.get(
                "article_number"
            ),

            item.get(
                "sub_article_number"
            )
        )

        article_title = normalize_text(
            item.get(
                "article_title"
            )
        )

        article_text = normalize_text(
            item.get(
                "article_text"
            )
        )

        effective_date = normalize_text(
            item.get(
                "effective_date"
            )
        )

        relevance_score = item.get(
            "relevance_score"
        )

        lines.append(
            ""
        )

        lines.append(
            f"{index}. "
            f"{law_name}"
            + (
                f" {article_label}"
                if article_label
                else ""
            )
        )

        if article_title:

            lines.append(
                f"제목: {article_title}"
            )

        if effective_date:

            lines.append(
                f"시행일자: {effective_date}"
            )

        if relevance_score is not None:

            lines.append(
                f"검색 관련도 점수: "
                f"{relevance_score}"
            )

        if article_text:

            lines.append(
                "조문 내용:"
            )

            lines.append(
                article_text
            )

    return "\n".join(
        lines
    )