# ============================================================
# 법률 Evidence 출처 표시
#
# 역할
# - 특정 조문
# - 관련 법령
# - 판례
# - 법령해석례
# - 국회도서관
# ============================================================

from services.generation.response_utils import (
    clean_text,
    format_date,
    make_article_label,
)


# ============================================================
# 1. 특정 조문 출처
# ============================================================

def build_article_source(
    article: dict
):

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

    title = clean_text(
        article.get(
            "article_title"
        )
    )

    effective_date = format_date(
        article.get(
            "effective_date"
        )
    )

    label = " ".join(

        value

        for value in [

            law_name,
            article_label,

        ]

        if value
    )

    lines = []

    if label:

        lines.append(
            f"- {label}"
        )

    if title:

        lines.append(
            f"  제목: {title}"
        )

    if effective_date:

        lines.append(
            f"  시행일자: {effective_date}"
        )

    return "\n".join(
        lines
    )


# ============================================================
# 2. 관련 법령 출처
# ============================================================

def build_law_sources(
    laws: list
):

    if not isinstance(
        laws,
        list
    ) or not laws:

        return ""

    lines = [

        "[근거 법령]",
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

        law_name = clean_text(
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

        title = clean_text(
            item.get(
                "article_title"
            )
        )

        effective_date = format_date(
            item.get(
                "effective_date"
            )
        )

        label = " ".join(

            value

            for value in [

                law_name,
                article_label,

            ]

            if value
        )

        lines.append(
            f"{index}. {label}"
        )

        if title:

            lines.append(
                f"   제목: {title}"
            )

        if effective_date:

            lines.append(
                f"   시행일자: {effective_date}"
            )

    return "\n".join(
        lines
    )


# ============================================================
# 3. 판례 출처
# ============================================================

def build_precedent_sources(
    precedents: list
):

    if not isinstance(
        precedents,
        list
    ) or not precedents:

        return ""

    lines = [

        "[관련 판례]",
    ]

    for index, item in enumerate(
        precedents,
        start=1
    ):

        if not isinstance(
            item,
            dict
        ):

            continue

        case_name = clean_text(
            item.get(
                "case_name"
            )
        )

        case_number = clean_text(
            item.get(
                "case_number"
            )
        )

        court_name = clean_text(
            item.get(
                "court_name"
            )
        )

        decision_date = clean_text(
            item.get(
                "decision_date"
            )
        )

        lines.append(
            f"{index}. {case_name}"
        )

        if case_number:

            lines.append(
                f"   사건번호: {case_number}"
            )

        if court_name:

            lines.append(
                f"   법원: {court_name}"
            )

        if decision_date:

            lines.append(
                f"   선고일자: {decision_date}"
            )

    return "\n".join(
        lines
    )


# ============================================================
# 4. 법령해석례 출처
# ============================================================

def build_interpretation_sources(
    interpretations: list
):

    if not isinstance(
        interpretations,
        list
    ) or not interpretations:

        return ""

    lines = [

        "[법령해석례]",
    ]

    for index, item in enumerate(
        interpretations,
        start=1
    ):

        if not isinstance(
            item,
            dict
        ):

            continue

        title = clean_text(
            item.get(
                "title"
            )
        )

        case_number = clean_text(
            item.get(
                "case_number"
            )
        )

        reply_date = clean_text(
            item.get(
                "reply_date"
            )
        )

        agency = clean_text(
            item.get(
                "agency"
            )
        )

        lines.append(
            f"{index}. {title}"
        )

        if case_number:

            lines.append(
                f"   안건번호: {case_number}"
            )

        if reply_date:

            lines.append(
                f"   회신일자: {reply_date}"
            )

        if agency:

            lines.append(
                f"   기관: {agency}"
            )

    return "\n".join(
        lines
    )


# ============================================================
# 5. 국회도서관 출처
# ============================================================

def build_library_sources(items: list):
    if not items:
        return ""
    lines = ["[국회도서관 참고자료]", "서지정보입니다. 자료 본문이나 법적 결론을 확인한 근거로 사용하지 않습니다."]
    for item in items:
        lines.append(" · ".join(str(item.get(k) or "") for k in ("title", "author", "publisher", "publication_year")))
        if item.get("official_link"):
            lines.append("[국회도서관 자료](" + item["official_link"] + ")")
    return "\n\n".join(lines)


# ============================================================
# 6. 모든 출처 조립
# ============================================================

def build_source_sections(
    evidence_result: dict
):

    sections = []

    article = evidence_result.get(
        "article"
    )

    if article:

        article_source = build_article_source(
            article
        )

        if article_source:

            sections.append(

                "\n".join(
                    [

                        "[근거 법령]",

                        article_source,
                    ]
                )
            )

    laws = build_law_sources(

        evidence_result.get(
            "laws",
            []
        )
    )

    if laws:

        sections.append(
            laws
        )

    interpretations = (
        build_interpretation_sources(

            evidence_result.get(
                "interpretations",
                []
            )
        )
    )

    if interpretations:

        sections.append(
            interpretations
        )

    precedents = build_precedent_sources(

        evidence_result.get(
            "precedents",
            []
        )
    )

    if precedents:

        sections.append(
            precedents
        )

    library = build_library_sources(

        evidence_result.get(
            "library_items",
            []
        )
    )

    if library:

        sections.append(
            library
        )

    return "\n\n".join(
        sections
    )