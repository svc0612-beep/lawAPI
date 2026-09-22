# ============================================================
# 국회도서관 상세정보 서비스
#
# 역할
# 1. controlno 기반 상세정보 조회
# 2. controlno 기반 목차 조회
# 3. detail + toc 통합
# 4. LibraryEvidence 변환
#
# 현재 지원:
# - /detail
# - /toc
#
# 아직 지원하지 않음:
# - 키워드 기반 자료 검색
#
# 실제 XML / HTTP / 파싱 구현은
# 역할별 모듈로 분리되어 있다.
# ============================================================

import os
import sys

from dataclasses import asdict


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
# 2. 설정
# ============================================================

from core.config import (
    CACHE_TTL,
)


# ============================================================
# 3. Evidence 모델
# ============================================================

from models.evidence import (
    LibraryEvidence,
)


# ============================================================
# 4. 유틸
# ============================================================

from services.library.nanet_utils import (
    normalize_text,
    split_keywords,
)


# ============================================================
# 5. XML
# ============================================================

from services.library.nanet_xml import (
    strip_namespace,
    xml_element_to_dict,
    parse_xml_response,
    validate_response_status,
)


# ============================================================
# 6. Fetcher
# ============================================================

from services.library.nanet_fetcher import (
    request_nanet,
)


# ============================================================
# 7. Parser
# ============================================================

from services.library.nanet_parser import (
    extract_detail_fields,
    normalize_detail_record,
    extract_toc_text,
    parse_toc_items,
    normalize_toc_record,
)


# ============================================================
# 8. 상세정보 조회
# ============================================================

def get_detail(
    control_no: str
):

    data = request_nanet(

        path="detail",

        control_no=control_no,

        endpoint="nanet-detail",

        ttl_hours=CACHE_TTL[
            "nanet_detail"
        ],
    )

    return normalize_detail_record(
        data=data,
        control_no=control_no
    )


# ============================================================
# 9. 목차 조회
# ============================================================

def get_toc(
    control_no: str
):

    data = request_nanet(

        path="toc",

        control_no=control_no,

        endpoint="nanet-toc",

        ttl_hours=CACHE_TTL[
            "nanet_toc"
        ],
    )

    return normalize_toc_record(
        data=data,
        control_no=control_no
    )


# ============================================================
# 10. 상세 + 목차 통합
# ============================================================

def get_library_record(
    control_no: str
):

    detail = get_detail(
        control_no
    )

    toc = get_toc(
        control_no
    )

    return {

        "control_no":
            detail.get(
                "control_no",
                control_no
            ),

        "title":
            detail.get(
                "title",
                ""
            ),

        "author":
            detail.get(
                "author",
                ""
            ),

        "publisher":
            detail.get(
                "publisher",
                ""
            ),

        "publication_year":
            detail.get(
                "publication_year",
                ""
            ),

        "keywords":
            detail.get(
                "keywords",
                []
            ),

        "isbn":
            detail.get(
                "isbn",
                ""
            ),

        "issn":
            detail.get(
                "issn",
                ""
            ),

        "language":
            detail.get(
                "language",
                ""
            ),

        "call_number":
            detail.get(
                "call_number",
                ""
            ),

        "library_room":
            detail.get(
                "library_room",
                ""
            ),

        "has_original_db":
            detail.get(
                "has_original_db",
                ""
            ),

        "has_toc":
            detail.get(
                "has_toc",
                ""
            ),

        "copyright_permission":
            detail.get(
                "copyright_permission",
                ""
            ),

        "voice_support":
            detail.get(
                "voice_support",
                ""
            ),

        "toc_items":
            toc.get(
                "toc_items",
                []
            ),
    }


# ============================================================
# 11. LibraryEvidence 객체 생성
# ============================================================

def get_library_evidence(
    control_no: str
):
    """
    국회도서관 자료를 조회한 뒤
    공통 LibraryEvidence 모델로 변환한다.
    """

    record = get_library_record(
        control_no
    )

    return LibraryEvidence(

        control_no=str(
            record.get(
                "control_no",
                ""
            )
            or ""
        ),

        title=str(
            record.get(
                "title",
                ""
            )
            or ""
        ),

        author=str(
            record.get(
                "author",
                ""
            )
            or ""
        ),

        publisher=str(
            record.get(
                "publisher",
                ""
            )
            or ""
        ),

        publication_year=str(
            record.get(
                "publication_year",
                ""
            )
            or ""
        ),

        keywords=list(
            record.get(
                "keywords",
                []
            )
            or []
        ),

        isbn=str(
            record.get(
                "isbn",
                ""
            )
            or ""
        ),

        issn=str(
            record.get(
                "issn",
                ""
            )
            or ""
        ),

        language=str(
            record.get(
                "language",
                ""
            )
            or ""
        ),

        call_number=str(
            record.get(
                "call_number",
                ""
            )
            or ""
        ),

        library_room=str(
            record.get(
                "library_room",
                ""
            )
            or ""
        ),

        has_original_db=str(
            record.get(
                "has_original_db",
                ""
            )
            or ""
        ),

        has_toc=str(
            record.get(
                "has_toc",
                ""
            )
            or ""
        ),

        copyright_permission=str(
            record.get(
                "copyright_permission",
                ""
            )
            or ""
        ),

        voice_support=str(
            record.get(
                "voice_support",
                ""
            )
            or ""
        ),

        toc_items=list(
            record.get(
                "toc_items",
                []
            )
            or []
        ),
    )


# ============================================================
# 12. 기존 공개 API 호환
# ============================================================

__all__ = [

    "normalize_text",

    "split_keywords",

    "strip_namespace",

    "xml_element_to_dict",

    "parse_xml_response",

    "validate_response_status",

    "request_nanet",

    "extract_detail_fields",

    "normalize_detail_record",

    "extract_toc_text",

    "parse_toc_items",

    "normalize_toc_record",

    "get_detail",

    "get_toc",

    "get_library_record",

    "get_library_evidence",
]


# ============================================================
# 13. 단독 테스트
# ============================================================

if __name__ == "__main__":

    test_control_no = (
        "MONO1201027232"
    )

    print()

    print(
        "=" * 70
    )

    print(
        "국회도서관 LibraryEvidence 변환 테스트"
    )

    print(
        "=" * 70
    )

    print(
        "controlno:",
        test_control_no
    )

    try:

        evidence = get_library_evidence(
            test_control_no
        )

        result = asdict(
            evidence
        )

        print()

        print(
            "자료형:",
            type(
                evidence
            ).__name__
        )

        print(
            "출처:",
            result.get(
                "source"
            )
        )

        print(
            "제어번호:",
            result.get(
                "control_no"
            )
        )

        print(
            "제목:",
            result.get(
                "title"
            )
        )

        print(
            "저자:",
            result.get(
                "author"
            )
        )

        print(
            "발행자:",
            result.get(
                "publisher"
            )
        )

        print(
            "발행년도:",
            result.get(
                "publication_year"
            )
        )

        print(
            "본문언어:",
            result.get(
                "language"
            )
        )

        print(
            "원문DB:",
            result.get(
                "has_original_db"
            )
        )

        print(
            "목차 제공:",
            result.get(
                "has_toc"
            )
        )

        print(
            "목차 항목 수:",
            len(
                result.get(
                    "toc_items",
                    []
                )
            )
        )

        print()

        print(
            "목차 앞 10개"
        )

        for index, item in enumerate(
            result.get(
                "toc_items",
                []
            )[:10],
            start=1
        ):

            print(
                f"[{index}] {item}"
            )

    except Exception as e:

        print()

        print(
            "오류:",
            e
        )