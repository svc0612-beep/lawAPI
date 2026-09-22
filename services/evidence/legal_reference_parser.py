# ============================================================
# Legal Reference Parser
#
# 역할
# - 법령 조문 안에 등장하는 다른 조문 참조를 구조화한다.
#
# 지원 예:
#
# 제33조
# 제33조제5항
# 제33조제7항제1호
#
# 제22조의5
# 제22조의5제5항
# 제22조의5제5항제1호
#
# 같은 조 제5항
# 같은 조 제5항제1호
#
# 결과 예:
#
# {
#     "article_number": 22,
#     "sub_article_number": 5,
#     "paragraph_number": 5,
#     "item_number": 0,
#     "raw_text": "제22조의5제5항"
# }
#
# 중요:
# - 법적 의미를 판단하지 않는다.
# - 공식 조문 안에 적힌 참조 구조만 파싱한다.
# ============================================================

import re

from typing import (
    Any,
    Dict,
    List,
    Optional,
    Set,
)


# ============================================================
# 1. 문자열 정리
# ============================================================

def clean_text(
    value: Any
) -> str:

    if value is None:

        return ""


    text = str(
        value
    )


    text = re.sub(
        r"\s+",
        " ",
        text
    )


    return text.strip()


# ============================================================
# 2. 안전한 int
# ============================================================

def safe_int(
    value: Any,
    default: int = 0
) -> int:

    try:

        return int(
            value
        )

    except (
        TypeError,
        ValueError,
    ):

        return default


# ============================================================
# 3. 참조 객체 생성
# ============================================================

def build_reference(
    article_number: Any,
    sub_article_number: Any = 0,
    paragraph_number: Any = 0,
    item_number: Any = 0,
    raw_text: str = ""
) -> Dict[str, Any]:

    return {

        "article_number":
            safe_int(
                article_number
            ),

        "sub_article_number":
            safe_int(
                sub_article_number
            ),

        "paragraph_number":
            safe_int(
                paragraph_number
            ),

        "item_number":
            safe_int(
                item_number
            ),

        "raw_text":
            clean_text(
                raw_text
            ),
    }


# ============================================================
# 4. 명시적 조문 참조 추출
#
# 지원:
#
# 제33조
# 제33조제5항
# 제33조제7항제1호
#
# 제22조의5
# 제22조의5제5항
# 제22조의5제5항제1호
#
# 공백이 있어도 처리:
#
# 제22조의5 제5항
# 제22조의5 제5항 제1호
# ============================================================

def extract_explicit_references(
    text: str
) -> List[
    Dict[str, Any]
]:

    text = clean_text(
        text
    )


    if not text:

        return []


    pattern = re.compile(

        r"제\s*(\d+)\s*조"

        r"(?:\s*의\s*(\d+))?"

        r"(?:\s*제\s*(\d+)\s*항)?"

        r"(?:\s*제\s*(\d+)\s*호)?"
    )


    results = []


    for match in pattern.finditer(
        text
    ):

        article_number = (
            match.group(
                1
            )
        )


        sub_article_number = (
            match.group(
                2
            )
            or 0
        )


        paragraph_number = (
            match.group(
                3
            )
            or 0
        )


        item_number = (
            match.group(
                4
            )
            or 0
        )


        results.append(

            build_reference(

                article_number=(
                    article_number
                ),

                sub_article_number=(
                    sub_article_number
                ),

                paragraph_number=(
                    paragraph_number
                ),

                item_number=(
                    item_number
                ),

                raw_text=(
                    match.group(
                        0
                    )
                ),
            )
        )


    return results


# ============================================================
# 5. "같은 조" 참조
#
# 예:
#
# 제33조제5항 ...
# 같은 조 제6항 ...
#
# 현재 조문 번호를 알고 있을 때:
#
# 같은 조 제5항
# → article_number = 현재 조문
#
# own_sub_article_number도 전달 가능하다.
#
# 예:
# 현재 조문 = 제22조의5
# "같은 조 제3항"
# →
# article_number = 22
# sub_article_number = 5
# paragraph_number = 3
# ============================================================

def extract_same_article_references(
    text: str,
    own_article_number: Optional[int] = None,
    own_sub_article_number: Optional[int] = 0
) -> List[
    Dict[str, Any]
]:

    text = clean_text(
        text
    )


    if not text:

        return []


    if not own_article_number:

        return []


    pattern = re.compile(

        r"같은\s*조"

        r"(?:\s*제\s*(\d+)\s*항)?"

        r"(?:\s*제\s*(\d+)\s*호)?"
    )


    results = []


    for match in pattern.finditer(
        text
    ):

        paragraph_number = (
            match.group(
                1
            )
            or 0
        )


        item_number = (
            match.group(
                2
            )
            or 0
        )


        results.append(

            build_reference(

                article_number=(
                    own_article_number
                ),

                sub_article_number=(
                    own_sub_article_number
                    or 0
                ),

                paragraph_number=(
                    paragraph_number
                ),

                item_number=(
                    item_number
                ),

                raw_text=(
                    match.group(
                        0
                    )
                ),
            )
        )


    return results


# ============================================================
# 6. 중복 제거
# ============================================================

def deduplicate_references(
    references: List[
        Dict[str, Any]
    ]
) -> List[
    Dict[str, Any]
]:

    results = []

    seen = set()


    for reference in references:

        key = (

            reference.get(
                "article_number",
                0
            ),

            reference.get(
                "sub_article_number",
                0
            ),

            reference.get(
                "paragraph_number",
                0
            ),

            reference.get(
                "item_number",
                0
            ),
        )


        if key in seen:

            continue


        seen.add(
            key
        )


        results.append(
            reference
        )


    return results


# ============================================================
# 7. 자기 조문 헤더 제거
#
# 예:
#
# 제86조(과태료)
#
# 또는:
#
# 제22조의5(장애인 표준사업장...)
#
# 이것은 다른 조문에 대한 참조가 아니므로
# 첫 번째 자기 자신 단순 참조를 제거한다.
# ============================================================

def remove_self_header_reference(
    references: List[
        Dict[str, Any]
    ],
    own_article_number: Optional[int],
    own_sub_article_number: Optional[int] = 0
) -> List[
    Dict[str, Any]
]:

    if not own_article_number:

        return references


    own_article_number = safe_int(
        own_article_number
    )


    own_sub_article_number = safe_int(
        own_sub_article_number
    )


    results = []

    self_removed = False


    for reference in references:

        article_number = reference.get(
            "article_number",
            0
        )


        sub_article_number = reference.get(
            "sub_article_number",
            0
        )


        paragraph_number = reference.get(
            "paragraph_number",
            0
        )


        item_number = reference.get(
            "item_number",
            0
        )


        # ----------------------------------------------------
        # 조문 맨 앞의 자기 자신 헤더만 한 번 제거
        #
        # 제86조(...)
        # 제22조의5(...)
        # ----------------------------------------------------

        if (
            not self_removed
            and
            article_number
            ==
            own_article_number
            and
            sub_article_number
            ==
            own_sub_article_number
            and
            paragraph_number
            ==
            0
            and
            item_number
            ==
            0
        ):

            self_removed = True

            continue


        results.append(
            reference
        )


    return results


# ============================================================
# 8. 최종 참조 파서
# ============================================================

def extract_legal_references(
    text: str,
    own_article_number: Optional[int] = None,
    own_sub_article_number: Optional[int] = 0
) -> List[
    Dict[str, Any]
]:

    # ========================================================
    # 명시적 참조
    # ========================================================

    explicit = (
        extract_explicit_references(
            text
        )
    )


    # ========================================================
    # 같은 조 참조
    # ========================================================

    same_article = (
        extract_same_article_references(

            text=text,

            own_article_number=(
                own_article_number
            ),

            own_sub_article_number=(
                own_sub_article_number
            ),
        )
    )


    references = (
        explicit
        +
        same_article
    )


    # ========================================================
    # 자기 조문 헤더 제거
    # ========================================================

    references = (
        remove_self_header_reference(

            references=references,

            own_article_number=(
                own_article_number
            ),

            own_sub_article_number=(
                own_sub_article_number
            ),
        )
    )


    # ========================================================
    # 중복 제거
    # ========================================================

    references = (
        deduplicate_references(
            references
        )
    )


    return references


# ============================================================
# 9. 조문 번호만 필요한 경우
#
# 기존 코드 호환용.
#
# 예:
# 제22조의5
# 제22조
#
# 둘 다 article_number 기준으로는 22가 된다.
# ============================================================

def extract_reference_article_numbers(
    text: str,
    own_article_number: Optional[int] = None,
    own_sub_article_number: Optional[int] = 0
) -> Set[int]:

    references = extract_legal_references(

        text=text,

        own_article_number=(
            own_article_number
        ),

        own_sub_article_number=(
            own_sub_article_number
        ),
    )


    return {

        reference.get(
            "article_number"
        )

        for reference in references

        if reference.get(
            "article_number"
        )
    }


# ============================================================
# 10. 조 + 가지번호까지 필요한 경우
#
# 예:
#
# 제22조
# → (22, 0)
#
# 제22조의5
# → (22, 5)
# ============================================================

def extract_reference_article_keys(
    text: str,
    own_article_number: Optional[int] = None,
    own_sub_article_number: Optional[int] = 0
):

    references = extract_legal_references(

        text=text,

        own_article_number=(
            own_article_number
        ),

        own_sub_article_number=(
            own_sub_article_number
        ),
    )


    return {

        (
            reference.get(
                "article_number",
                0
            ),

            reference.get(
                "sub_article_number",
                0
            ),
        )

        for reference in references

        if reference.get(
            "article_number"
        )
    }