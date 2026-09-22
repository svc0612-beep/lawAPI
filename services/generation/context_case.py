# ============================================================
# 판례 / 법령해석례 Evidence → LLM 컨텍스트
# ============================================================

from services.generation.context_utils import (
    normalize_text,
)


# ============================================================
# 1. 판례 목록
# ============================================================

def build_precedents_context(
    precedents: list
):

    if not isinstance(
        precedents,
        list
    ):

        return ""

    if not precedents:

        return ""

    lines = [
        "[관련 판례]",
    ]

    for index, item in enumerate(
        precedents,
        start=1
    ):

        if not isinstance(
            item,
            dict
        ):

            continue

        case_name = normalize_text(
            item.get(
                "case_name"
            )
        )

        case_number = normalize_text(
            item.get(
                "case_number"
            )
        )

        court_name = normalize_text(
            item.get(
                "court_name"
            )
        )

        decision_date = normalize_text(
            item.get(
                "decision_date"
            )
        )

        precedent_id = normalize_text(
            item.get(
                "precedent_id"
            )
        )

        lines.append(
            ""
        )

        lines.append(
            f"{index}. {case_name}"
        )

        if case_number:

            lines.append(
                f"사건번호: {case_number}"
            )

        if court_name:

            lines.append(
                f"법원: {court_name}"
            )

        if decision_date:

            lines.append(
                f"선고일자: {decision_date}"
            )

        if precedent_id:

            lines.append(
                f"판례 ID: {precedent_id}"
            )

    return "\n".join(
        lines
    )


# ============================================================
# 2. 법령해석례 목록
# ============================================================

def build_interpretations_context(
    interpretations: list
):

    if not isinstance(
        interpretations,
        list
    ):

        return ""

    if not interpretations:

        return ""

    lines = [
        "[법령해석례]",
    ]

    for index, item in enumerate(
        interpretations,
        start=1
    ):

        if not isinstance(
            item,
            dict
        ):

            continue

        title = normalize_text(
            item.get(
                "title"
            )
        )

        case_number = normalize_text(
            item.get(
                "case_number"
            )
        )

        reply_date = normalize_text(
            item.get(
                "reply_date"
            )
        )

        agency = normalize_text(
            item.get(
                "agency"
            )
        )

        interpretation_id = normalize_text(
            item.get(
                "interpretation_id"
            )
        )

        lines.append(
            ""
        )

        lines.append(
            f"{index}. {title}"
        )

        if case_number:

            lines.append(
                f"안건번호: {case_number}"
            )

        if reply_date:

            lines.append(
                f"회신일자: {reply_date}"
            )

        if agency:

            lines.append(
                f"기관: {agency}"
            )

        if interpretation_id:

            lines.append(
                f"해석례 ID: "
                f"{interpretation_id}"
            )

    return "\n".join(
        lines
    )