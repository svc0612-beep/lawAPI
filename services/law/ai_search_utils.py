# ============================================================
# aiSearch 공통 유틸리티
# ============================================================

import re


def normalize_text(
    text
):

    if text is None:
        return ""

    return re.sub(
        r"\s+",
        " ",
        str(text)
    ).strip()


def safe_int(
    value,
    default=0
):

    try:

        return int(
            value
        )

    except (
        TypeError,
        ValueError
    ):

        return default