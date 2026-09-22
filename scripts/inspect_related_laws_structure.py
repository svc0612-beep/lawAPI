# ============================================================
# 법제처 법령 체계도 JSON 구조 점검
#
# 목적
# - lsStmd 실제 응답의 키와 컨테이너 구조를 확인한다.
# - 인증키와 요청 URL은 출력하지 않는다.
# - parser 구현 전에 여러 법령의 공통 구조를 비교한다.
# ============================================================

import json
import os
import re
import sys
from typing import Any

import requests
from dotenv import load_dotenv


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


load_dotenv(
    os.path.join(
        PROJECT_ROOT,
        ".env",
    )
)


LAW_API_KEY = os.getenv(
    "LAW_API_KEY"
)

LAW_SERVICE_URL = (
    "https://www.law.go.kr/DRF/lawService.do"
)


def describe_shape(
    value: Any,
    depth: int = 0,
    max_depth: int = 10,
) -> Any:

    if depth >= max_depth:
        return type(value).__name__

    if isinstance(value, dict):

        return {
            str(key): describe_shape(
                child,
                depth + 1,
                max_depth,
            )
            for key, child in value.items()
        }

    if isinstance(value, list):

        return {
            "__type__": "list",
            "__length__": len(value),
            "__item__": (
                describe_shape(
                    value[0],
                    depth + 1,
                    max_depth,
                )
                if value
                else None
            ),
        }

    return type(value).__name__


def redact_sensitive(
    value: Any,
    key_name: str = "",
) -> Any:

    if isinstance(value, dict):

        return {
            str(key): redact_sensitive(
                child,
                str(key),
            )
            for key, child in value.items()
        }

    if isinstance(value, list):

        return [
            redact_sensitive(child, key_name)
            for child in value
        ]

    if "링크" in key_name:
        return "[링크 생략]"

    if isinstance(value, str):

        redacted = value

        if LAW_API_KEY:
            redacted = redacted.replace(
                LAW_API_KEY,
                "[인증값 생략]",
            )

        redacted = re.sub(
            r"([?&]OC=)[^&]+",
            r"\1[인증값 생략]",
            redacted,
            flags=re.IGNORECASE,
        )

        return redacted

    return value


def inspect_mst(
    label: str,
    mst: str,
) -> None:

    if not LAW_API_KEY:
        raise RuntimeError(
            "LAW_API_KEY를 찾을 수 없습니다."
        )

    params = {
        "OC": LAW_API_KEY,
        "target": "lsStmd",
        "type": "JSON",
        "MST": mst,
    }

    try:

        response = requests.get(
            LAW_SERVICE_URL,
            params=params,
            timeout=30,
        )

        response.raise_for_status()

        data = response.json()

    except requests.RequestException:

        raise RuntimeError(
            "법령 체계도 API 호출에 실패했습니다."
        ) from None

    except ValueError:

        raise RuntimeError(
            "법령 체계도 응답을 JSON으로 해석할 수 없습니다."
        ) from None

    print(
        f"===== {label} / MST={mst} ====="
    )

    print(
        json.dumps(
            describe_shape(data),
            ensure_ascii=False,
            indent=2,
        )
    )

    print(
        "----- 값 미리보기(링크/인증값 제거) -----"
    )

    print(
        json.dumps(
            redact_sensitive(data),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":

    inspect_mst(
        "대한민국헌법",
        "61603",
    )

    inspect_mst(
        "특허법",
        "279827",
    )

    inspect_mst(
        "민법",
        "284415",
    )
