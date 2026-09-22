# ============================================================
# 국회도서관 Evidence → LLM 컨텍스트
# ============================================================

from services.generation.context_utils import (
    normalize_text,
    has_text,
)


def build_library_context(
    library_items: list,
    toc_limit: int = 20
):

    if not isinstance(
        library_items,
        list
    ):

        return ""

    if not library_items:

        return ""

    lines = [
        "[국회도서관 참고자료]",
    ]

    for index, item in enumerate(
        library_items,
        start=1
    ):

        if not isinstance(
            item,
            dict
        ):

            continue

        title = normalize_text(
            item.get(
                "title"
            )
        )

        author = normalize_text(
            item.get(
                "author"
            )
        )

        publisher = normalize_text(
            item.get(
                "publisher"
            )
        )

        publication_year = normalize_text(
            item.get(
                "publication_year"
            )
        )

        control_no = normalize_text(
            item.get(
                "control_no"
            )
        )

        keywords = item.get(
            "keywords",
            []
        )

        toc_items = item.get(
            "toc_items",
            []
        )

        lines.append(
            ""
        )

        lines.append(
            f"{index}. {title}"
        )

        if control_no:

            lines.append(
                f"제어번호: {control_no}"
            )

        if author:

            lines.append(
                f"저자: {author}"
            )

        if publisher:

            lines.append(
                f"발행자: {publisher}"
            )

        if publication_year:

            lines.append(
                f"발행년도: "
                f"{publication_year}"
            )

        if (
            isinstance(
                keywords,
                list
            )
            and keywords
        ):

            clean_keywords = [

                normalize_text(
                    keyword
                )

                for keyword in keywords

                if has_text(
                    keyword
                )
            ]

            if clean_keywords:

                lines.append(
                    "키워드: "
                    + ", ".join(
                        clean_keywords
                    )
                )

        if (
            isinstance(
                toc_items,
                list
            )
            and toc_items
        ):

            lines.append(
                "주요 목차:"
            )

            for toc_item in toc_items[
                :toc_limit
            ]:

                toc_text = normalize_text(
                    toc_item
                )

                if toc_text:

                    lines.append(
                        f"- {toc_text}"
                    )

    return "\n".join(
        lines
    )