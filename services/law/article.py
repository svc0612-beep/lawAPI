# ============================================================
# 법령 조문 조회 서비스
#
# 역할
#
# 법령명
#   ↓
# 정확한 공식 법령 검색
#   ↓
# MST 확보
#   ↓
# 특정 JO 조회
#   ↓
# 조문 JSON 반환
#
# 세부 HTTP / Parser / Utility 로직은
# 각각 별도 모듈에서 담당한다.
# ============================================================

from services.law.search import (
    find_exact_law,
)


# ============================================================
# 기존 외부 import 호환성을 위해 재노출
# ============================================================

from services.law.article_utils import (
    make_jo_code,
    ensure_list,
)

from services.law.article_fetcher import (
    get_law_article,
)

from services.law.article_parser import (
    find_article_items,
    extract_article_text,
)


# ============================================================
# 법령명 + 조문번호 조회
# ============================================================

def search_law_article(
    law_name: str,
    article_number: int,
    sub_article_number: int = 0
):

    """
    예:

    search_law_article(
        law_name="대한민국헌법",
        article_number=1
    )
    """

    # ========================================================
    # 1. 법령명 → 공식 법령 정보
    # ========================================================

    law_info = find_exact_law(
        law_name
    )

    if law_info is None:

        raise RuntimeError(
            f"법령을 찾을 수 없습니다: {law_name}"
        )

    # ========================================================
    # 2. MST
    # ========================================================

    mst = (

        law_info.get(
            "법령일련번호"
        )

        or

        law_info.get(
            "MST"
        )
    )

    if not mst:

        raise RuntimeError(
            f"{law_name}의 MST를 찾을 수 없습니다."
        )

    # ========================================================
    # 3. 특정 조문 조회
    # ========================================================

    article_data = get_law_article(

        mst=mst,

        article_number=article_number,

        sub_article_number=(
            sub_article_number
        )
    )

    return {

        "law_info":
            law_info,

        "article_data":
            article_data,
    }


# ============================================================
# 단독 테스트
# ============================================================

if __name__ == "__main__":

    test_law_name = (
        "대한민국헌법"
    )

    test_article_number = 1

    print()

    print(
        "=" * 70
    )

    print(
        "법령 조문 조회 서비스 테스트"
    )

    print(
        "=" * 70
    )

    print(
        "법령:",
        test_law_name
    )

    print(
        "조문:",
        f"제{test_article_number}조"
    )

    try:

        result = search_law_article(

            law_name=test_law_name,

            article_number=(
                test_article_number
            )
        )

        clean_article = extract_article_text(
            result[
                "article_data"
            ]
        )

        print()

        print(
            "-" * 70
        )

        print(
            "조회 결과"
        )

        print(
            "-" * 70
        )

        print(
            clean_article[
                "text"
            ]
        )

        print()

        print(
            "조문:",
            clean_article[
                "article"
            ]
        )

        print(
            "조문 제목:",
            clean_article[
                "title"
            ]
        )

        print(
            "항 개수:",
            len(
                clean_article[
                    "paragraphs"
                ]
            )
        )

        for index, paragraph in enumerate(

            clean_article[
                "paragraphs"
            ],

            start=1
        ):

            print(
                f"{index}항:",
                paragraph
            )

    except Exception as e:

        print()

        print(
            "오류:",
            e
        )