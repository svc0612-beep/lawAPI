# ============================================================
# 일반 법률 검색 결과 UI
# ============================================================

import streamlit as st

from services.generation.response_builder import (
    build_core_answer,
)

from services.ui.common import (
    clean_text,
    format_date,
    make_article_label,
)


# ============================================================
# 1. 검색 메타데이터
# ============================================================

def render_result_header(
    result: dict,
    current_question: str
):

    question_type = clean_text(
        result.get(
            "question_type"
        )
    )

    search_query = clean_text(
        result.get(
            "search_query"
        )
    )

    metadata = result.get(
        "metadata",
        {}
    ) or {}

    fallback_used = metadata.get(
        "fallback_used",
        False
    )

    with st.container(
        border=True
    ):

        st.markdown(
            f"### {current_question}"
        )

        meta_cols = st.columns(
            3
        )

        with meta_cols[0]:

            st.caption(
                "질문 유형"
            )

            st.write(
                question_type
                or "-"
            )

        with meta_cols[1]:

            st.caption(
                "검색어"
            )

            st.write(
                search_query
                or "-"
            )

        with meta_cols[2]:

            st.caption(
                "검색 방식"
            )

            if fallback_used:

                st.write(
                    "관련 법령 자동 탐색"
                )

            else:

                st.write(
                    "일반 검색"
                )


# ============================================================
# 2. Python 공식 답변
# ============================================================

def render_core_answer(
    result: dict
):

    core_answer = build_core_answer(
        result
    )

    with st.container(
        border=True
    ):

        st.markdown(
            "## 답변"
        )

        if core_answer:

            st.markdown(
                core_answer
            )

        else:

            st.write(
                "관련 공식 근거를 확인했습니다."
            )


# ============================================================
# 3. 법령 Tab
# ============================================================

def render_law_tab(
    article,
    laws
):

    if article:

        law_name = clean_text(
            article.get(
                "law_name"
            )
        )

        article_title = clean_text(
            article.get(
                "article_title"
            )
        )

        article_label = clean_text(
            article.get(
                "article"
            )
        )

        heading = " ".join(

            value

            for value in [

                law_name,

                article_label,

                article_title,

            ]

            if value
        )

        with st.expander(
            heading or "조문",
            expanded=True
        ):

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

            if specific_paragraph:

                st.text(
                    specific_paragraph
                )

            elif full_article_text:

                st.text(
                    full_article_text
                )

            else:

                st.caption(
                    "표시할 조문 내용이 없습니다."
                )

    for law in laws:

        law_name = clean_text(
            law.get(
                "law_name"
            )
        )

        article_number = law.get(
            "article_number"
        )

        sub_article_number = law.get(
            "sub_article_number",
            0
        )

        article_title = clean_text(
            law.get(
                "article_title"
            )
        )

        article_text = clean_text(
            law.get(
                "article_text"
            )
        )

        if article_number is not None:

            article_label = make_article_label(

                article_number,

                sub_article_number
            )

            heading = (
                f"{law_name} "
                f"{article_label}"
            )

            if article_title:

                heading += (
                    f" {article_title}"
                )

        else:

            heading = (
                law_name
                or
                "법령"
            )

        with st.expander(
            heading
        ):

            if law.get(
                "ministry"
            ):

                st.caption(
                    f"소관부처: {law.get('ministry')}"
                )

            if law.get(
                "effective_date"
            ):

                st.caption(
                    "시행일: "
                    + format_date(
                        law.get(
                            "effective_date"
                        )
                    )
                )

            if article_text:

                st.text(
                    article_text
                )

            else:

                st.caption(
                    "관련 법령이 검색되었습니다."
                )

    if not article and not laws:

        st.info(
            "표시할 법령 근거가 없습니다."
        )


# ============================================================
# 4. 판례 Tab
# ============================================================

def render_precedent_tab(precedents):
    if not precedents:
        st.info("이번 조회에서 판례를 확보하지 못했습니다. 판례가 없다는 뜻은 아닙니다.")
    for item in precedents:
        with st.expander(item.get("case_name") or item.get("case_number") or "판례 후보"):
            st.write("사건번호:", item.get("case_number", ""))
            st.write("법원:", item.get("court_name", ""))
            st.write("선고일:", item.get("decision_date", ""))
            if item.get("detail_verified"):
                st.write("판결요지 원문")
                st.text(item.get("summary") or "판결요지 미제공")
                st.write("판례 본문")
                st.text(item.get("full_text", ""))
            else:
                st.info("상세 원문 검증이 완료되지 않았습니다. 제목으로 판결 내용이나 선고형을 추정하지 않습니다.")
            if item.get("official_link"):
                st.link_button("국가법령정보센터 판례 원문", item["official_link"])


# ============================================================
# 5. 법령해석례 Tab
# ============================================================

def render_interpretation_tab(
    interpretations
):

    if not interpretations:

        st.info(
            "확인된 관련 법령해석례가 없습니다."
        )

    for item in interpretations:

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

        with st.expander(
            title
            or
            case_number
            or
            "법령해석례"
        ):

            if case_number:

                st.write(
                    f"**안건번호:** {case_number}"
                )

            if item.get(
                "agency"
            ):

                st.write(
                    f"**기관:** {item.get('agency')}"
                )

            if item.get(
                "reply_date"
            ):

                st.write(
                    "**회신일:** "
                    + format_date(
                        item.get(
                            "reply_date"
                        )
                    )
                )


# ============================================================
# 6. 국회도서관 Tab
# ============================================================

def render_library_tab(library_items):
    if not library_items:
        st.info("이번 조회에서 국회도서관 참고자료를 확보하지 못했습니다. 조회 오류 여부는 답변의 조회 제한 안내를 확인하세요.")
    for item in library_items:
        with st.expander(item.get("title") or "국회도서관 참고자료"):
            st.caption("서지·목차 참고자료이며 자료 본문과 법적 결론은 검증하지 않았습니다.")
            for key, label in [("author", "저자"), ("publisher", "발행기관"), ("publication_year", "발행연도")]:
                if item.get(key):
                    st.write(label + ":", item[key])
            for toc in item.get("toc_items", [])[:20]:
                st.text(toc)
            if item.get("official_link"):
                st.link_button("국회도서관 자료", item["official_link"])


# ============================================================
# 7. 일반 결과 전체
# ============================================================

def render_general_result(result: dict):
    render_core_answer(result)
    laws = result.get("verified_laws", [])
    precedents = result.get("precedents", []) or []
    library_items = result.get("library_items", []) or []
    interpretations = result.get("interpretations", []) or []
    tab_law, tab_case, tab_interpretation, tab_library = st.tabs([f"법령 원문 {len(laws)}", f"판례 후보 {len(precedents)}", f"해석례 검색 후보 {len(interpretations)}", f"국회도서관 참고자료 {len(library_items)}"])
    with tab_law:
        for item in laws:
            with st.expander(item.get("law_name", "") + " " + make_article_label(item.get("article_number"), item.get("sub_article_number", 0))):
                st.text(item.get("article_text", ""))
                if item.get("official_link"):
                    st.link_button("국가법령정보센터 원문", item["official_link"])
    with tab_case:
        render_precedent_tab(precedents)
    with tab_interpretation:
        st.caption("해석례 검색 후보입니다. 현재 사건에 대한 적용 여부는 확정하지 않았습니다.")
        render_interpretation_tab(interpretations)
    with tab_library:
        render_library_tab(library_items)
