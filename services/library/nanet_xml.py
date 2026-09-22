# ============================================================
# 국회도서관 XML 처리
#
# 역할
# - namespace 제거
# - XML Element → dict
# - XML 문자열 → dict
# - API 응답 상태 검증
# ============================================================

import xml.etree.ElementTree as ET

from services.library.nanet_utils import (
    normalize_text,
)


# ============================================================
# 1. XML namespace 제거
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
# 2. XML Element → dict
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
# 3. XML 문자열 → dict
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
            f"국회도서관 XML 파싱 오류: {e}"
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
# 4. 응답 상태 확인
# ============================================================

def validate_response_status(data: dict):
    if not isinstance(data, dict):
        raise RuntimeError("국회도서관 응답 구조가 올바르지 않습니다.")
    if "OpenAPI_ServiceResponse" in data:
        raise RuntimeError("국회도서관 API 게이트웨이가 요청을 거부했습니다.")
    response = data.get("response")
    if not isinstance(response, dict):
        raise RuntimeError("국회도서관 응답 구조가 올바르지 않습니다.")
    header = response.get("header")
    if not isinstance(header, dict):
        raise RuntimeError("국회도서관 응답 상태를 확인할 수 없습니다.")
    code = normalize_text(header.get("resultCode"))
    if code != "00":
        # Do not expose an untrusted error body that may echo credentials.
        raise RuntimeError("국회도서관 API가 정상 응답을 반환하지 않았습니다.")
