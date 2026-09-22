# ============================================================
# 법령 전체조회 UI
# ============================================================

import math

import streamlit as st

from services.ui.common import (
    clean_text,
    format_date,
    make_article_label,
    contains_keyword,
)


PAGE_SIZE = 50


def render_full_law_view(
    result: dict
):

    status = result.get(
        "status",
        ""
    )

    full_law = result.get(
        "full_law"
    ) or {}

    # Optional sources (for example, the National Assembly Library) may fail
    # after the official statute text has already been verified.  In that
    # case the aggregate result is ``partial`` but the full law is still safe
    # and useful to render.  Gate this view on the full-law payload itself,
    # not on unrelated source status.
    full_law_verified = result.get("metadata", {}).get("full_law_verified")

    if (
        not full_law
        or
        full_law.get("status") != "success"
        or
        full_law_verified is False
    ):

        st.warning(
            result.get(
                "message",
                "법령 전체 원문을 찾지 못했습니다."
            )
        )

        return

    law_name = clean_text(
        full_law.get(
            "law_name"
        )
    )

    law_type = clean_text(
        full_law.get(
            "law_type"
        )
    )

    ministry = clean_text(
        full_law.get(
            "ministry"
        )
    )

    effective_date = format_date(
        full_law.get(
            "effective_date"
        )
    )

    article_count = int(
        full_law.get(
            "article_count",
            0
        )
        or 0
    )

    articles = full_law.get(
        "articles",
        []
    ) or []

    st.markdown(
        "## 법령 전문"
    )

    metric_cols = st.columns(
        4
    )

    metric_cols[0].metric(
        "법령명",
        law_name or "-"
    )

    metric_cols[1].metric(
        "법령 구분",
        law_type or "-"
    )

    metric_cols[2].metric(
        "시행일",
        effective_date
    )

    metric_cols[3].metric(
        "조문 수",
        f"{article_count:,}"
    )

    if ministry:

        st.caption(
            f"소관부처: {ministry}"
        )

    st.divider()

    # ========================================================
    # 조문 내 검색
    # ========================================================

    article_keyword = st.text_input(

        "조문 내 검색",

        placeholder=(
            "예: 손해배상, 장애인, 계약, 특허권"
        ),

        key="full_law_article_search",
    )

    if article_keyword:

        filtered_articles = [

            article

            for article in articles

            if contains_keyword(
                article,
                article_keyword
            )
        ]

    else:

        filtered_articles = articles

    st.caption(
        f"검색 결과 {len(filtered_articles):,}개 조문"
    )

    if not filtered_articles:

        st.info(
            "해당 검색어가 포함된 조문을 찾지 못했습니다."
        )

        return

    # ========================================================
    # Pagination
    # ========================================================

    total_pages = max(

        1,

        math.ceil(
            len(
                filtered_articles
            )
            /
            PAGE_SIZE
        )
    )

    if total_pages > 1:

        page = st.selectbox(

            "페이지",

            options=list(
                range(
                    1,
                    total_pages + 1
                )
            ),

            format_func=lambda value: (
                f"{value} / {total_pages}"
            ),

            key="full_law_page",
        )

    else:

        page = 1

    start_index = (
        page - 1
    ) * PAGE_SIZE

    end_index = min(

        start_index
        + PAGE_SIZE,

        len(
            filtered_articles
        )
    )

    page_articles = filtered_articles[
        start_index:end_index
    ]

    st.caption(
        (
            f"{start_index + 1:,}"
            f" ~ "
            f"{end_index:,}"
            f"번째 조문 표시"
        )
    )

    # ========================================================
    # 조문 출력
    # ========================================================

    for article in page_articles:

        article_number = article.get(
            "article_number"
        )

        sub_article_number = article.get(
            "sub_article_number",
            0
        )

        article_title = clean_text(
            article.get(
                "article_title"
            )
        )

        article_label = make_article_label(

            article_number,

            sub_article_number
        )

        expander_title = article_label

        if article_title:

            expander_title += (
                f"  {article_title}"
            )

        with st.expander(
            expander_title
        ):

            section_headers = article.get(
                "section_headers",
                []
            ) or []

            if section_headers:

                st.caption(
                    " > ".join(
                        section_headers
                    )
                )

            article_text = clean_text(
                article.get(
                    "full_text"
                )
            )

            if article_text:

                st.text(
                    article_text
                )

            else:

                st.caption(
                    "표시할 조문 내용이 없습니다."
                )

    st.divider()

    st.caption(
        (
            "법령 원문은 공식 법령정보를 기준으로 표시합니다. "
            "법률 적용 여부는 구체적인 사실관계에 따라 달라질 수 있습니다."
        )
    )
