# ============================================================
# 국회도서관 Evidence 연결 서비스
#
# 역할
# 1. 이미 알고 있는 controlno를 이용해 자료 조회
# 2. nanet.py의 get_library_evidence() 호출
# 3. 여러 controlno를 LibraryEvidence 목록으로 변환
# 4. EvidenceBundle dict에 국회도서관 자료 연결
#
# 중요:
# - 현재 자료검색 API는 키 권한 문제로 자동 검색하지 않는다.
# - controlno를 이미 알고 있는 경우에만 동작한다.
# - 검색 API 승인 후 search.py와 연결할 예정이다.
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
# 2. 국회도서관 서비스
# ============================================================

from services.library.nanet import (
    get_library_evidence,
)


# ============================================================
# 3. LibraryEvidence 모델
# ============================================================

from models.evidence import (
    LibraryEvidence,
)


# ============================================================
# 4. controlno 정리
# ============================================================

def normalize_control_no(
    control_no
):

    if control_no is None:

        return ""

    return str(
        control_no
    ).strip()


# ============================================================
# 5. controlno 목록 정리
# ============================================================

def normalize_control_numbers(
    control_numbers
):

    """
    입력 예:

    None
    → []

    "MONO1201027232"
    → ["MONO1201027232"]

    ["MONO1201027232", "..."]
    → 중복 제거된 리스트
    """

    if control_numbers is None:

        return []

    if isinstance(
        control_numbers,
        str
    ):

        control_numbers = [
            control_numbers
        ]

    if not isinstance(
        control_numbers,
        (
            list,
            tuple,
            set
        )
    ):

        return []

    results = []

    for control_no in control_numbers:

        normalized = normalize_control_no(
            control_no
        )

        if not normalized:

            continue

        if normalized in results:

            continue

        results.append(
            normalized
        )

    return results


# ============================================================
# 6. 단일 국회도서관 Evidence 조회
# ============================================================

def load_library_evidence(
    control_no: str
):

    control_no = normalize_control_no(
        control_no
    )

    if not control_no:

        return None

    evidence = get_library_evidence(
        control_no
    )

    if not isinstance(
        evidence,
        LibraryEvidence
    ):

        raise TypeError(
            "국회도서관 결과가 LibraryEvidence 형식이 아닙니다."
        )

    return evidence


# ============================================================
# 7. 여러 국회도서관 Evidence 조회
# ============================================================

def load_library_evidences(
    control_numbers
):

    """
    controlno 목록을 받아
    LibraryEvidence 목록으로 반환한다.

    하나의 자료 조회가 실패해도
    전체 질의 서비스를 중단하지 않는다.
    """

    normalized_numbers = (
        normalize_control_numbers(
            control_numbers
        )
    )

    if not normalized_numbers:

        return []

    results = []

    for control_no in normalized_numbers:

        try:

            evidence = load_library_evidence(
                control_no
            )

            if evidence is not None:

                results.append(
                    evidence
                )

        except Exception as e:

            # -----------------------------------------------
            # 국회도서관 보조 근거 때문에
            # 전체 법률 질의가 실패하면 안 된다.
            # -----------------------------------------------

            print(
                f"[LIBRARY WARNING] "
                f"{control_no}: "
                f"{e}"
            )

    return results


# ============================================================
# 8. EvidenceBundle dict의 기존 근거 존재 여부 확인
# ============================================================

def has_existing_evidence(
    result: dict
) -> bool:

    """
    EvidenceBundle.update_evidence_found()와
    동일한 기준으로 기존 근거가 있는지 확인한다.

    library_items는 이 함수에서 제외한다.
    국회도서관 자료는 attach_library_items()에서
    별도로 합산한다.
    """

    return any(
        [
            result.get(
                "article"
            )
            is not None,

            bool(
                result.get(
                    "laws"
                )
            ),

            bool(
                result.get(
                    "law_candidates"
                )
            ),

            bool(
                result.get(
                    "precedents"
                )
            ),

            bool(
                result.get(
                    "interpretations"
                )
            ),

            result.get(
                "basic_info"
            )
            is not None,

            result.get(
                "full_law"
            )
            is not None,

            bool(
                result.get(
                    "histories"
                )
            ),

            bool(
                result.get(
                    "related_laws"
                )
            ),

            bool(
                result.get(
                    "supplementary_provisions"
                )
            ),

            bool(
                result.get(
                    "attachments"
                )
            ),
        ]
    )


# ============================================================
# 9. EvidenceBundle dict에 국회도서관 자료 추가
# ============================================================

def attach_library_items(
    result: dict,
    control_numbers
):

    """
    query_service가 만든 EvidenceBundle dict에
    국회도서관 자료를 추가한다.

    아직 검색 API가 연결되지 않았으므로
    controlno가 명시적으로 전달된 경우에만 동작한다.
    """

    if not isinstance(
        result,
        dict
    ):

        raise TypeError(
            "result는 dict여야 합니다."
        )

    # ========================================================
    # 국회도서관 Evidence 조회
    # ========================================================

    evidences = load_library_evidences(
        control_numbers
    )

    # ========================================================
    # LibraryEvidence → dict
    #
    # LibraryEvidence는 일반 dataclass이므로
    # evidence.to_dict()가 아니라
    # dataclasses.asdict()를 사용한다.
    # ========================================================

    library_items = [

        asdict(
            evidence
        )

        for evidence in evidences
    ]

    # ========================================================
    # 국회도서관 자료 추가
    # ========================================================

    result[
        "library_items"
    ] = library_items

    # ========================================================
    # 기존 근거 존재 여부
    # ========================================================

    existing_evidence = (
        has_existing_evidence(
            result
        )
    )

    # ========================================================
    # 전체 근거 존재 여부 갱신
    # ========================================================

    result[
        "evidence_found"
    ] = bool(
        existing_evidence
        or
        library_items
    )

    # ========================================================
    # metadata 갱신
    # ========================================================

    metadata = result.get(
        "metadata"
    )

    if not isinstance(
        metadata,
        dict
    ):

        metadata = {}

    metadata[
        "library_item_count"
    ] = len(
        library_items
    )

    metadata[
        "library_auto_search_enabled"
    ] = False

    result[
        "metadata"
    ] = metadata

    return result


# ============================================================
# 10. 단독 테스트
# ============================================================

if __name__ == "__main__":

    test_control_numbers = [

        "MONO1201027232",
    ]

    print()

    print(
        "=" * 70
    )

    print(
        "국회도서관 Evidence 연결 테스트"
    )

    print(
        "=" * 70
    )

    print(
        "controlno:",
        test_control_numbers
    )

    try:

        evidences = load_library_evidences(
            test_control_numbers
        )

        print()

        print(
            "조회 결과:",
            len(
                evidences
            ),
            "건"
        )

        for index, evidence in enumerate(
            evidences,
            start=1
        ):

            # =================================================
            # LibraryEvidence는 dataclass
            # =================================================

            result = asdict(
                evidence
            )

            print()

            print(
                f"[{index}]"
            )

            print(
                "자료형:",
                type(
                    evidence
                ).__name__
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
                "발행년도:",
                result.get(
                    "publication_year"
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

    except Exception as e:

        print()

        print(
            "오류:",
            e
        )