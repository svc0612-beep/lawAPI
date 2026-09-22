# ============================================================
# Article Response
#
# 역할:
# - "헌법 1조 1항"처럼 특정 조문 질문의 공식 조문 답변 생성
# ============================================================

from services.generation.response_utils import (
    clean_text,
)


def build_article_core_answer(
    article: dict
) -> str:

    if not isinstance(
        article,
        dict
    ):
        return ""

    law_name = clean_text(
        article.get(
            "law_name"
        )
    )

    article_label = clean_text(
        article.get(
            "article"
        )
    )

    specific_paragraph = clean_text(
        article.get(
            "specific_paragraph"
        )
    )

    full_article_text = clean_text(
        article.get(
            "full_article_text"
        )
    )

    lines = []

    if specific_paragraph:

        if law_name or article_label:

            lines.append(
                (
                    f"**{law_name} "
                    f"{article_label}에서 확인되는 내용입니다.**"
                ).strip()
            )

        lines.append(
            specific_paragraph
        )

        return "\n\n".join(
            lines
        )

    if full_article_text:

        if law_name or article_label:

            lines.append(
                (
                    f"**{law_name} "
                    f"{article_label}의 공식 조문입니다.**"
                ).strip()
            )

        lines.append(
            full_article_text
        )

    return "\n\n".join(
        lines
    )
