# ============================================================
# Conclusion Text Utils
#
# legal_conclusion_builder.py에서 분리한 순수 텍스트 유틸.
# 법률 판단/분류 로직은 포함하지 않는다.
# ============================================================

import re

from typing import (
    Any,
    List,
    Tuple,
)

def clean_text(
    value: Any
) -> str:

    if value is None:

        return ""


    return re.sub(

        r"\s+",

        " ",

        str(
            value
        ),
    ).strip()


def remove_revision_note(
    text: str
) -> str:

    text = clean_text(
        text
    )


    text = re.sub(

        r"\s*<[^>]*(?:개정|신설|전문개정|삭제)[^>]*>\s*",

        "",

        text,
    )


    return clean_text(
        text
    )


def remove_paragraph_marker(
    text: str
) -> str:

    return re.sub(

        r"^[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳]\s*",

        "",

        clean_text(
            text
        ),
    ).strip()


def normalize_statement(
    text: str
) -> str:

    text = remove_revision_note(
        text
    )


    text = remove_paragraph_marker(
        text
    )


    return clean_text(
        text
    )


def remove_parenthetical_details(
    text: str
) -> str:

    text = clean_text(
        text
    )


    previous = None


    while (
        previous != text
    ):

        previous = text


        text = re.sub(
            r"\([^()]*\)",
            "",
            text
        )


    return clean_text(
        text
    )


def ensure_sentence_end(
    text: str
) -> str:

    text = clean_text(
        text
    )


    if not text:

        return ""


    if text.endswith(
        (
            ".",
            "다.",
            "요.",
        )
    ):

        return text


    return (
        text
        +
        "."
    )


def extract_numeric_conditions(
    text: str
) -> List[str]:

    text = clean_text(
        text
    )


    if not text:

        return []


    patterns = [

        r"상시\s*\d+\s*명(?:의\s*근로자를\s*고용하는\s*사업주)?\s*이상",

        r"상시\s*\d+\s*명\s*미만",

        r"\d+\s*명\s*이상",

        r"\d+\s*명\s*미만",

        r"\d+\s*일\s*이내",

        r"\d+\s*개월\s*이내",

        r"\d+\s*년\s*이내",
    ]


    matches: List[
        Tuple[
            int,
            int,
            str,
        ]
    ] = []


    for pattern in patterns:

        for match in re.finditer(
            pattern,
            text
        ):

            value = clean_text(
                match.group(
                    0
                )
            )


            matches.append(
                (
                    match.start(),
                    match.end(),
                    value,
                )
            )


    # 긴 범위 우선
    matches.sort(

        key=lambda item: (

            item[0],

            -(
                item[1]
                -
                item[0]
            ),
        )
    )


    selected = []


    selected_ranges = []


    for start, end, value in matches:

        overlap = False


        for selected_start, selected_end in selected_ranges:

            if (
                start >= selected_start
                and
                end <= selected_end
            ):

                overlap = True

                break


        if overlap:

            continue


        if value not in selected:

            selected.append(
                value
            )


            selected_ranges.append(
                (
                    start,
                    end,
                )
            )


    return selected


def extract_exclusion_clause(
    text: str
) -> str:

    text = clean_text(
        text
    )


    if not text:

        return ""


    parentheses = re.findall(
        r"\(([^()]*)\)",
        text
    )


    for value in parentheses:

        value = clean_text(
            value
        )


        if any(

            term in value

            for term in (

                "제외한다",

                "제외된다",

                "적용하지 아니한다",

                "적용하지 않는다",

                "면제",
            )
        ):

            return value


    match = re.search(

        r"([^.!?]*(?:제외한다|제외된다|적용하지 아니한다|적용하지 않는다|면제한다)[^.!?]*)",

        text,
    )


    if match:

        return clean_text(
            match.group(
                1
            )
        )


    return ""


def extract_actor_clause(
    text: str
) -> str:

    text = clean_text(
        text
    )


    actor_terms = (

        "사업주는",

        "사업자는",

        "사용자는",

        "근로자는",

        "법인은",

        "기관은",

        "국가와 지방자치단체의 장은",
    )


    for term in actor_terms:

        index = text.find(
            term
        )


        if index >= 0:

            return clean_text(
                text[
                    :index
                    +
                    len(
                        term
                    )
                ]
            )


    return ""


def extract_norm_clause(
    text: str
) -> str:

    text = clean_text(
        text
    )


    patterns = (

        r"([^.!?]{0,220}하여야 한다)",

        r"([^.!?]{0,220}해야 한다)",

        r"([^.!?]{0,220}아니 된다)",
    )


    for pattern in patterns:

        match = re.search(
            pattern,
            text
        )


        if match:

            return clean_text(
                match.group(
                    1
                )
            )


    return ""
