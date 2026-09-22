# ============================================================
# query_service 회귀 테스트
#
# 역할
# - services/query_service.py의 기능 확인
# - 출력 전용
# - 실제 서비스 로직은 포함하지 않음
# ============================================================

import os
import sys


# ============================================================
# 1. 프로젝트 루트 등록
# ============================================================

CURRENT_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

PROJECT_ROOT = os.path.dirname(
    CURRENT_DIR
)

if PROJECT_ROOT not in sys.path:

    sys.path.append(
        PROJECT_ROOT
    )


# ============================================================
# 2. 통합 서비스
# ============================================================

from services.query_service import (
    process_law_question,
)


# ============================================================
# 3. 특정 조문 출력
# ============================================================

def print_article_result(
    result: dict
):

    article = result.get(
        "article"
    )


    print()

    print(
        "-" * 80
    )

    print(
        "공식 법령 근거"
    )

    print(
        "-" * 80
    )


    if not article:

        print(
            "확인된 조문이 없습니다."
        )

        return


    print(
        article.get(
            "full_article_text"
        )
    )


    paragraph_number = article.get(
        "paragraph_number"
    )


    specific_paragraph = article.get(
        "specific_paragraph"
    )


    if (
        paragraph_number is not None
        and
        specific_paragraph
    ):

        print()

        print(
            f"요청한 {paragraph_number}항:"
        )

        print(
            specific_paragraph
        )


# ============================================================
# 4. 관련 법령 출력
# ============================================================

def print_laws(
    result: dict
):

    laws = result.get(
        "laws",
        []
    )


    print()

    print(
        "-" * 80
    )

    print(
        "관련 법령"
    )

    print(
        "-" * 80
    )


    if not laws:

        print(
            "확인된 관련 법령이 없습니다."
        )

        return


    for item in laws:

        article_number = item.get(
            "article_number"
        )


        sub_number = (
            item.get(
                "sub_article_number"
            )
            or 0
        )


        if article_number is None:

            article_label = (
                "조문 정보 없음"
            )


        elif sub_number:

            article_label = (
                f"제{article_number}조의{sub_number}"
            )


        else:

            article_label = (
                f"제{article_number}조"
            )


        print()


        print(
            f"[{item.get('final_rank')}] "
            f"{item.get('law_name')}"
        )


        print(
            "조문:",
            article_label
        )


        print(
            "제목:",
            item.get(
                "article_title"
            )
        )


        print(
            "관련도:",
            item.get(
                "relevance_score"
            )
        )


# ============================================================
# 5. 판례 출력
# ============================================================

def print_precedents(
    result: dict
):

    precedents = result.get(
        "precedents",
        []
    )


    print()

    print(
        "-" * 80
    )

    print(
        "관련 판례"
    )

    print(
        "-" * 80
    )


    if not precedents:

        print(
            "확인된 관련 판례가 없습니다."
        )

        return


    for item in precedents:

        print()


        print(
            f"[{item.get('rank')}] "
            f"{item.get('case_name')}"
        )


        print(
            "사건번호:",
            item.get(
                "case_number"
            )
        )


        print(
            "법원:",
            item.get(
                "court_name"
            )
        )


        print(
            "선고일자:",
            item.get(
                "decision_date"
            )
        )


# ============================================================
# 6. 법령해석례 출력
# ============================================================

def print_interpretations(
    result: dict
):

    interpretations = result.get(
        "interpretations",
        []
    )


    print()

    print(
        "-" * 80
    )

    print(
        "법령해석례"
    )

    print(
        "-" * 80
    )


    if not interpretations:

        print(
            "확인된 법령해석례가 없습니다."
        )

        return


    for item in interpretations:

        print()


        print(
            f"[{item.get('rank')}] "
            f"{item.get('title')}"
        )


        print(
            "안건번호:",
            item.get(
                "case_number"
            )
        )


        print(
            "회신일자:",
            item.get(
                "reply_date"
            )
        )


# ============================================================
# 7. 국회도서관 출력
# ============================================================

def print_library_items(
    result: dict
):

    items = result.get(
        "library_items",
        []
    )


    print()

    print(
        "-" * 80
    )

    print(
        "국회도서관 자료"
    )

    print(
        "-" * 80
    )


    if not items:

        print(
            "연결된 국회도서관 자료가 없습니다."
        )

        return


    for index, item in enumerate(
        items,
        start=1
    ):

        print()


        print(
            f"[{index}] "
            f"{item.get('title')}"
        )


        print(
            "제어번호:",
            item.get(
                "control_no"
            )
        )


        print(
            "저자:",
            item.get(
                "author"
            )
        )


        print(
            "발행자:",
            item.get(
                "publisher"
            )
        )


        print(
            "발행년도:",
            item.get(
                "publication_year"
            )
        )


        print(
            "목차 항목 수:",
            len(
                item.get(
                    "toc_items",
                    []
                )
            )
        )


# ============================================================
# 8. 전체 결과 출력
# ============================================================

def print_result(
    result: dict
):

    print()

    print(
        "상태:",
        result.get(
            "status"
        )
    )


    print(
        "질문 유형:",
        result.get(
            "question_type"
        )
    )


    print(
        "원 질문:",
        result.get(
            "original_question"
        )
    )


    print(
        "검색어:",
        result.get(
            "search_query"
        )
    )


    print(
        "근거 존재:",
        result.get(
            "evidence_found"
        )
    )


    question_type = result.get(
        "question_type"
    )


    if question_type == "특정_조문조회":

        print_article_result(
            result
        )


    elif question_type == "관련_법령탐색":

        print_laws(
            result
        )

        print_precedents(
            result
        )

        print_interpretations(
            result
        )


    if result.get(
        "library_items"
    ):

        print_library_items(
            result
        )


# ============================================================
# 9. 테스트 실행
# ============================================================

if __name__ == "__main__":

    print()

    print(
        "=" * 80
    )

    print(
        "query_service 회귀 테스트"
    )

    print(
        "=" * 80
    )


    # ========================================================
    # 테스트 1
    # ========================================================

    test_questions = [

        "헌법 1조 1항 뭐야?",

        "장애인 취업 관련 법 알려줘",

        "특허 침해하면 어떻게 돼?",
    ]


    for question in test_questions:

        print()
        print()


        print(
            "=" * 80
        )


        print(
            "사용자 질문:",
            question
        )


        print(
            "=" * 80
        )


        try:

            result = process_law_question(
                question
            )


            print_result(
                result
            )


        except Exception as e:

            print()

            print(
                "오류:",
                e
            )


    # ========================================================
    # 테스트 2
    # 국회도서관 통합
    # ========================================================

    print()
    print()


    print(
        "=" * 80
    )


    print(
        "국회도서관 Evidence 통합 테스트"
    )


    print(
        "=" * 80
    )


    question = (
        "국가기반시설 관련 법 알려줘"
    )


    print(
        "사용자 질문:",
        question
    )


    try:

        result = process_law_question(

            question=question,

            control_numbers=[
                "MONO1201027232"
            ]
        )


        print_result(
            result
        )


        print()

        print(
            "국회도서관 자료 개수:",
            len(
                result.get(
                    "library_items",
                    []
                )
            )
        )


    except Exception as e:

        print()

        print(
            "오류:",
            e
        )