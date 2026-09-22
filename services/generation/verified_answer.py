# ============================================================
# 검증된 답변 렌더러
#
# 역할
# - result 딕셔너리의 검증된 법령/판례 원문을 사용자용 마크다운으로 조립
# - 결코 새 법률 결론을 생성하지 않음
# - 원문을 인용부(>)로 표시하고 출처 링크를 붙임
#
# 변경 이력
# - 2026-09-21: 판례 렌더 세 가지 버그 수정
#   1) <br/> 로 시작하는 판결요지 → 빈 인용줄이 앞에 붙는 문제 수정
#   2) 판결요지(summary)가 없어도 판시사항(holding)이 있으면 그것을 대신 인용
#   3) 실제 검증이 통과했는데도 "검증 완료되지 않아..." 문구가 뜨는 오해 수정
# - 2026-09-21 (2차): 사건명 노출 조건 강화
#   판결요지·판시사항 중 하나가 실제로 인용 가능할 때만 사건명 노출
#   (원문 인용 불가 상태의 판례는 사건명 필드도 신뢰 못 하므로 표시하지 않음)
# ============================================================

import re


# ============================================================
# 조 라벨 생성
# 예: 제37조, 제9조의2
# ============================================================

def label(row):

    sub = row.get(
        "sub_article_number",
        0
    )

    return (
        f"제{row['article_number']}조"
        + (f"의{sub}" if sub else "")
    )


# ============================================================
# 인용 블록 생성 헬퍼
#
# 여러 줄 텍스트를 '> ' prefix로 감싸되,
# 앞뒤 빈 줄과 <br/> 유래 빈 줄은 제거해서
# '> ' 만 홀로 뜨는 시각적 노이즈를 없앤다.
# ============================================================

def _quote_block(
    text: str
) -> str:

    # <br/>·<br>·<BR /> 등을 개행으로 치환
    text = re.sub(
        r"<br\s*/?>",
        "\n",
        str(text or ""),
        flags=re.I
    )

    # 라인 단위 분해 후 오른쪽 공백 트리밍
    raw_lines = [
        line.rstrip()
        for line in text.splitlines()
    ]

    # 앞쪽 빈 줄 제거
    while raw_lines and not raw_lines[0].strip():
        raw_lines.pop(0)

    # 뒤쪽 빈 줄 제거
    while raw_lines and not raw_lines[-1].strip():
        raw_lines.pop()

    # 남은 게 없으면 빈 문자열
    if not raw_lines:
        return ""

    # 각 줄 앞에 '> ' 붙임 (빈 줄은 '>' 한 개로)
    return "\n".join(
        ("> " + line) if line.strip() else ">"
        for line in raw_lines
    )


# ============================================================
# 판례 한 건 렌더
#
# 반환: 렌더된 라인들 (join 대상)
#
# 노출 원칙:
#   detail_verified=True 이고 판결요지 또는 판시사항 원문이 있을 때만
#   → 사건명 + 원문 인용 블록 노출
#   그 외 → "검증 미완료" 안내만 (사건명 포함해서 어떤 세부 필드도 노출 X)
#
# 이유: 검증 안 됐거나 인용할 원문이 없는 판례의 사건명 필드는
#       형량·오해 소지 있는 문구를 담고 있을 수 있음.
# ============================================================

def _render_precedent(
    case: dict
) -> list:

    lines = []

    # 상단 타이틀 (법원, 사건번호, 선고일, 사건종류)
    # → 이 4개는 판례 목록 API 자체에서 검증된 식별정보라 항상 노출 OK
    title = (
        f"{case.get('court_name', '')} "
        f"{case.get('case_number', '')} "
        f"({case.get('decision_date', '')}) "
        f"· {case.get('case_type', '사건종류 미확인')}"
    )
    lines.append(title)

    # 필드 정리
    summary_raw = str(
        case.get("summary", "")
        or ""
    ).strip()

    holding_raw = str(
        case.get("holding", "")
        or ""
    ).strip()

    verified = bool(
        case.get("detail_verified")
    )

    # 어떤 필드를 어떤 라벨로 인용할지 결정
    quoted = ""
    field_label = ""

    if verified and summary_raw:

        quoted = _quote_block(summary_raw)
        field_label = "판결요지"

    elif verified and holding_raw:

        # 판결요지가 없으면 판시사항으로 대체 인용
        quoted = _quote_block(holding_raw)
        field_label = "판시사항"

    # 실제로 인용할 텍스트가 나온 경우에만 사건명 + 인용 노출
    if quoted:

        # 사건명 노출 (인용 가능한 원문이 있을 때만)
        case_name = str(
            case.get("case_name", "")
            or ""
        ).strip()
        if case_name:
            lines.append(
                f"사건명: {case_name}"
            )

        lines.append(
            f"{field_label} 원문:\n{quoted}"
        )

    else:

        # verified=False 이거나 두 필드 모두 비어있을 때
        # 사건명도 노출하지 않고 안내 문구만 표시
        lines.append(
            "판결요지·본문의 일치 검증이 완료되지 않아 "
            "판결 내용과 선고형을 설명하지 않습니다."
        )

    # 원문 링크 (있으면 항상 노출)
    link = case.get("official_link")
    if link:
        lines.append(
            f"[판례 원문]({link})"
        )

    return lines


# ============================================================
# 메인 렌더러
# ============================================================

def build_verified_answer(
    result: dict
) -> str:

    rows = result.get(
        "verified_laws",
        []
    )

    meta = result.get(
        "metadata",
        {}
    )

    lines = []

    # ------------------------------------------------------------
    # 1. 법령 조문 원문 블록
    # ------------------------------------------------------------
    if rows:

        lines.append(
            "질문과 관련해 조회한 법령 원문입니다. "
            "아래 조문이 실제 사건에 적용되는지와 처벌 여부는 아직 확정하지 않았습니다. "
            "원문의 형량은 법정형이며 실제 선고형을 예측한 것이 아닙니다."
        )

        for title, roles in [
            ("관련 조문 원문", {"direct", "requested", "candidate"}),
            ("연결된 제재 조문 원문", {"sanction_reference"}),
        ]:

            group = [
                r for r in rows
                if r.get("role") in roles
            ]

            if not group:
                continue

            lines.append("**" + title + "**")

            # 벌칙 참조 블록은 추가 안내를 붙인다
            if "sanction_reference" in roles:
                lines.append(
                    "관련 조문 번호를 참조하는 제재 규정입니다. "
                    "규정 안의 대상·항·호·예외를 확인해야 하며, "
                    "아래 벌칙 전체가 질문에 적용된다는 뜻은 아닙니다. "
                    "법정형과 실제 선고형은 다릅니다."
                )

            for row in group:

                # 헤더: 법령명 + 조 라벨 + 조문 제목 + 시행일
                lines.append(
                    f"**{row['law_name']} {label(row)} "
                    f"{row.get('article_title', '')}** "
                    f"· 시행일 {row.get('effective_date', '미확인')}"
                )

                # 조문 본문 인용 (헬퍼로 빈 줄 정리)
                lines.append(
                    _quote_block(row["article_text"])
                )

                # 출처 링크
                lines.append(
                    f"[국가법령정보센터 원문]({row['official_link']})"
                )

        # 벌칙 참조 블록이 하나도 없을 때 안내
        if not any(
            r.get("role") == "sanction_reference"
            for r in rows
        ):
            lines.append(
                "처벌 규정을 별도로 확정하지 못했습니다. "
                "처벌 규정이 없다는 의미는 아닙니다."
            )

    # ------------------------------------------------------------
    # 2. 조문 없음 → 법령 전체조회 or 실패 안내
    # ------------------------------------------------------------
    else:

        full = result.get("full_law")

        if (
            result.get("question_type") == "법령_전체조회"
            and meta.get("full_law_verified")
            and full
        ):

            from services.evidence.verified_retrieval import (
                law_link,
            )

            lines.append(
                f"{full['law_name']} 전문 "
                f"{full.get('article_count', len(full['articles']))}개 조문을 조회했습니다. "
                f"시행일: {full['effective_date']}. "
                f"[국가법령정보센터 원문]({law_link(full['mst'])})"
            )

        else:

            lines.append(
                "질문에 답할 수 있는 법령 원문을 충분히 확인하지 못했습니다. "
                "검색 결과만으로 처벌이나 법적 결론을 제시하지 않습니다."
            )

    # ------------------------------------------------------------
    # 3. 요청한 항 미확인 안내
    # ------------------------------------------------------------
    if meta.get("requested_paragraph_available") is False:
        lines.append(
            "요청한 항을 원문에서 확인하지 못했습니다. "
            "위 내용은 해당 조 전체이며 요청한 항에 대한 답변이 아닙니다."
        )

    # ------------------------------------------------------------
    # 4. 커버리지·추가 질문 안내
    # ------------------------------------------------------------
    questions = meta.get(
        "additional_questions",
        []
    )

    if meta.get("coverage_limited"):
        lines.append(
            "질문에 포함된 쟁점이 많아 일부 후보 법령만 조회했습니다. "
            "답변이 모든 쟁점을 다루지 못하므로 질문을 나누어 확인해야 합니다."
        )

    if questions:
        lines.append(
            "**적용 여부를 판단하기 위해 필요한 정보**\n"
            + "\n".join("- " + q for q in questions)
        )

    # ------------------------------------------------------------
    # 5. 시점 안내 (항상)
    # ------------------------------------------------------------
    lines.append(
        "사건 발생일과 당시 시행법·개정 부칙은 별도 확인이 필요합니다. "
        "현재 조회한 원문을 과거 사건에 그대로 적용하지 않습니다."
    )

    # ------------------------------------------------------------
    # 6. 판례 블록
    # ------------------------------------------------------------
    cases = result.get("precedents") or []

    lines.append("**판례 확인**")

    if not cases:
        lines.append(
            "이번 조회에서 판례를 확보하지 못했습니다. "
            "판례의 존재 여부나 처벌 가능성을 판단할 수 없습니다."
        )

    for case in cases:
        lines.extend(
            _render_precedent(case)
        )

    if cases:
        lines.append(
            "검색된 판례는 검토 후보입니다. "
            "사실관계의 유사성, 판결의 후속 변경 및 실제 선고형을 별도로 확인해야 합니다."
        )

    # ------------------------------------------------------------
    # 7. 출처 상태 안내
    # ------------------------------------------------------------
    for status in result.get("source_status", []):

        if (
            status.get("endpoint") == "exact-original"
            and status.get("status") == "not_found"
        ):
            lines.append(
                "요청한 조문을 원문에서 찾지 못했습니다. "
                "다른 조문으로 대신 답하지 않습니다."
            )

        if status.get("status") in ("error", "partial"):
            lines.append(
                f"조회 제한: "
                f"{status.get('source', '')} "
                f"{status.get('endpoint', '')} "
                f"— {status.get('message', '조회 실패')}"
            )

    return "\n\n".join(lines)
