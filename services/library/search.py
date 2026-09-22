# ============================================================
# 국회도서관 자료검색 서비스
#
# 역할
# 1. 키워드 기반 국회도서관 자료 검색
# 2. searchservice/basic 호출
# 3. XML 응답 파싱
# 4. controlno 추출
# 5. SQLite 캐시 사용
#
# 상세정보 / 목차 조회는
# services/library/nanet.py 에서 담당한다.
# ============================================================

import os
import sys
import requests
import xml.etree.ElementTree as ET
from services.library.nanet_xml import validate_response_status


# ============================================================
# 1. 프로젝트 루트 등록
# ============================================================

CURRENT_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        CURRENT_DIR
    )
)

if PROJECT_ROOT not in sys.path:
    sys.path.append(
        PROJECT_ROOT
    )


# ============================================================
# 2. 공통 설정
# ============================================================

from core.config import (
    NANET_API_KEY,
    SOURCE_NANET,
    validate_nanet_api_key,
)


# ============================================================
# 3. 공통 캐시
# ============================================================

from core.cache import (
    get_cache,
    save_cache,
    record_api_call,
)


# ============================================================
# 4. 자료검색 API URL
# ============================================================

NANET_SEARCH_URL = (
    "https://apis.data.go.kr/9720000/searchservice/basic"
)


# ============================================================
# 5. 텍스트 정리
# ============================================================

def normalize_text(
    value
):

    if value is None:
        return ""

    return str(
        value
    ).strip()


# ============================================================
# 6. XML namespace 제거
# ============================================================

def strip_namespace(
    tag: str
):

    if not tag:
        return ""

    if "}" in tag:
        return tag.split(
            "}",
            1
        )[1]

    return tag


# ============================================================
# 7. XML Element → dict
# ============================================================

def xml_element_to_dict(
    element
):

    children = list(
        element
    )


    if not children:

        return normalize_text(
            element.text
        )


    result = {}


    for child in children:

        tag = strip_namespace(
            child.tag
        )


        value = xml_element_to_dict(
            child
        )


        if tag in result:

            if not isinstance(
                result[tag],
                list
            ):

                result[tag] = [
                    result[tag]
                ]


            result[tag].append(
                value
            )


        else:

            result[tag] = value


    return result


# ============================================================
# 8. XML 문자열 → dict
# ============================================================

def parse_xml_response(
    xml_text: str
):

    try:

        root = ET.fromstring(
            xml_text
        )


    except ET.ParseError as e:

        raise RuntimeError(
            f"국회도서관 검색 XML 파싱 오류: {e}"
        )


    return {

        strip_namespace(
            root.tag
        ):
            xml_element_to_dict(
                root
            )
    }


# ============================================================
# 9. 실제 검색 결과처럼 보이는 item인지 확인
# ============================================================

def is_search_item(
    item
):

    if not isinstance(
        item,
        dict
    ):
        return False


    keys = {
        str(
            key
        ).lower()
        for key in item.keys()
    }


    # controlno 또는 제목 계열 필드가 있으면
    # 검색 결과 후보로 본다.
    return bool(

        {
            "controlno",
            "control_no",
            "title",
            "자료명",
        }

        &
        keys
    )


# ============================================================
# 10. 응답 전체에서 검색 결과 추출
# ============================================================

def extract_search_items(
    data
):

    # ================================================================
    # 국회도서관 API 실제 응답: response.recode = [{item: [{name, value}, ...]}, ...]
    # is_search_item()은 직접 키(controlno/title 등)를 찾아서 이 구조를 못 잡음.
    # 여기서 recode 를 먼저 파싱하고, 실패 시 기존 walk 로직으로 fallback.
    # ================================================================
    if isinstance(data, dict):
        _resp = data.get("response", {})
        if isinstance(_resp, dict):
            _recode = _resp.get("recode", [])
            if isinstance(_recode, dict):
                _recode = [_recode]
            if isinstance(_recode, list) and _recode:
                _parsed = []
                for _entry in _recode:
                    if not isinstance(_entry, dict):
                        continue
                    _raw_items = _entry.get("item", [])
                    if isinstance(_raw_items, dict):
                        _raw_items = [_raw_items]
                    if not isinstance(_raw_items, list):
                        continue
                    # {name, value} 쌍들을 하나의 dict 로 재구성
                    _flat = {}
                    for _nv in _raw_items:
                        if not isinstance(_nv, dict):
                            continue
                        _name = str(_nv.get("name", "") or "").strip()
                        _value = str(_nv.get("value", "") or "").strip()
                        if _name:
                            _flat[_name] = _value
                    if _flat:
                        _parsed.append(_flat)
                if _parsed:
                    return _parsed

    # 기존 walk 로직 (다른 응답 형식 fallback)
    results = []


    def walk(
        value
    ):

        if isinstance(
            value,
            dict
        ):

            if is_search_item(
                value
            ):

                results.append(
                    value
                )

                return


            for child in value.values():

                walk(
                    child
                )


        elif isinstance(
            value,
            list
        ):

            for child in value:

                walk(
                    child
                )


    walk(
        data
    )


    return results


# ============================================================
# 11. 특정 키 후보에서 값 찾기
# ============================================================

def pick_value(
    item: dict,
    candidates
):

    for key in candidates:

        if key in item:

            value = normalize_text(
                item.get(
                    key
                )
            )

            if value:

                return value


    return ""


# ============================================================
# 12. 검색 결과 정규화
# ============================================================

def normalize_search_item(
    item: dict,
    rank: int
):

    return {

        "rank":
            rank,

        "control_no":
            pick_value(
                item,
                [
                    "controlno",
                    "controlNo",
                    "control_no",
                    "제어번호",
                ]
            ),

        "title":
            pick_value(
                item,
                [
                    "title",
                    "자료명",
                    "기사명",
                    "서명",
                ]
            ),

        "author":
            pick_value(
                item,
                [
                    "author",
                    "저자",
                    "저자명",
                ]
            ),

        "publisher":
            pick_value(
                item,
                [
                    "publisher",
                    "발행자",
                    "출판사",
                ]
            ),

        "publication_year":
            pick_value(
                item,
                [
                    "publicationyear",
                    "publicationYear",
                    "발행년도",
                    "발행년",
                ]
            ),

        "raw":
            item,
    }


# ============================================================
# 13. 국회도서관 자료 검색
# ============================================================

def search_library(
    keyword: str,
    search_field: str = "자료명",
    page_no: int = 1,
    display_lines: int = 10
):

    validate_nanet_api_key()


    keyword = normalize_text(
        keyword
    )


    if not keyword:

        return []


    search_value = (
        f"{search_field},{keyword}"
    )


    params = {

        "ServiceKey":
            NANET_API_KEY,

        "pageno":
            page_no,

        "displaylines":
            display_lines,

        "search":
            search_value,
    }


    endpoint = (
        "nanet-search-basic"
    )


    # ========================================================
    # 캐시 확인
    # ========================================================

    cached = get_cache(
        source=SOURCE_NANET,
        endpoint=endpoint,
        params=params
    )


    if cached is not None:

        validate_response_status(cached)

        print(
            f"[CACHE HIT] 국회도서관 검색: "
            f"{search_value}"
        )


        raw_items = extract_search_items(
            cached
        )


        return [

            normalize_search_item(
                item=item,
                rank=index
            )

            for index, item in enumerate(
                raw_items,
                start=1
            )
        ]


    # ========================================================
    # 실제 API 호출
    # ========================================================

    print(
        f"[API CALL] 국회도서관 검색: "
        f"{search_value}"
    )


    try:

        response = requests.get(
            NANET_SEARCH_URL,
            params=params,
            timeout=20
        )


        response.raise_for_status()


    except requests.exceptions.Timeout:

        raise RuntimeError(
            "국회도서관 자료검색 요청 시간이 초과되었습니다."
        )


    except requests.exceptions.ConnectionError:

        raise RuntimeError(
            "국회도서관 자료검색 API 서버에 연결할 수 없습니다."
        )


    except requests.exceptions.RequestException:

        raise RuntimeError(
            "국회도서관 자료검색 요청에 실패했습니다. 인증 및 서비스 권한을 확인하세요."
        ) from None


    # ========================================================
    # XML 파싱
    # ========================================================

    data = parse_xml_response(
        response.text
    )

    validate_response_status(data)


    # ========================================================
    # 실제 API 호출 기록
    # ========================================================

    record_api_call(
        source=SOURCE_NANET,
        endpoint=endpoint
    )


    # ========================================================
    # 캐시 저장
    #
    # 검색결과는 하루보다 짧게 사용
    # 현재 구현 정책으로 6시간 적용
    # ========================================================

    save_cache(
        source=SOURCE_NANET,
        endpoint=endpoint,
        params=params,
        response_data=data,
        ttl_hours=6
    )


    # ========================================================
    # 결과 추출
    # ========================================================

    raw_items = extract_search_items(
        data
    )


    results = []


    for index, item in enumerate(
        raw_items,
        start=1
    ):

        results.append(

            normalize_search_item(
                item=item,
                rank=index
            )
        )


    return results


# ============================================================
# 14. 단독 테스트
# ============================================================

if __name__ == "__main__":

    test_keyword = (
        "특허"
    )


    print()

    print(
        "=" * 70
    )

    print(
        "국회도서관 자료검색 테스트"
    )

    print(
        "=" * 70
    )


    print(
        "검색어:",
        test_keyword
    )


    try:

        results = search_library(
            keyword=test_keyword,
            search_field="자료명",
            page_no=1,
            display_lines=10
        )


        print()

        print(
            "검색 결과:",
            len(
                results
            ),
            "건"
        )


        for item in results:

            print()

            print(
                f"[{item['rank']}]"
            )


            print(
                "제어번호:",
                item.get(
                    "control_no"
                )
            )


            print(
                "제목:",
                item.get(
                    "title"
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


    except Exception as e:

        print()

        print(
            "오류:",
            e
        )
