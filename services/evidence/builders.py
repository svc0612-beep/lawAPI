# ============================================================
# API 결과 → Evidence 모델 변환
# ============================================================

from typing import (
    Any,
    Dict,
    Optional,
)

from models.evidence import (
    LawBasicInfo,
    LawEvidence,
    FullArticleEvidence,
    FullLawEvidence,
    PrecedentEvidence,
    InterpretationEvidence,
    RelatedLawEvidence,
    SupplementaryProvisionEvidence,
)

from services.evidence.common import (
    normalize_text,
    safe_int,
)


# ============================================================
# 법령 기본정보
# ============================================================

def build_basic_info(
    item: Optional[Dict[str, Any]]
) -> Optional[LawBasicInfo]:

    if not item:
        return None

    return LawBasicInfo(

        law_name=normalize_text(
            item.get("법령명한글")
        ),

        law_type=normalize_text(
            item.get("법령구분명")
        ),

        ministry=normalize_text(
            item.get("소관부처명")
        ),

        law_id=normalize_text(
            item.get("법령ID")
        ),

        mst=normalize_text(
            item.get("법령일련번호")
        ),

        promulgation_number=normalize_text(
            item.get("공포번호")
        ),

        promulgation_date=normalize_text(
            item.get("공포일자")
        ),

        effective_date=normalize_text(
            item.get("시행일자")
        ),

        revision_type=normalize_text(
            item.get("제개정구분명")
        ),

        abbreviation=normalize_text(
            item.get("법령약칭명")
        ),

        current_history_code=normalize_text(
            item.get("현행연혁코드")
        ),

        detail_link=normalize_text(
            item.get("법령상세링크")
        ),
    )


# ============================================================
# aiSearch 조문
# ============================================================

def build_law_evidence(
    item: Dict[str, Any]
) -> LawEvidence:

    return LawEvidence(

        law_name=normalize_text(
            item.get("law_name")
        ),

        law_type=normalize_text(
            item.get("law_type")
        ),

        ministry=normalize_text(
            item.get("ministry")
        ),

        law_id=normalize_text(
            item.get("law_id")
        ),

        mst=normalize_text(
            item.get("mst")
        ),

        article_number=safe_int(
            item.get("article_number")
        ),

        sub_article_number=(
            safe_int(
                item.get(
                    "sub_article_number"
                ),
                0
            )
            or 0
        ),

        article_title=normalize_text(
            item.get("article_title")
        ),

        article_text=normalize_text(
            item.get("article_text")
        ),

        effective_date=normalize_text(
            item.get("effective_date")
        ),

        promulgation_date=normalize_text(
            item.get("promulgation_date")
        ),

        revision_type=normalize_text(
            item.get("revision_type")
        ),

        relevance_score=item.get(
            "relevance_score"
        ),

        query_coverage=item.get(
            "query_coverage"
        ),

        matched_tokens=list(
            item.get(
                "matched_tokens",
                []
            )
            or []
        ),

        original_rank=safe_int(
            item.get(
                "original_rank",
                item.get("rank")
            )
        ),

        final_rank=safe_int(
            item.get("final_rank")
        ),
    )


# ============================================================
# 판례
# ============================================================

def build_precedent_evidence(
    item: Dict[str, Any]
) -> PrecedentEvidence:

    return PrecedentEvidence(
        detail_verified=bool(item.get("detail_verified", False)),
        detail_status=str(item.get("detail_status", "not_requested")),
        official_link=normalize_text(item.get("official_link")),

        case_name=normalize_text(
            item.get("case_name")
        ),

        case_number=normalize_text(
            item.get("case_number")
        ),

        decision_date=normalize_text(
            item.get("decision_date")
        ),

        court_name=normalize_text(
            item.get("court_name")
        ),

        court_type=normalize_text(
            item.get("court_type")
        ),

        case_type=normalize_text(
            item.get("case_type")
        ),

        decision_type=normalize_text(
            item.get("decision_type")
        ),

        precedent_id=normalize_text(
            item.get("precedent_id")
        ),

        rank=safe_int(
            item.get("rank")
        ),

        holding=normalize_text(
            item.get("holding")
        ),

        summary=normalize_text(
            item.get("summary")
        ),

        reasoning=normalize_text(
            item.get("reasoning")
        ),

        full_text=normalize_text(
            item.get("full_text")
        ),
    )


# ============================================================
# 법령해석례
# ============================================================

def build_interpretation_evidence(
    item: Dict[str, Any]
) -> InterpretationEvidence:

    return InterpretationEvidence(

        title=normalize_text(
            item.get("title")
        ),

        case_number=normalize_text(
            item.get("case_number")
        ),

        reply_date=normalize_text(
            item.get("reply_date")
        ),

        agency=normalize_text(
            item.get("agency")
        ),

        interpretation_id=normalize_text(
            item.get("interpretation_id")
        ),

        rank=safe_int(
            item.get("rank")
        ),

        inquiry_agency=normalize_text(
            item.get("inquiry_agency")
        ),

        reply_agency=normalize_text(
            item.get("reply_agency")
        ),

        inquiry_summary=normalize_text(
            item.get("inquiry_summary")
        ),

        answer_summary=normalize_text(
            item.get("answer_summary")
        ),

        reasoning=normalize_text(
            item.get("reasoning")
        ),

        full_text=normalize_text(
            item.get("full_text")
        ),
    )


# ============================================================
# 전체 법령 내부 조문
# ============================================================

def build_full_article(
    item: Dict[str, Any]
) -> FullArticleEvidence:

    return FullArticleEvidence(

        article_number=safe_int(
            item.get("article_number")
        ),

        sub_article_number=(
            safe_int(
                item.get(
                    "sub_article_number"
                ),
                0
            )
            or 0
        ),

        article_title=normalize_text(
            item.get("article_title")
        ),

        article_content=normalize_text(
            item.get("article_content")
        ),

        effective_date=normalize_text(
            item.get("effective_date")
        ),

        article_key=normalize_text(
            item.get("article_key")
        ),

        section_headers=list(
            item.get(
                "section_headers",
                []
            )
            or []
        ),

        paragraphs=list(
            item.get(
                "paragraphs",
                []
            )
            or []
        ),

        full_text=normalize_text(
            item.get("full_text")
        ),
    )


# ============================================================
# 전체 법령
# ============================================================

def build_full_law_evidence(
    data: Optional[Dict[str, Any]]
) -> Optional[FullLawEvidence]:

    if not data:
        return None

    if data.get("status") != "success":
        return None

    articles = [

        build_full_article(
            item
        )

        for item in data.get(
            "articles",
            []
        )

        if isinstance(
            item,
            dict
        )
    ]

    return FullLawEvidence(

        requested_law_name=normalize_text(
            data.get("requested_law_name")
        ),

        law_name=normalize_text(
            data.get("law_name")
        ),

        law_type=normalize_text(
            data.get("law_type")
        ),

        ministry=normalize_text(
            data.get("ministry")
        ),

        law_id=normalize_text(
            data.get("law_id")
        ),

        mst=normalize_text(
            data.get("mst")
        ),

        effective_date=normalize_text(
            data.get("effective_date")
        ),

        promulgation_date=normalize_text(
            data.get("promulgation_date")
        ),

        revision_type=normalize_text(
            data.get("revision_type")
        ),

        article_count=len(
            articles
        ),

        structure=list(
            data.get(
                "structure",
                []
            )
            or []
        ),

        articles=articles,
    )


# ============================================================
# 부칙
# ============================================================

def build_supplementary_evidence(
    item: Dict[str, Any]
) -> SupplementaryProvisionEvidence:

    return SupplementaryProvisionEvidence(

        source="법제처",

        law_name=normalize_text(
            item.get("law_name")
        ),

        promulgation_number=normalize_text(
            item.get("promulgation_number")
        ),

        promulgation_date=normalize_text(
            item.get("promulgation_date")
        ),

        title=normalize_text(
            item.get("title")
        ),

        text=normalize_text(
            item.get("text")
        ),
    )


# ============================================================
# 공식 법령 관계
# ============================================================

def build_related_law_evidence(
    item: Dict[str, Any]
) -> RelatedLawEvidence:

    return RelatedLawEvidence(

        relation_type=normalize_text(
            item.get("relation_type")
        ),

        source_law_name=normalize_text(
            item.get("source_law_name")
        ),

        target_law_name=normalize_text(
            item.get("target_law_name")
        ),

        target_law_id=normalize_text(
            item.get("target_law_id")
        ),

        target_mst=normalize_text(
            item.get("target_mst")
        ),

        target_law_type=normalize_text(
            item.get("target_law_type")
        ),

        ministry=normalize_text(
            item.get("ministry")
        ),

        article_reference=normalize_text(
            item.get("article_reference")
        ),

        description=normalize_text(
            item.get("description")
        ),

        official_link=normalize_text(
            item.get("official_link")
        ),

        retrieved_at=normalize_text(
            item.get("retrieved_at")
        ),
    )
