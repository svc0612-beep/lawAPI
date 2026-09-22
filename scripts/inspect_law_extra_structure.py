# ============================================================
# 법제처 전체 법령 JSON 구조 점검
#
# 목적
# - 부칙
# - 별표
# - 서식
# - 기타 첨부자료
#
# 실제 API JSON 구조를 먼저 확인한다.
#
# 특정 법령 구조를 하드코딩하기 위한 스크립트가 아니라,
# 법제처 API의 공통 응답 구조를 파악하기 위한 점검용이다.
# ============================================================

import os
import sys
import json
import requests

from dotenv import load_dotenv


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
# 2. 환경변수
# ============================================================

load_dotenv(
    os.path.join(
        PROJECT_ROOT,
        ".env"
    )
)

LAW_API_KEY = os.getenv(
    "LAW_API_KEY"
)


if not LAW_API_KEY:

    raise RuntimeError(
        "LAW_API_KEY를 찾을 수 없습니다."
    )


# ============================================================
# 3. 기존 법령 검색
# ============================================================

from services.law.search import search_law


# ============================================================
# 4. 법령 상세 API
# ============================================================

LAW_SERVICE_URL = (
    "https://www.law.go.kr/"
    "DRF/lawService.do"
)


# ============================================================
# 5. 출력용 함수
# ============================================================

def print_section(
    title,
    value
):

    print(
        "\n"
        +
        "=" * 80
    )

    print(
        title
    )

    print(
        "=" * 80
    )

    if isinstance(
        value,
        (dict, list)
    ):

        print(
            json.dumps(
                value,
                ensure_ascii=False,
                indent=2
            )[:8000]
        )

    else:

        print(
            value
        )


# ============================================================
# 6. 재귀적으로 키 탐색
#
# 부칙 / 별표 / 서식 / 첨부 관련 키를
# 전체 JSON에서 찾아본다.
# ============================================================

TARGET_WORDS = [
    "부칙",
    "별표",
    "서식",
    "첨부",
    "별지",
]


def find_interesting_keys(
    obj,
    path="root"
):

    results = []


    if isinstance(
        obj,
        dict
    ):

        for key, value in obj.items():

            current_path = (
                f"{path}.{key}"
            )


            if any(
                word in str(key)
                for word in TARGET_WORDS
            ):

                results.append(
                    {
                        "path":
                            current_path,

                        "key":
                            key,

                        "type":
                            type(value).__name__,

                        "preview":
                            value,
                    }
                )


            results.extend(
                find_interesting_keys(
                    value,
                    current_path
                )
            )


    elif isinstance(
        obj,
        list
    ):

        for index, value in enumerate(
            obj[:20]
        ):

            results.extend(
                find_interesting_keys(
                    value,
                    f"{path}[{index}]"
                )
            )


    return results


# ============================================================
# 7. 법령 상세 조회
# ============================================================

def inspect_law(
    law_name
):

    # --------------------------------------------------------
    # 법령 검색
    # --------------------------------------------------------

    search_results = search_law(
        query=law_name,
        display=20
    )


    if not search_results:

        print(
            "법령 검색 결과가 없습니다."
        )

        return


    # --------------------------------------------------------
    # 정확한 법령명 우선
    # --------------------------------------------------------

    selected = None


    for item in search_results:

        if (
            item.get(
                "법령명한글"
            )
            ==
            law_name
        ):

            selected = item

            break


    if selected is None:

        selected = search_results[0]


    selected_name = selected.get(
        "법령명한글"
    )


    mst = selected.get(
        "법령일련번호"
    )


    print_section(
        "선택 법령",
        {
            "법령명":
                selected_name,

            "MST":
                mst,

            "법령ID":
                selected.get(
                    "법령ID"
                ),

            "종류":
                selected.get(
                    "법령구분명"
                ),
        }
    )


    # --------------------------------------------------------
    # 상세조회
    # --------------------------------------------------------

    params = {
        "OC":
            LAW_API_KEY,

        "target":
            "law",

        "MST":
            mst,

        "type":
            "JSON",
    }


    response = requests.get(
        LAW_SERVICE_URL,
        params=params,
        timeout=30
    )


    response.raise_for_status()


    data = response.json()


    # --------------------------------------------------------
    # 최상위 구조
    # --------------------------------------------------------

    print_section(
        "최상위 KEY",
        list(
            data.keys()
        )
    )


    law_root = data.get(
        "법령",
        {}
    )


    print_section(
        "법령 내부 KEY",
        list(
            law_root.keys()
        )
        if isinstance(
            law_root,
            dict
        )
        else
        type(
            law_root
        ).__name__
    )


    # --------------------------------------------------------
    # 부칙 / 별표 / 서식 관련 구조 탐색
    # --------------------------------------------------------

    interesting = (
        find_interesting_keys(
            data
        )
    )


    print(
        "\n"
        +
        "=" * 80
    )

    print(
        "부칙 / 별표 / 서식 관련 KEY 탐색 결과"
    )

    print(
        "=" * 80
    )


    if not interesting:

        print(
            "관련 KEY를 찾지 못했습니다."
        )

        return


    for index, item in enumerate(
        interesting,
        start=1
    ):

        print(
            f"\n[{index}]"
        )

        print(
            "PATH =",
            item[
                "path"
            ]
        )

        print(
            "KEY  =",
            item[
                "key"
            ]
        )

        print(
            "TYPE =",
            item[
                "type"
            ]
        )


        preview = item[
            "preview"
        ]


        if isinstance(
            preview,
            (dict, list)
        ):

            text = json.dumps(
                preview,
                ensure_ascii=False,
                indent=2
            )


            print(
                text[:3000]
            )

        else:

            print(
                str(
                    preview
                )[:3000]
            )


# ============================================================
# 8. 실행
#
# 구조가 비교적 큰 법령 하나로 확인
# 특정 법령 전용 코드는 아님.
# ============================================================

if __name__ == "__main__":

    inspect_law(
        "장애인복지법"
    )