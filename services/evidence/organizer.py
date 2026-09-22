# ============================================================
# Evidence Organizer
#
# 역할:
#
# 1. Raw Evidence에서 주 법령을 확정한다.
# 2. 자연어 topic 질문은 법령 family 집중도를 이용한다.
# 3. query_service에서 이미 확정한 주 법령 정보는 보존한다.
# 4. 전체 법령(full_law)이 있으면 Legal Effect Analyzer 실행
# 5. 직접 근거 / 직접 미이행 효과 / 후속 불이익 /
#    조건부 제재 / 절차·정산을 구조화한다.
#
# 중요:
#
# - 새로운 법률 사실을 생성하지 않는다.
# - 특정 법령명을 하드코딩하지 않는다.
# - aiSearch 관련 조문과 공식 related_laws를 구분한다.
# - 법적 효과는 공식 full_law 원문만 분석한다.
# ============================================================

from dataclasses import (
    fields,
)

from typing import (
    Any,
    Dict,
    List,
    Optional,
    Type,
    TypeVar,
)


# ============================================================
# Evidence Models
# ============================================================

from models.evidence_law import (
    LawEvidence,
    LawCandidateEvidence,
    RelatedLawEvidence,
)

from models.evidence_organized import (
    OrganizedEvidence,
    PrimaryLawEvidence,
    OrganizedLegalBasis,
    LegalEffectGroup,
)


# ============================================================
# Legal Effect
# ============================================================

from services.evidence.legal_effect_analyzer import (
    analyze_legal_effects,
)

from services.evidence.legal_effect_classifier import (
    classify_effect_items,
)


# ============================================================
# Generic Dataclass Type
# ============================================================

T = TypeVar(
    "T"
)


# ============================================================
# 1. Organizer 설정
# ============================================================

TOPIC_PRIMARY_LIMIT = 3


# topic 질문 자동확정 최소 조건

MIN_ROOT_MATCHED_ARTICLES = 3

MIN_FAMILY_MATCHED_ARTICLES = 4

MIN_FAMILY_DOMINANCE = 0.70

MIN_ROOT_SHARE_IN_FAMILY = 0.50


# ============================================================
# 2. 법적 효과 Label
# ============================================================

LEGAL_EFFECT_LABELS = {

    "direct_consequence":
        "직접 미이행 효과",

    "downstream_consequence":
        "후속 불이익",

    "conditional_sanction":
        "조건부 별도 제재",

    "procedure_settlement":
        "절차·정산",

    "secondary_related":
        "기타 관련 효과",

    "related_effect":
        "관련 법적 효과",

    "unknown":
        "분류되지 않은 효과",
}


# ============================================================
# 3. 최종 핵심 답변에 포함할 Effect
#
# procedure_settlement은 내부 Evidence로 유지하지만
# consequence_basis 핵심 목록에서는 제외한다.
# ============================================================

CORE_CONSEQUENCE_CATEGORIES = {

    "direct_consequence",

    "downstream_consequence",

    "conditional_sanction",
}


# ============================================================
# 4. 기본 문자열 정리
# ============================================================

def clean_text(
    value: Any
) -> str:

    if value is None:

        return ""

    return str(
        value
    ).strip()


# ============================================================
# 5. 안전한 정수
# ============================================================

def safe_int(
    value: Any,
    default: int = 0
) -> int:

    try:

        return int(
            value
        )

    except (
        TypeError,
        ValueError,
    ):

        return default


# ============================================================
# 6. 안전한 실수
# ============================================================

def safe_float(
    value: Any
) -> Optional[float]:

    if value is None:

        return None

    try:

        return float(
            value
        )

    except (
        TypeError,
        ValueError,
    ):

        return None


# ============================================================
# 7. 비율
# ============================================================

def safe_ratio(
    numerator: int,
    denominator: int
) -> float:

    if denominator <= 0:

        return 0.0

    return (
        float(
            numerator
        )
        /
        float(
            denominator
        )
    )


# ============================================================
# 8. dict → dataclass 안전 변환
# ============================================================

def build_dataclass_from_dict(
    cls: Type[T],
    data: Any
) -> Optional[T]:

    if not isinstance(
        data,
        dict
    ):

        return None


    valid_fields = {

        item.name

        for item in fields(
            cls
        )
    }


    kwargs = {

        key: value

        for key, value in data.items()

        if key in valid_fields
    }


    try:

        return cls(
            **kwargs
        )

    except TypeError:

        return None


# ============================================================
# 9. 법령명 비교용 정규화
# ============================================================

def normalize_law_name(
    value: Any
) -> str:

    text = clean_text(
        value
    )

    return "".join(
        text.split()
    )


# ============================================================
# 10. 법령 family root
#
# 예:
#
# 어떤법
# 어떤법 시행령
# 어떤법 시행규칙
#
# → 어떤법
# ============================================================

def get_law_family_root(
    law_name: str
) -> str:

    law_name = clean_text(
        law_name
    )


    if not law_name:

        return ""


    subordinate_suffixes = (

        " 시행규칙",

        " 시행령",
    )


    for suffix in subordinate_suffixes:

        if law_name.endswith(
            suffix
        ):

            return law_name[
                :-len(
                    suffix
                )
            ].strip()


    return law_name


# ============================================================
# 11. 법령 후보 복원
# ============================================================

def build_law_candidates(
    evidence_result: Dict[
        str,
        Any
    ]
) -> List[
    LawCandidateEvidence
]:

    raw_candidates = evidence_result.get(
        "law_candidates",
        []
    )


    if not isinstance(
        raw_candidates,
        list
    ):

        return []


    results = []


    for item in raw_candidates:

        candidate = build_dataclass_from_dict(

            LawCandidateEvidence,

            item
        )


        if candidate is None:

            continue


        if not clean_text(
            candidate.law_name
        ):

            continue


        results.append(
            candidate
        )


    results.sort(

        key=lambda item: (

            item.rank
            if item.rank is not None
            else 999999,

            -safe_int(
                item.matched_article_count
            ),
        )
    )


    return results


# ============================================================
# 12. 공식 related_laws 복원
# ============================================================

def build_related_laws(
    evidence_result: Dict[
        str,
        Any
    ]
) -> List[
    RelatedLawEvidence
]:

    raw_items = evidence_result.get(
        "related_laws",
        []
    )


    if not isinstance(
        raw_items,
        list
    ):

        return []


    results = []


    for item in raw_items:

        related_law = build_dataclass_from_dict(

            RelatedLawEvidence,

            item
        )


        if related_law is None:

            continue


        if not clean_text(
            related_law.target_law_name
        ):

            continue


        results.append(
            related_law
        )


    return results


# ============================================================
# 13. resolved 법령 정보
#
# basic_info → 우선
# full_law → 보조
# ============================================================

def get_resolved_law_info(
    evidence_result: Dict[
        str,
        Any
    ]
) -> Optional[
    Dict[str, Any]
]:

    # ========================================================
    # A. 기본정보
    # ========================================================

    basic_info = evidence_result.get(
        "basic_info"
    )


    if isinstance(
        basic_info,
        dict
    ):

        law_name = clean_text(
            basic_info.get(
                "law_name"
            )
        )


        if law_name:

            return {

                "law_name":
                    law_name,

                "law_type":
                    clean_text(
                        basic_info.get(
                            "law_type"
                        )
                    ),

                "ministry":
                    clean_text(
                        basic_info.get(
                            "ministry"
                        )
                    ),

                "law_id":
                    clean_text(
                        basic_info.get(
                            "law_id"
                        )
                    ),

                "mst":
                    clean_text(
                        basic_info.get(
                            "mst"
                        )
                    ),

                "source":
                    "basic_info",
            }


    # ========================================================
    # B. 전체 법령
    # ========================================================

    full_law = evidence_result.get(
        "full_law"
    )


    if isinstance(
        full_law,
        dict
    ):

        law_name = clean_text(
            full_law.get(
                "law_name"
            )
        )


        if law_name:

            return {

                "law_name":
                    law_name,

                "law_type":
                    clean_text(
                        full_law.get(
                            "law_type"
                        )
                    ),

                "ministry":
                    clean_text(
                        full_law.get(
                            "ministry"
                        )
                    ),

                "law_id":
                    clean_text(
                        full_law.get(
                            "law_id"
                        )
                    ),

                "mst":
                    clean_text(
                        full_law.get(
                            "mst"
                        )
                    ),

                "source":
                    "full_law",
            }


    return None


# ============================================================
# 14. 동일 법령 Candidate
# ============================================================

def find_matching_candidate(
    resolved_law_name: str,
    candidates: List[
        LawCandidateEvidence
    ]
) -> Optional[
    LawCandidateEvidence
]:

    target = normalize_law_name(
        resolved_law_name
    )


    if not target:

        return None


    for candidate in candidates:

        candidate_name = normalize_law_name(
            candidate.law_name
        )


        if (
            candidate_name
            and
            candidate_name == target
        ):

            return candidate


    return None


# ============================================================
# 15. query_service가 이미 확정한 Primary 보존
#
# 중요:
#
# 자연어 topic 질문은 query_service에서
# topic_family_confirmed로 확정된 뒤 full_law가 붙는다.
#
# 그 상태에서 Organizer를 다시 실행하면
# full_law 때문에 "resolved"로 바뀌면 안 된다.
# ============================================================

def get_preserved_primary_result(
    evidence_result: Dict[
        str,
        Any
    ],
    candidates: List[
        LawCandidateEvidence
    ]
) -> Optional[
    Dict[str, Any]
]:

    metadata = evidence_result.get(
        "metadata",
        {}
    )


    if not isinstance(
        metadata,
        dict
    ):

        return None


    confirmed = bool(
        metadata.get(
            "primary_law_confirmed"
        )
    )


    if not confirmed:

        return None


    law_name = clean_text(
        metadata.get(
            "primary_law_name"
        )
    )


    if not law_name:

        return None


    selection_mode = clean_text(
        metadata.get(
            "primary_law_selection_mode"
        )
        or
        metadata.get(
            "selection_mode"
        )
    )


    if selection_mode not in {

        "resolved",

        "topic_family_confirmed",

    }:

        return None


    candidate = find_matching_candidate(

        resolved_law_name=law_name,

        candidates=candidates,
    )


    law_type = ""

    ministry = ""

    law_id = clean_text(
        metadata.get(
            "primary_law_id"
        )
    )

    mst = clean_text(
        metadata.get(
            "primary_law_mst"
        )
    )


    if candidate is not None:

        law_type = clean_text(
            candidate.law_type
        )

        ministry = clean_text(
            candidate.ministry
        )

        if not law_id:

            law_id = clean_text(
                candidate.law_id
            )

        if not mst:

            mst = clean_text(
                candidate.mst
            )


    # full_law metadata로 보완

    full_law = evidence_result.get(
        "full_law"
    )


    if isinstance(
        full_law,
        dict
    ):

        if not law_type:

            law_type = clean_text(
                full_law.get(
                    "law_type"
                )
            )

        if not ministry:

            ministry = clean_text(
                full_law.get(
                    "ministry"
                )
            )

        if not law_id:

            law_id = clean_text(
                full_law.get(
                    "law_id"
                )
            )

        if not mst:

            mst = clean_text(
                full_law.get(
                    "mst"
                )
            )


    confidence = safe_float(
        metadata.get(
            "primary_law_confidence"
        )
    )


    if confidence is None:

        confidence = (
            1.0
            if selection_mode == "resolved"
            else None
        )


    primary_law = PrimaryLawEvidence(

        law_name=law_name,

        law_type=law_type,

        ministry=ministry,

        law_id=law_id,

        mst=mst,

        confidence=confidence,

        matched_article_count=(
            safe_int(
                candidate.matched_article_count
            )
            if candidate is not None
            else 0
        ),

        rank=(
            candidate.rank
            if candidate is not None
            else None
        ),

        selection_reason=(
            "query_service에서 이미 확정한 "
            "주 법령 선택 결과를 유지합니다."
        ),

        is_confirmed=True,

        candidate=candidate,
    )


    family_evaluation = None


    if selection_mode == "topic_family_confirmed":

        family_evaluation = {

            "confirmed":
                True,

            "root_name":
                clean_text(
                    metadata.get(
                        "family_root"
                    )
                    or
                    law_name
                ),

            "family_count":
                safe_int(
                    metadata.get(
                        "family_matched_article_count"
                    )
                ),

            "root_count":
                safe_int(
                    metadata.get(
                        "primary_law_matched_article_count"
                    )
                    or
                    (
                        candidate.matched_article_count
                        if candidate is not None
                        else 0
                    )
                ),

            "total_count":
                safe_int(
                    metadata.get(
                        "family_total_candidate_articles"
                    )
                ),

            "family_dominance":
                safe_float(
                    metadata.get(
                        "family_dominance"
                    )
                )
                or 0.0,

            "root_share":
                safe_float(
                    metadata.get(
                        "root_share_in_family"
                    )
                )
                or 0.0,

            "family_member_count":
                safe_int(
                    metadata.get(
                        "family_member_count"
                    )
                ),
        }


    return {

        "primary_laws": [
            primary_law
        ],

        "confirmed":
            True,

        "ambiguous":
            False,

        "selection_mode":
            selection_mode,

        "family_evaluation":
            family_evaluation,

        "preserved":
            True,
    }


# ============================================================
# 16. resolved Primary 생성
# ============================================================

def build_confirmed_primary_law(
    resolved_info: Dict[
        str,
        Any
    ],
    candidate: Optional[
        LawCandidateEvidence
    ] = None,
    confidence: float = 1.0,
    selection_reason: str = ""
) -> PrimaryLawEvidence:

    matched_article_count = 0

    rank = None


    if candidate is not None:

        matched_article_count = safe_int(
            candidate.matched_article_count
        )

        rank = candidate.rank


    if not selection_reason:

        selection_reason = (
            "공식 법령 검색에서 특정 법령으로 "
            "resolve되어 기본정보 또는 전체 법령이 "
            "확인되었습니다."
        )


    return PrimaryLawEvidence(

        law_name=clean_text(
            resolved_info.get(
                "law_name"
            )
        ),

        law_type=clean_text(
            resolved_info.get(
                "law_type"
            )
        ),

        ministry=clean_text(
            resolved_info.get(
                "ministry"
            )
        ),

        law_id=clean_text(
            resolved_info.get(
                "law_id"
            )
        ),

        mst=clean_text(
            resolved_info.get(
                "mst"
            )
        ),

        confidence=confidence,

        matched_article_count=(
            matched_article_count
        ),

        rank=rank,

        selection_reason=(
            selection_reason
        ),

        is_confirmed=True,

        candidate=candidate,
    )


# ============================================================
# 17. topic Primary Candidates
# ============================================================

def build_topic_primary_candidates(
    candidates: List[
        LawCandidateEvidence
    ],
    limit: int = TOPIC_PRIMARY_LIMIT
) -> List[
    PrimaryLawEvidence
]:

    results = []


    for candidate in candidates[
        :limit
    ]:

        results.append(

            PrimaryLawEvidence(

                law_name=clean_text(
                    candidate.law_name
                ),

                law_type=clean_text(
                    candidate.law_type
                ),

                ministry=clean_text(
                    candidate.ministry
                ),

                law_id=clean_text(
                    candidate.law_id
                ),

                mst=clean_text(
                    candidate.mst
                ),

                confidence=None,

                matched_article_count=(
                    safe_int(
                        candidate.matched_article_count
                    )
                ),

                rank=candidate.rank,

                selection_reason=(
                    "자연어 질문의 aiSearch 결과에서 "
                    "관련 조문이 확인된 주 법령 후보입니다. "
                    "아직 자동 확정하지 않았습니다."
                ),

                is_confirmed=False,

                candidate=candidate,
            )
        )


    return results


# ============================================================
# 18. 법령 Family 구성
# ============================================================

def group_law_families(
    candidates: List[
        LawCandidateEvidence
    ]
) -> Dict[
    str,
    Dict[str, Any]
]:

    families = {}


    for candidate in candidates:

        law_name = clean_text(
            candidate.law_name
        )


        if not law_name:

            continue


        root_name = get_law_family_root(
            law_name
        )


        root_key = normalize_law_name(
            root_name
        )


        if not root_key:

            continue


        if root_key not in families:

            families[
                root_key
            ] = {

                "root_name":
                    root_name,

                "items":
                    [],

                "matched_article_count":
                    0,

                "root_candidate":
                    None,
            }


        family = families[
            root_key
        ]


        family[
            "items"
        ].append(
            candidate
        )


        family[
            "matched_article_count"
        ] += safe_int(
            candidate.matched_article_count
        )


        if (
            normalize_law_name(
                law_name
            )
            ==
            normalize_law_name(
                root_name
            )
        ):

            family[
                "root_candidate"
            ] = candidate


    return families


# ============================================================
# 19. Family Ranking
# ============================================================

def rank_law_families(
    families: Dict[
        str,
        Dict[str, Any]
    ]
) -> List[
    Dict[str, Any]
]:

    results = list(
        families.values()
    )


    def get_best_rank(
        family: Dict[
            str,
            Any
        ]
    ) -> int:

        ranks = [

            candidate.rank

            for candidate in family.get(
                "items",
                []
            )

            if candidate.rank is not None
        ]


        if not ranks:

            return 999999


        return min(
            ranks
        )


    results.sort(

        key=lambda family: (

            -safe_int(
                family.get(
                    "matched_article_count"
                )
            ),

            get_best_rank(
                family
            ),
        )
    )


    return results


# ============================================================
# 20. Topic Family 자동확정
# ============================================================

def evaluate_topic_family_confirmation(
    candidates: List[
        LawCandidateEvidence
    ]
) -> Optional[
    Dict[str, Any]
]:

    if not candidates:

        return None


    families = group_law_families(
        candidates
    )


    ranked_families = rank_law_families(
        families
    )


    if not ranked_families:

        return None


    top_family = ranked_families[
        0
    ]


    root_candidate = top_family.get(
        "root_candidate"
    )


    if root_candidate is None:

        return None


    root_count = safe_int(
        root_candidate.matched_article_count
    )


    family_count = safe_int(
        top_family.get(
            "matched_article_count"
        )
    )


    total_count = sum(

        safe_int(
            candidate.matched_article_count
        )

        for candidate in candidates
    )


    family_dominance = safe_ratio(

        family_count,

        total_count
    )


    root_share = safe_ratio(

        root_count,

        family_count
    )


    root_rank = (
        root_candidate.rank
        if root_candidate.rank is not None
        else 999999
    )


    family_items = top_family.get(
        "items",
        []
    )


    family_member_count = len(
        family_items
    )


    family_count_confirmed = all(
        [

            root_count
            >=
            2,

            family_count
            >=
            MIN_FAMILY_MATCHED_ARTICLES,

            family_dominance
            >=
            MIN_FAMILY_DOMINANCE,

            root_share
            >=
            MIN_ROOT_SHARE_IN_FAMILY,
        ]
    )


    single_root_confirmed = all(
        [

            len(
                ranked_families
            )
            == 1,

            family_member_count
            == 1,

            root_rank
            == 1,

            root_count
            >=
            2,

            family_dominance
            >=
            0.95,
        ]
    )


    confirmed = bool(
        family_count_confirmed
        or
        single_root_confirmed
    )


    if family_count_confirmed:

        confirmation_mode = (
            "family_root_supported"
        )

    elif single_root_confirmed:

        confirmation_mode = (
            "single_root_supported"
        )

    else:

        confirmation_mode = (
            "insufficient"
        )


    return {

        "confirmed":
            confirmed,

        "confirmation_mode":
            confirmation_mode,

        "root_candidate":
            root_candidate,

        "root_name":
            top_family.get(
                "root_name",
                ""
            ),

        "family_count":
            family_count,

        "root_count":
            root_count,

        "total_count":
            total_count,

        "family_dominance":
            family_dominance,

        "root_share":
            root_share,

        "family_member_count":
            family_member_count,
    }


# ============================================================
# 21. Topic Family Confirmed Primary
# ============================================================

def build_topic_confirmed_primary_law(
    evaluation: Dict[
        str,
        Any
    ]
) -> PrimaryLawEvidence:

    candidate = evaluation[
        "root_candidate"
    ]


    family_dominance = float(
        evaluation.get(
            "family_dominance",
            0.0
        )
    )


    confirmation_mode = clean_text(
        evaluation.get(
            "confirmation_mode"
        )
    )


    selection_reason = (

        "자연어 질문의 관련 조문이 하나의 법령 체계에 "
        "집중되어 주 법령으로 자동 확정되었습니다. "

        f"확정 방식 {confirmation_mode or 'family_evidence'}, "

        f"본법 관련 조문 "
        f"{evaluation.get('root_count', 0)}건, "

        f"동일 법령 family 전체 "
        f"{evaluation.get('family_count', 0)}건, "

        f"전체 후보 대비 family 비중 "
        f"{family_dominance:.1%}입니다."
    )


    return PrimaryLawEvidence(

        law_name=clean_text(
            candidate.law_name
        ),

        law_type=clean_text(
            candidate.law_type
        ),

        ministry=clean_text(
            candidate.ministry
        ),

        law_id=clean_text(
            candidate.law_id
        ),

        mst=clean_text(
            candidate.mst
        ),

        confidence=(
            family_dominance
        ),

        matched_article_count=(
            safe_int(
                candidate.matched_article_count
            )
        ),

        rank=candidate.rank,

        selection_reason=(
            selection_reason
        ),

        is_confirmed=True,

        candidate=candidate,
    )


# ============================================================
# 22. Primary Law 전체 구성
# ============================================================

def organize_primary_laws(
    evidence_result: Dict[
        str,
        Any
    ]
) -> Dict[
    str,
    Any
]:

    candidates = build_law_candidates(
        evidence_result
    )


    # ========================================================
    # A. query_service에서 이미 확정한 선택 결과 보존
    # ========================================================

    preserved = get_preserved_primary_result(

        evidence_result=evidence_result,

        candidates=candidates,
    )


    if preserved is not None:

        return preserved


    # ========================================================
    # B. Resolver가 정확한 법령으로 resolve
    # ========================================================

    resolved_info = get_resolved_law_info(
        evidence_result
    )


    if resolved_info:

        matching_candidate = (
            find_matching_candidate(

                resolved_law_name=(
                    resolved_info[
                        "law_name"
                    ]
                ),

                candidates=candidates,
            )
        )


        primary_law = (
            build_confirmed_primary_law(

                resolved_info=resolved_info,

                candidate=matching_candidate,

                confidence=1.0,

                selection_reason=(
                    "공식 법령 검색에서 특정 법령으로 "
                    "resolve되어 기본정보 또는 전체 법령이 "
                    "확인되었습니다."
                ),
            )
        )


        return {

            "primary_laws": [
                primary_law
            ],

            "confirmed":
                True,

            "ambiguous":
                False,

            "selection_mode":
                "resolved",

            "family_evaluation":
                None,

            "preserved":
                False,
        }


    # ========================================================
    # C. 자연어 Topic Family
    # ========================================================

    family_evaluation = (
        evaluate_topic_family_confirmation(
            candidates
        )
    )


    if (
        family_evaluation
        and
        family_evaluation.get(
            "confirmed"
        )
    ):

        primary_law = (
            build_topic_confirmed_primary_law(
                family_evaluation
            )
        )


        return {

            "primary_laws": [
                primary_law
            ],

            "confirmed":
                True,

            "ambiguous":
                False,

            "selection_mode":
                "topic_family_confirmed",

            "family_evaluation":
                family_evaluation,

            "preserved":
                False,
        }


    # ========================================================
    # D. 아직 자동확정 불가
    # ========================================================

    topic_candidates = (
        build_topic_primary_candidates(
            candidates
        )
    )


    return {

        "primary_laws":
            topic_candidates,

        "confirmed":
            False,

        "ambiguous":
            len(
                topic_candidates
            ) > 1,

        "selection_mode":
            (
                "topic_candidates"
                if topic_candidates
                else "none"
            ),

        "family_evaluation":
            family_evaluation,

        "preserved":
            False,
    }


# ============================================================
# 23. Analyzer Article → LawEvidence
#
# full_law 원문 조문을 OrganizedLegalBasis에 넣기 위한 변환.
# ============================================================

def build_law_evidence_from_full_article(
    article: Dict[
        str,
        Any
    ],
    full_law: Dict[
        str,
        Any
    ],
    relevance_score: Optional[float] = None
) -> Optional[
    LawEvidence
]:

    if not isinstance(
        article,
        dict
    ):

        return None


    article_number = article.get(
        "article_number"
    )


    if article_number is None:

        return None


    return LawEvidence(

        source=clean_text(
            full_law.get(
                "source"
            )
            or
            "법제처"
        ),

        law_name=clean_text(
            full_law.get(
                "law_name"
            )
        ),

        law_type=clean_text(
            full_law.get(
                "law_type"
            )
        ),

        ministry=clean_text(
            full_law.get(
                "ministry"
            )
        ),

        law_id=clean_text(
            full_law.get(
                "law_id"
            )
        ),

        mst=clean_text(
            full_law.get(
                "mst"
            )
        ),

        article_number=(
            safe_int(
                article_number,
                0
            )
        ),

        sub_article_number=(
            safe_int(
                article.get(
                    "sub_article_number",
                    0
                ),
                0
            )
        ),

        article_title=clean_text(
            article.get(
                "article_title"
            )
        ),

        article_text=clean_text(
            article.get(
                "full_text"
            )
            or
            article.get(
                "article_content"
            )
        ),

        effective_date=clean_text(
            article.get(
                "effective_date"
            )
            or
            full_law.get(
                "effective_date"
            )
        ),

        promulgation_date=clean_text(
            full_law.get(
                "promulgation_date"
            )
        ),

        revision_type=clean_text(
            full_law.get(
                "revision_type"
            )
        ),

        relevance_score=(
            relevance_score
        ),

        query_coverage=None,

        matched_tokens=[],

        original_rank=None,

        final_rank=None,

        official_link=clean_text(
            full_law.get(
                "official_link"
            )
        ),

        retrieved_at=clean_text(
            full_law.get(
                "retrieved_at"
            )
        ),
    )


# ============================================================
# 24. Direct Basis 구조화
# ============================================================

def build_direct_basis(
    analyzer_result: Dict[
        str,
        Any
    ],
    full_law: Dict[
        str,
        Any
    ]
) -> List[
    OrganizedLegalBasis
]:

    raw_items = analyzer_result.get(
        "direct_anchors",
        []
    )


    if not isinstance(
        raw_items,
        list
    ):

        return []


    results = []


    for item in raw_items:

        if not isinstance(
            item,
            dict
        ):

            continue


        article = item.get(
            "article",
            {}
        )


        evidence = (
            build_law_evidence_from_full_article(

                article=article,

                full_law=full_law,

                relevance_score=safe_float(
                    item.get(
                        "score"
                    )
                ),
            )
        )


        if evidence is None:

            continue


        roles = item.get(
            "roles",
            []
        )


        if not isinstance(
            roles,
            list
        ):

            roles = []


        role_text = (
            roles[
                0
            ]
            if roles
            else "직접근거"
        )


        basis = build_dataclass_from_dict(

            OrganizedLegalBasis,

            {

                "role":
                    "direct_basis",

                "effect_type":
                    role_text,

                "relevance_score":
                    safe_float(
                        item.get(
                            "score"
                        )
                    ),

                "reason":
                    (
                        "사용자 질문의 주체·행위와 "
                        "직접 연결되는 핵심 규범 조문입니다."
                    ),

                "evidence":
                    evidence,
            }
        )


        if basis is not None:

            results.append(
                basis
            )


    return results


# ============================================================
# 25. Classified Effect → OrganizedLegalBasis
# ============================================================

def build_effect_basis(
    classified_item: Dict[
        str,
        Any
    ],
    full_law: Dict[
        str,
        Any
    ]
) -> Optional[
    OrganizedLegalBasis
]:

    if not isinstance(
        classified_item,
        dict
    ):

        return None


    article = classified_item.get(
        "article",
        {}
    )


    category = clean_text(
        classified_item.get(
            "effect_category"
        )
        or
        "related_effect"
    )


    evidence = (
        build_law_evidence_from_full_article(

            article=article,

            full_law=full_law,

            relevance_score=safe_float(
                classified_item.get(
                    "score"
                )
            ),
        )
    )


    if evidence is None:

        return None


    return build_dataclass_from_dict(

        OrganizedLegalBasis,

        {

            "role":
                category,

            "effect_type":
                category,

            "relevance_score":
                safe_float(
                    classified_item.get(
                        "score"
                    )
                ),

            "reason":
                clean_text(
                    classified_item.get(
                        "effect_reason"
                    )
                ),

            "evidence":
                evidence,
        }
    )


# ============================================================
# 26. Consequence Basis
#
# 최종 핵심 답변에 사용:
#
# direct_consequence
# downstream_consequence
# conditional_sanction
#
# 절차/정산은 제외한다.
# ============================================================

def build_consequence_basis(
    classified_items: List[
        Dict[
            str,
            Any
        ]
    ],
    full_law: Dict[
        str,
        Any
    ]
) -> List[
    OrganizedLegalBasis
]:

    results = []


    for item in classified_items:

        category = clean_text(
            item.get(
                "effect_category"
            )
        )


        if category not in CORE_CONSEQUENCE_CATEGORIES:

            continue


        basis = build_effect_basis(

            classified_item=item,

            full_law=full_law,
        )


        if basis is not None:

            results.append(
                basis
            )


    return results


# ============================================================
# 27. Legal Effect Group
#
# procedure_settlement도 여기에는 유지한다.
# ============================================================

def build_legal_effect_groups(
    classified_items: List[
        Dict[
            str,
            Any
        ]
    ],
    full_law: Dict[
        str,
        Any
    ]
) -> List[
    LegalEffectGroup
]:

    grouped = {}


    for item in classified_items:

        category = clean_text(
            item.get(
                "effect_category"
            )
            or
            "unknown"
        )


        basis = build_effect_basis(

            classified_item=item,

            full_law=full_law,
        )


        if basis is None:

            continue


        grouped.setdefault(
            category,
            []
        ).append(
            basis
        )


    results = []


    preferred_order = [

        "direct_consequence",

        "downstream_consequence",

        "conditional_sanction",

        "procedure_settlement",

        "secondary_related",

        "related_effect",

        "unknown",
    ]


    remaining = [

        category

        for category in grouped.keys()

        if category not in preferred_order
    ]


    ordered_categories = (
        preferred_order
        +
        remaining
    )


    for category in ordered_categories:

        items = grouped.get(
            category,
            []
        )


        if not items:

            continue


        group = build_dataclass_from_dict(

            LegalEffectGroup,

            {

                "effect_type":
                    category,

                "label":
                    LEGAL_EFFECT_LABELS.get(
                        category,
                        category
                    ),

                "evidence_count":
                    len(
                        items
                    ),

                "items":
                    items,
            }
        )


        if group is not None:

            results.append(
                group
            )


    return results


# ============================================================
# 28. Issue Types
# ============================================================

def build_issue_types(
    direct_basis: List[
        OrganizedLegalBasis
    ],
    classified_items: List[
        Dict[
            str,
            Any
        ]
    ]
) -> List[str]:

    results = []


    for item in direct_basis:

        effect_type = clean_text(
            getattr(
                item,
                "effect_type",
                ""
            )
        )


        if (
            effect_type
            and
            effect_type not in results
        ):

            results.append(
                effect_type
            )


    for item in classified_items:

        category = clean_text(
            item.get(
                "effect_category"
            )
        )


        if (
            category
            and
            category not in results
        ):

            results.append(
                category
            )


    return results


# ============================================================
# 29. Legal Effect 전체 실행
# ============================================================

def organize_legal_effects(
    evidence_result: Dict[
        str,
        Any
    ],
    primary_result: Dict[
        str,
        Any
    ]
) -> Dict[
    str,
    Any
]:

    empty_result = {

        "status":
            "skipped",

        "direct_basis":
            [],

        "consequence_basis":
            [],

        "legal_effects":
            [],

        "classified_items":
            [],

        "issue_types":
            [],

        "analyzer_result":
            None,

        "message":
            "",
    }


    # ========================================================
    # A. 주 법령 미확정
    # ========================================================

    if not primary_result.get(
        "confirmed"
    ):

        empty_result[
            "message"
        ] = "주 법령이 확정되지 않아 법적 효과 분석을 생략했습니다."

        return empty_result


    primary_laws = primary_result.get(
        "primary_laws",
        []
    )


    if not primary_laws:

        empty_result[
            "message"
        ] = "주 법령 정보가 없습니다."

        return empty_result


    primary_law = primary_laws[
        0
    ]


    # ========================================================
    # B. Full Law 필요
    # ========================================================

    full_law = evidence_result.get(
        "full_law"
    )


    if not isinstance(
        full_law,
        dict
    ):

        empty_result[
            "message"
        ] = "전체 법령 원문이 없어 법적 효과 분석을 생략했습니다."

        return empty_result


    if not full_law.get(
        "articles"
    ):

        empty_result[
            "message"
        ] = "전체 법령 조문이 비어 있습니다."

        return empty_result


    # ========================================================
    # C. aiSearch Seed
    # ========================================================

    seed_laws = evidence_result.get(
        "laws",
        []
    )


    if not isinstance(
        seed_laws,
        list
    ):

        seed_laws = []


    # ========================================================
    # D. Analyzer
    # ========================================================

    try:

        analyzer_result = analyze_legal_effects(

            question=clean_text(
                evidence_result.get(
                    "original_question"
                )
            ),

            full_law=full_law,

            seed_laws=seed_laws,

            primary_law_name=clean_text(
                primary_law.law_name
            ),
        )

    except Exception:

        empty_result[
            "status"
        ] = "error"

        empty_result[
            "message"
        ] = "법적 효과 분석 중 오류가 발생했습니다."

        return empty_result


    if analyzer_result.get(
        "status"
    ) != "success":

        empty_result[
            "status"
        ] = "error"

        empty_result[
            "message"
        ] = "법적 효과 분석 결과가 정상적이지 않습니다."

        return empty_result


    # ========================================================
    # E. Classifier
    # ========================================================

    classified_items = classify_effect_items(

        analyzer_result.get(
            "consequence_basis",
            []
        )
    )


    # ========================================================
    # F. Organized Models
    # ========================================================

    direct_basis = build_direct_basis(

        analyzer_result=analyzer_result,

        full_law=full_law,
    )


    consequence_basis = (
        build_consequence_basis(

            classified_items=classified_items,

            full_law=full_law,
        )
    )


    legal_effects = build_legal_effect_groups(

        classified_items=classified_items,

        full_law=full_law,
    )


    issue_types = build_issue_types(

        direct_basis=direct_basis,

        classified_items=classified_items,
    )


    return {

        "status":
            "success",

        "direct_basis":
            direct_basis,

        "consequence_basis":
            consequence_basis,

        "legal_effects":
            legal_effects,

        "classified_items":
            classified_items,

        "issue_types":
            issue_types,

        "analyzer_result":
            analyzer_result,

        "message":
            "법적 효과 구조화가 완료되었습니다.",
    }


# ============================================================
# 30. 최종 Organizer
# ============================================================

def organize_evidence(
    evidence_result: Dict[
        str,
        Any
    ]
) -> OrganizedEvidence:

    if not isinstance(
        evidence_result,
        dict
    ):

        return OrganizedEvidence(

            status="error",

            message=(
                "Evidence 입력 형식이 올바르지 않습니다."
            ),
        )


    original_question = clean_text(

        evidence_result.get(
            "original_question"
        )
    )


    search_query = clean_text(

        evidence_result.get(
            "search_query"
        )
    )


    candidates = build_law_candidates(
        evidence_result
    )


    # ========================================================
    # Primary Law
    # ========================================================

    primary_result = organize_primary_laws(
        evidence_result
    )


    # ========================================================
    # Official Related Laws
    # ========================================================

    related_laws = build_related_laws(
        evidence_result
    )


    # ========================================================
    # Legal Effects
    # ========================================================

    legal_result = organize_legal_effects(

        evidence_result=evidence_result,

        primary_result=primary_result,
    )


    # ========================================================
    # Metadata
    # ========================================================

    family_evaluation = (
        primary_result.get(
            "family_evaluation"
        )
    )


    organizer_metadata = {

        "organizer_stage":
            (
                "legal_effect_organization"
                if legal_result.get(
                    "status"
                )
                == "success"
                else "primary_law_selection"
            ),

        "selection_mode":
            primary_result[
                "selection_mode"
            ],

        "primary_selection_preserved":
            bool(
                primary_result.get(
                    "preserved"
                )
            ),

        "law_candidate_count":
            len(
                candidates
            ),

        "related_law_count":
            len(
                related_laws
            ),

        "legal_effect_status":
            legal_result.get(
                "status"
            ),

        "direct_basis_count":
            len(
                legal_result.get(
                    "direct_basis",
                    []
                )
            ),

        "consequence_basis_count":
            len(
                legal_result.get(
                    "consequence_basis",
                    []
                )
            ),

        "legal_effect_group_count":
            len(
                legal_result.get(
                    "legal_effects",
                    []
                )
            ),
    }


    # ========================================================
    # Family Metadata
    # ========================================================

    if family_evaluation:

        organizer_metadata[
            "family_root"
        ] = clean_text(
            family_evaluation.get(
                "root_name"
            )
        )


        organizer_metadata[
            "family_matched_article_count"
        ] = safe_int(
            family_evaluation.get(
                "family_count"
            )
        )


        organizer_metadata[
            "family_total_candidate_articles"
        ] = safe_int(
            family_evaluation.get(
                "total_count"
            )
        )


        organizer_metadata[
            "family_dominance"
        ] = float(
            family_evaluation.get(
                "family_dominance",
                0.0
            )
        )


        organizer_metadata[
            "root_share_in_family"
        ] = float(
            family_evaluation.get(
                "root_share",
                0.0
            )
        )


        organizer_metadata[
            "family_member_count"
        ] = safe_int(
            family_evaluation.get(
                "family_member_count"
            )
        )


    # ========================================================
    # Legal Analyzer 내부 Count
    # ========================================================

    analyzer_result = legal_result.get(
        "analyzer_result"
    )


    if isinstance(
        analyzer_result,
        dict
    ):

        organizer_metadata[
            "legal_direct_anchor_count"
        ] = safe_int(
            analyzer_result.get(
                "direct_anchor_count"
            )
        )


        organizer_metadata[
            "legal_first_level_count"
        ] = safe_int(
            analyzer_result.get(
                "first_level_count"
            )
        )


        organizer_metadata[
            "legal_second_level_count"
        ] = safe_int(
            analyzer_result.get(
                "second_level_count"
            )
        )


    # ========================================================
    # Final OrganizedEvidence
    # ========================================================

    organized = OrganizedEvidence(

        status="success",

        original_question=(
            original_question
        ),

        search_query=(
            search_query
        ),

        issue_types=(
            legal_result.get(
                "issue_types",
                []
            )
        ),

        primary_laws=(
            primary_result[
                "primary_laws"
            ]
        ),

        primary_law_confirmed=bool(
            primary_result[
                "confirmed"
            ]
        ),

        ambiguous=bool(
            primary_result[
                "ambiguous"
            ]
        ),

        direct_basis=(
            legal_result.get(
                "direct_basis",
                []
            )
        ),

        consequence_basis=(
            legal_result.get(
                "consequence_basis",
                []
            )
        ),

        legal_effects=(
            legal_result.get(
                "legal_effects",
                []
            )
        ),

        related_laws=(
            related_laws
        ),

        metadata=(
            organizer_metadata
        ),

        message=(
            legal_result.get(
                "message"
            )
            or
            "주 법령 구조화가 완료되었습니다."
        ),
    )


    return organized


# ============================================================
# 31. dict 반환 Helper
# ============================================================

def organize_evidence_to_dict(
    evidence_result: Dict[
        str,
        Any
    ]
) -> Dict[
    str,
    Any
]:

    return organize_evidence(
        evidence_result
    ).to_dict()