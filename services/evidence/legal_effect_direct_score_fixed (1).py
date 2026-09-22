# ============================================================
# Legal Effect Direct Score
#
# ?ъ슜??吏덈Ц ??議곕Ц 媛?吏곸젒 ?곌껐 ?먯닔 怨꾩궛.
# 湲곗〈 ?먯닔/議곌굔/quality gate 濡쒖쭅? 蹂寃쏀븯吏 ?딅뒗??
# ============================================================

import re

from typing import (
    Any,
    Dict,
    Tuple,
)

from services.evidence.question_action_matcher import (
    score_question_connection,
)

from services.evidence.legal_effect_utils import (
    clean_text,
    safe_int,
    make_article_key,
    extract_question_tokens,
    extract_question_roles,
    get_article_lead_text,
    count_matches,
    detect_title_roles,
    detect_normative_roles,
    has_strong_consequence_signal,
    has_subject_conflict,
)


def get_direct_scoring_text(
    article: Dict[str, Any]
) -> str:
    """
    direct basis 점수 계산에는 조문 제목만이 아니라
    실제 첫 번째 규범 문장을 우선 사용한다.

    full_law article 구조:
    - paragraphs
    - full_text
    - article_text
    - article_content

    특정 법률명/조문번호는 사용하지 않는다.
    """

    paragraphs = (
        article.get(
            "paragraphs"
        )
        or
        []
    )

    if isinstance(
        paragraphs,
        list
    ):

        for paragraph in paragraphs:

            if not isinstance(
                paragraph,
                dict
            ):

                continue

            paragraph_text = clean_text(
                paragraph.get(
                    "text"
                )
            )

            if paragraph_text:

                return paragraph_text

    for key in (
        "full_text",
        "article_text",
        "article_content",
    ):

        value = clean_text(
            article.get(
                key
            )
        )

        if value:

            return value

    return get_article_lead_text(
        article
    )


def get_action_core_fragments(
    action_token: str
):
    """
    한국어 복합 행동어의 뒤쪽 행동 핵심을 일반적으로 추출한다.

    예:
    - '음주운전' -> '운전'
    - '무단복제' -> '복제'

    특정 도메인 단어 사전은 사용하지 않는다.
    """

    token = clean_text(
        action_token
    )

    token = re.sub(
        r"[^가-힣A-Za-z0-9]",
        "",
        token
    )

    if len(
        token
    ) < 3:

        return []

    fragments = []

    max_length = min(
        4,
        len(
            token
        )
        - 1
    )

    for length in range(
        2,
        max_length + 1
    ):

        fragment = token[
            -length:
        ]

        if (
            fragment
            and
            fragment != token
            and
            fragment not in fragments
        ):

            fragments.append(
                fragment
            )

    return fragments


def has_action_core_match(
    action_token: str,
    text: str
) -> bool:

    text = clean_text(
        text
    )

    if not text:

        return False

    return any(
        fragment in text

        for fragment in get_action_core_fragments(
            action_token
        )
    )


def has_cross_reference_subject_scope(
    lead_text: str
) -> bool:
    """
    첫 문장의 적용대상이 다른 조문에 따른 자격/조건을 전제로
    좁혀져 있는지 확인한다.

    예:
    '제00조에 따라 ... 받은 사람은 ...'

    특정 법률이나 조문번호는 사용하지 않는다.
    """

    lead_text = clean_text(
        lead_text
    )

    if not lead_text:

        return False

    prefix = lead_text[
        :140
    ]

    return bool(
        re.search(
            r"제\s*\d+\s*조(?:의\s*\d+)?[^.]{0,45}에\s*따라",
            prefix
        )
    )


def has_broad_subject_signal(
    lead_text: str
) -> bool:

    lead_text = clean_text(
        lead_text
    )

    if not lead_text:

        return False

    prefix = lead_text[
        :80
    ]

    return any(
        marker in prefix

        for marker in (
            "누구든지",
            "모든 사람",
            "모든 자",
        )
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

    lead_text = get_direct_scoring_text(
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
    # 吏덈Ц???듭떖 ?됱쐞 / 媛앹껜 ?곌껐??    #
    # ??
    #
    # ?뱁뿀 移⑦빐
    # ??action = 移⑦빐
    # ??object = ?뱁뿀
    #
    # 媛쒖씤?뺣낫 ?섏쭛
    # ??action = ?섏쭛
    # ??object = 媛쒖씤?뺣낫 / ?숈쓽
    #
    # ?뱀젙 踰뺣쪧紐낆씠??議곕Ц踰덊샇???ъ슜?섏? ?딅뒗??
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

    # ========================================================
    # 복합 행동어 / 독립 객체 보정
    #
    # matcher가 '음주운전'처럼 하나의 복합 행동어를
    # action과 object 양쪽에 동시에 넣는 경우,
    # 동일 토큰을 독립 object로 강제하지 않는다.
    #
    # 또한 정확한 복합어가 없어도 뒤쪽 행동 핵심이
    # 실제 규범 문장에 있으면 약한 action 연결로 인정한다.
    # ========================================================

    independent_object_tokens = [

        token

        for token in object_tokens

        if clean_text(
            token
        )
        and
        clean_text(
            token
        ) != action_token
    ]

    title_action_core_match = bool(
        action_token
        and
        has_action_core_match(
            action_token,
            title
        )
    )

    body_action_core_match = bool(
        action_token
        and
        has_action_core_match(
            action_token,
            lead_text
        )
    )

    action_core_match = bool(
        title_action_core_match
        or
        body_action_core_match
    )

    effective_action_match = bool(
        action_match
        or
        action_core_match
    )

    cross_reference_scope = (
        has_cross_reference_subject_scope(
            lead_text
        )
    )

    broad_subject_signal = (
        has_broad_subject_signal(
            lead_text
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
    # aiSearch seed ?뺤씤
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

    # ========================================================
    # ?듭떖 ?됱쐞媛 吏덈Ц?먯꽌 異붿텧?섏뿀?ㅻ㈃
    # 議곕Ц?먮룄 洹??됱쐞媛 ?ㅼ젣濡??덉뼱??direct ?꾨낫媛 ?쒕떎.
    #
    # ?닿쾬??湲곗〈??"?뱁뿀?쇰뒗 ?⑥뼱留?留욎븘????7議곌? ?좏깮"
    # 媛숈? ?ㅻ쪟瑜?留됰뒗??
    #
    # ?? 吏덈Ц?먯꽌 ?덉젙?곸씤 action??異붿텧?섏? 紐삵븳 寃쎌슦?먮뒗
    # 湲곗〈 洹쒖튃?쇰줈 fallback?????덇쾶 ?쒕떎.
    # ========================================================

    if (
        action_token
        and
        not effective_action_match
    ):

        return (
            -1.0,
            {},
        )

    # ========================================================
    # 吏곸젒 洹쒕쾾??    #
    # 湲곗〈:
    # - ?쒕ぉ???섎Т/湲덉?/沅뚮━/梨낆엫
    # - 蹂몃Ц???섏뿬???쒕떎/?꾨땲 ?쒕떎 ??    #
    # 異붽?:
    # 吏덈Ц???듭떖 ?됱쐞媛 ?쒕ぉ??吏곸젒 ?섏삤嫄곕굹,
    # action+object媛 ?④퍡 留욎쑝硫댁꽌 媛뺥븳 踰뺤쟻 ?④낵媛 ?덈뒗 寃쎌슦
    # direct 洹쇨굅 ?꾨낫濡??덉슜?쒕떎.
    #
    # ??
    # - "移⑦빐二?
    # - "媛쒖씤?뺣낫???섏쭛쨌?댁슜"
    # ========================================================

    has_action_grounded_direct_signal = bool(
        effective_action_match
        and
        (
            title_action_match
            or
            combined_match
            or
            action_core_match
        )
        and
        (
            title_action_match
            or
            title_action_core_match
            or
            has_strong_consequence_signal(
                article
            )
            or
            bool(
                seed
            )
            or
            bool(
                title_roles
            )
        )
    )

    has_direct_norm = bool(
        title_roles
        or
        normative_roles
        or
        has_action_grounded_direct_signal
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
    # 吏덈Ц 媛앹껜/二쇱젣 ?곌껐
    #
    # action留?留욊퀬 吏덈Ц???듭떖 媛앹껜媛 ?꾪? 留욎? ?딆쑝硫?    # direct 洹쇨굅濡?蹂닿린 ?대졄??
    #
    # 媛앹껜媛 ?녿뒗 吏덈Ц? ??議곌굔???곸슜?섏? ?딅뒗??
    # ========================================================

    if (
        independent_object_tokens
        and
        object_match_count == 0
    ):

        return (
            -1.0,
            {},
        )

    # ========================================================
    # 湲곗〈 topic match??理쒖냼 ?섎굹???좎??쒕떎.
    # ========================================================

    if (
        title_topic_matches == 0
        and
        lead_topic_matches == 0
        and
        not combined_match
        and
        not action_core_match
    ):

        return (
            -1.0,
            {},
        )

    score = 0.0

    # ========================================================
    # 吏덈Ц???듭떖 ?됱쐞 ?곌껐??媛??媛뺥븯寃?諛섏쁺
    # ========================================================

    if title_action_match:

        score += 35.0

    elif body_action_match:

        score += 25.0

    elif title_action_core_match:

        score += 30.0

    elif body_action_core_match:

        score += 22.0

    if combined_match:

        score += 20.0

    elif action_core_match:

        score += 10.0

    score += (
        min(
            object_match_count,
            3
        )
        * 8.0
    )

    # ========================================================
    # 湲곗〈 topic / role / normative ?먯닔
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
    # 적용범위 정합성
    # ========================================================

    if not question_roles:

        if cross_reference_scope:

            score -= 45.0

        elif broad_subject_signal:

            score += 15.0

    # ========================================================
    # aiSearch???ъ쟾??蹂댁“ seed??肉먯씠??
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

            "action_core_match":
                action_core_match,

            "title_action_core_match":
                title_action_core_match,

            "body_action_core_match":
                body_action_core_match,

            "cross_reference_scope":
                cross_reference_scope,

            "broad_subject_signal":
                broad_subject_signal,
        },
    )
