# ============================================================
# Legal Effect Direct Score
#
# 사용자 질문 ↔ 조문 간 직접 연결 점수 계산.
# 기존 점수/조건/quality gate 로직은 변경하지 않는다.
# ============================================================

from typing import (
    Any,
    Dict,
    Tuple,
)

from services.evidence.question_action_matcher import (
    score_question_connection,
)

from services.evidence.legal_effect_direct_search_context import (
    build_seed_search_context,
    score_seed_search_context,
)

from services.evidence.legal_effect_seed_bridge import (
    LOCAL_SEED_MAX_DISTANCE,
    LOCAL_SEED_MAX_RANK,
    find_local_seed_bridge,
    has_bridge_exception,
)

from services.evidence.legal_effect_utils import (
    clean_text,
    safe_int,
    make_article_key,
    extract_question_tokens,
    extract_question_roles,
    get_article_text,
    get_article_lead_text,
    count_matches,
    detect_title_roles,
    detect_normative_roles,
    detect_effect_types,
    has_strong_consequence_signal,
    has_subject_conflict,
)

def score_direct_article(
    article: Dict[str, Any],
    question: str,
    seed_map: Dict[
        str,
        Dict[str, Any]
    ]
) -> Tuple[
    float,
    Dict[str, Any]
]:

    title = clean_text(
        article.get(
            "article_title"
        )
    )

    lead_text = get_article_lead_text(
        article
    )

    if not title and not lead_text:

        return (
            -1.0,
            {},
        )

    question_tokens = extract_question_tokens(
        question
    )

    question_roles = extract_question_roles(
        question
    )

    title_roles = detect_title_roles(
        title
    )

    normative_roles = detect_normative_roles(
        lead_text
    )

    title_topic_matches = count_matches(
        question_tokens,
        title
    )

    lead_topic_matches = count_matches(
        question_tokens,
        lead_text
    )

    title_role_matches = count_matches(
        question_roles,
        title
    )

    lead_role_matches = count_matches(
        question_roles,
        lead_text
    )

    # ========================================================
    # 질문의 핵심 행위 / 객체 연결도
    #
    # 예:
    #
    # 특허 침해
    # → action = 침해
    # → object = 특허
    #
    # 개인정보 수집
    # → action = 수집
    # → object = 개인정보 / 동의
    #
    # 특정 법률명이나 조문번호는 사용하지 않는다.
    # ========================================================

    question_connection = score_question_connection(

        question=question,

        title=title,

        body=lead_text,
    )

    action_token = clean_text(
        question_connection.get(
            "action_token"
        )
    )

    object_tokens = (
        question_connection.get(
            "object_tokens",
            []
        )
        or
        []
    )

    action_match = bool(
        question_connection.get(
            "action_match"
        )
    )

    title_action_match = bool(
        question_connection.get(
            "title_action_match"
        )
    )

    body_action_match = bool(
        question_connection.get(
            "body_action_match"
        )
    )

    object_match_count = safe_int(
        question_connection.get(
            "object_match_count"
        ),
        0
    )

    combined_match = bool(
        question_connection.get(
            "combined_match"
        )
    )

    if has_subject_conflict(
        article,
        question_roles
    ):

        return (
            -1.0,
            {},
        )

    # ========================================================
    # aiSearch seed 확인
    # ========================================================

    key = make_article_key(

        article.get(
            "article_number"
        ),

        article.get(
            "sub_article_number",
            0
        ),
    )

    seed = seed_map.get(
        key
    )

    seed_context = build_seed_search_context(

        seed=seed,

        question=question,

        title=title,

        lead_text=lead_text,

        title_roles=title_roles,

        normative_roles=normative_roles,
    )

    semantic_seed_bypass = bool(
        seed_context.get(
            "semantic_seed_bypass"
        )
    )

    local_bridge = find_local_seed_bridge(
        article=article,
        title=title,
        seed_map=seed_map,
    )

    bridge_distance = safe_int(
        local_bridge.get(
            "distance"
        ),
        999,
    )

    bridge_prefix_length = safe_int(
        local_bridge.get(
            "prefix_length"
        ),
        0,
    )

    bridge_seed_rank = safe_int(
        local_bridge.get(
            "seed_rank"
        ),
        999,
    )

    bridge_is_exact_seed = bool(
        local_bridge
        and
        bridge_distance == 0
    )

    bridge_normative = bool(
        title_roles
        or
        normative_roles
        or
        has_strong_consequence_signal(
            article
        )
    )

    if bridge_is_exact_seed:

        # ----------------------------------------------------
        # exact 검색 Seed는 "검색 관련성"일 뿐이므로
        # Local Bridge 우선권을 매우 엄격하게 준다.
        #
        # 기존 has_strong_consequence_signal()에는
        # "위반하여" 같은 넓은 표현도 포함되어 있어,
        # 설치ㆍ관리 조문 안의 부수적 위반 문구만으로도
        # strong consequence로 오인될 수 있었다.
        #
        # 따라서 exact Seed는 실제 effect type이
        # 명시적으로 감지되는 경우만 Bridge로 승격한다.
        #
        # 형사처벌/과태료/손해배상/행정처분처럼
        # 조문 자체가 직접적인 법적 결과를 담는 경우만 허용한다.
        #
        # 특정 법률명/조문번호 하드코딩 없음.
        # ----------------------------------------------------

        exact_seed_effect_types = set(
            detect_effect_types(
                get_article_text(
                    article
                )
            )
        )

        exact_seed_bridge_effect_types = {
            "형사처벌",
            "과태료",
            "손해배상",
            "행정처분",
        }

        local_seed_bridge = bool(
            bridge_normative
            and
            (
                exact_seed_effect_types
                &
                exact_seed_bridge_effect_types
            )
        )

    else:

        local_seed_bridge = bool(
            local_bridge
            and
            bridge_normative
        )

    # ========================================================
    # 핵심 행위가 질문에서 추출되었다면
    # 조문에도 그 행위가 실제로 있어야 direct 후보가 된다.
    #
    # 이것이 기존의 "특허라는 단어만 맞아서 제37조가 선택"
    # 같은 오류를 막는다.
    #
    # 단, 질문에서 안정적인 action을 추출하지 못한 경우에는
    # 기존 규칙으로 fallback할 수 있게 한다.
    # ========================================================

    if (
        action_token
        and
        not action_match
        and
        not local_seed_bridge
        and
        not semantic_seed_bypass
    ):

        return (
            -1.0,
            {},
        )

    # ========================================================
    # 직접 규범성
    #
    # 기존:
    # - 제목에 의무/금지/권리/책임
    # - 본문에 하여야 한다/아니 된다 등
    #
    # 추가:
    # 질문의 핵심 행위가 제목에 직접 나오거나,
    # action+object가 함께 맞으면서 강한 법적 효과가 있는 경우
    # direct 근거 후보로 허용한다.
    #
    # 예:
    # - "침해죄"
    # - "개인정보의 수집·이용"
    # ========================================================

    has_action_grounded_direct_signal = bool(
        action_match
        and
        (
            title_action_match
            or
            combined_match
        )
        and
        (
            title_action_match
            or
            has_strong_consequence_signal(
                article
            )
            or
            bool(
                seed
            )
        )
    )

    has_direct_norm = bool(
        title_roles
        or
        normative_roles
        or
        has_action_grounded_direct_signal
        or
        local_seed_bridge
        or
        semantic_seed_bypass
    )

    if not has_direct_norm:

        return (
            -1.0,
            {},
        )

    if (
        question_roles
        and
        title_role_matches == 0
        and
        lead_role_matches == 0
    ):

        return (
            -1.0,
            {},
        )

    # ========================================================
    # 질문 객체/주제 연결
    #
    # action만 맞고 질문의 핵심 객체가 전혀 맞지 않으면
    # direct 근거로 보기 어렵다.
    #
    # 객체가 없는 질문은 이 조건을 적용하지 않는다.
    # ========================================================

    if (
        object_tokens
        and
        object_match_count == 0
        and
        not local_seed_bridge
        and
        not semantic_seed_bypass
    ):

        return (
            -1.0,
            {},
        )

    # ========================================================
    # 기존 topic match도 최소 하나는 유지한다.
    # ========================================================

    if (
        title_topic_matches == 0
        and
        lead_topic_matches == 0
        and
        not combined_match
        and
        not local_seed_bridge
        and
        not semantic_seed_bypass
    ):

        return (
            -1.0,
            {},
        )

    score = 0.0

    if (
        local_seed_bridge
        and
        not action_match
        and
        not semantic_seed_bypass
    ):

        prefix_bonus = min(
            bridge_prefix_length,
            5,
        ) * 6.0

        distance_bonus = max(
            0.0,
            (
                LOCAL_SEED_MAX_DISTANCE
                -
                bridge_distance
            )
            *
            6.0,
        )

        rank_bonus = max(
            0.0,
            (
                LOCAL_SEED_MAX_RANK
                +
                1
                -
                bridge_seed_rank
            )
            *
            2.0,
        )

        score += (
            35.0
            +
            prefix_bonus
            +
            distance_bonus
            +
            rank_bonus
        )

        # 최상위 검색 Seed 자체가 실제 core 규범이고
        # 예외/불능/특례 제목이 아니라면 약간 우대한다.
        #
        # 예:
        # 일반 행위 규정이 검색 1위인 경우
        # → 주변의 특수형/가중형보다 기본형을 우선.
        #
        # 특정 법률명/조문번호는 사용하지 않는다.
        if (
            bridge_is_exact_seed
            and
            not has_bridge_exception(
                title
            )
        ):

            score += 12.0

        if has_bridge_exception(
            title
        ):

            score -= 30.0

    # ========================================================
    # 질문의 핵심 행위 연결을 가장 강하게 반영
    # ========================================================

    if title_action_match:

        score += 35.0

    elif body_action_match:

        score += 25.0

    if combined_match:

        score += 20.0

    score += (
        min(
            object_match_count,
            3
        )
        * 8.0
    )

    # ========================================================
    # 기존 topic / role / normative 점수
    # ========================================================

    score += (
        title_topic_matches
        * 12.0
    )

    score += (
        lead_topic_matches
        * 3.0
    )

    score += (
        title_role_matches
        * 15.0
    )

    score += (
        lead_role_matches
        * 5.0
    )

    score += (
        len(
            title_roles
        )
        * 10.0
    )

    score += (
        len(
            normative_roles
        )
        * 5.0
    )

    # ========================================================
    # Query Expansion / Reranker의 검색 품질을
    # 검색 관련성 점수로만 반영한다.
    # ========================================================

    if seed:

        score += score_seed_search_context(
            seed_context
        )

    # ========================================================
    # aiSearch는 여전히 보조 seed일 뿐이다.
    # ========================================================

    if seed:

        rank = safe_int(
            seed.get(
                "rank"
            ),
            999
        )

        seed_bonus = max(
            1.0,
            7.0
            -
            min(
                rank,
                6
            )
        )

        score += seed_bonus

    return (
        score,
        {
            "title_roles":
                title_roles,

            "normative_roles":
                normative_roles,

            "seed":
                bool(
                    seed
                ),

            "action_token":
                action_token,

            "object_tokens":
                object_tokens,

            "action_match":
                action_match,

            "title_action_match":
                title_action_match,

            "body_action_match":
                body_action_match,

            "object_match_count":
                object_match_count,

            "combined_match":
                combined_match,

            "local_seed_bridge":
                local_seed_bridge,

            "bridge_seed_article_number":
                local_bridge.get(
                    "seed_number",
                    0
                ),

            "bridge_distance":
                bridge_distance,

            "bridge_prefix_length":
                bridge_prefix_length,

            "exact_seed_effect_types":
                sorted(
                    exact_seed_effect_types
                )
                if bridge_is_exact_seed
                else [],

            "seed_query_coverage":
                seed_context.get(
                    "query_coverage",
                    0.0
                ),

            "seed_original_rank":
                seed_context.get(
                    "original_rank",
                    999
                ),

            "seed_final_rank":
                seed_context.get(
                    "final_rank",
                    999
                ),

            "seed_matched_tokens":
                seed_context.get(
                    "matched_tokens",
                    []
                ),

            "seed_expansion_terms":
                seed_context.get(
                    "expansion_terms",
                    []
                ),

            "novel_expansion_terms":
                seed_context.get(
                    "novel_expansion_terms",
                    []
                ),

            "novel_expansion_title_matches":
                seed_context.get(
                    "novel_title_matches",
                    0
                ),

            "novel_expansion_body_matches":
                seed_context.get(
                    "novel_body_matches",
                    0
                ),

            "negative_context_match":
                seed_context.get(
                    "negative_context_match",
                    False
                ),

            "semantic_seed_bypass":
                semantic_seed_bypass,
        },
    )
