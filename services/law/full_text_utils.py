# ============================================================
# Full Text 공통 유틸리티
# ============================================================

import re

from typing import (
    Any,
    List,
    Optional,
)


def normalize_text(
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


def compact_text(
    value: Any
) -> str:

    text = normalize_text(
        value
    )

    text = re.sub(
        r"[^가-힣A-Za-z0-9]",
        "",
        text
    )

    return text.lower()


def safe_int(
    value: Any,
    default: Optional[int] = None
) -> Optional[int]:

    try:
        return int(
            value
        )

    except (
        TypeError,
        ValueError
    ):
        return default


def ensure_list(
    value: Any
) -> List[Any]:

    if value is None:
        return []

    if isinstance(
        value,
        list
    ):
        return value

    return [
        value
    ]