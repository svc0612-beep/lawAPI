# ============================================================
# Legal Effect Analyzer
#
# 역할
# 1. 사용자 질문과 직접 관련된 핵심 조문 탐색
# 2. 직접 의무 / 금지 / 권리 근거 탐색
# 3. 직접 근거와 연결되는 1차 법적 효과 탐색
# 4. 1차 효과와 연결되는 2차 후속 효과 탐색
#
# 중요
# - 특정 법령명을 하드코딩하지 않는다.
# - 공식 법령 전체 조문만 사용한다.
# - aiSearch 결과는 관련성 seed로만 사용한다.
# - 제목이 "벌칙"이라고 자동 연결하지 않는다.
# ============================================================

import re

from services.evidence.question_action_matcher import (
    score_question_connection,
)

from typing import (
    Any,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
)


# ============================================================
# 설정
# ============================================================

DIRECT_BASIS_LIMIT = 3
FIRST_LEVEL_LIMIT = 6
SECOND_LEVEL_LIMIT = 6

DIRECT_ANCHOR_RATIO = 0.85


# ============================================================
# 질문 불용어
# ============================================================

QUESTION_STOP_WORDS = {
    "하면",
    "안하면",
    "안",
    "어떻게",
    "어떻게돼",
    "어떻게되",
    "되나",
    "되나요",
    "뭐야",
    "무엇",
    "알려줘",
    "알려",
    "관련",
    "대한",
    "대해서",
    "경우",
    "있는",
    "있어",
    "있나요",
    "무슨",
    "어떤",
}


# ============================================================
# 일반 사용자 표현 → 일반 법률 주체
# ============================================================

LEGAL_ROLE_ALIASES = {

    "회사": (
        "사업주",
        "사용자",
        "법인",
        "사업자",
    ),

    "직장": (
        "사업주",
        "사용자",
    ),

    "사장": (
        "사업주",
        "사용자",
    ),

    "직원": (
        "근로자",
    ),

    "근로자": (
        "근로자",
    ),

    "사업주": (
        "사업주",
    ),

    "사업자": (
        "사업자",
    ),

    "국가": (
        "국가",
    ),

    "지자체": (
        "지방자치단체",
    ),

    "지방자치단체": (
        "지방자치단체",
    ),

    "공공기관": (
        "공공기관",
    ),
}


# ============================================================
# 법적 주체
# ============================================================

KNOWN_LEGAL_SUBJECTS = {
    "사업주",
    "사용자",
    "사업자",
    "근로자",
    "국가",
    "지방자치단체",
    "공공기관",
    "법인",
    "임원",
    "공무원",
}


# ============================================================
# 제목의 직접 규범 표현
# ============================================================

TITLE_DIRECT_TERMS = {

    "의무": (
        "의무",
    ),

    "금지": (
        "금지",
    ),

    "책임": (
        "책임",
    ),

    "권리": (
        "권리",
    ),
}


# ============================================================
# 본문의 규범 표현
# ============================================================

NORMATIVE_TERMS = {

    "의무": (
        "하여야 한다",
        "하여야 할",
        "해야 한다",
        "하도록 하여야",
    ),

    "금지": (
        "하여서는 아니 된다",
        "해서는 아니 된다",
        "할 수 없다",
    ),

    "권리": (
        "청구할 수 있다",
        "신청할 수 있다",
    ),
}


# ============================================================
# 법적 효과 유형
# ============================================================

LEGAL_EFFECT_TERMS = {

    "형사처벌": (
        "징역",
        "벌금",
        "처한다",
    ),

    "과태료": (
        "과태료",
    ),

    "부담금": (
        "부담금",
    ),

    "가산금": (
        "가산금",
    ),

    "연체금": (
        "연체금",
    ),

    "체납처분": (
        "체납처분",
        "독촉",
        "공매",
    ),

    "공표": (
        "공표",
        "명단공개",
        "명단을 공개",
    ),

    "행정처분": (
        "허가취소",
        "등록취소",
        "영업정지",
        "업무정지",
        "취소할 수 있다",
        "정지할 수 있다",
    ),

    "손해배상": (
        "손해배상",
        "배상하여야",
        "배상할 책임",
    ),

    "징수": (
        "징수",
    ),
}


# ============================================================
# 강한 법적 효과 표현
# ============================================================

STRONG_CONSEQUENCE_TERMS = (
    "위반한 자",
    "위반하여",
    "위반하였",
    "못 미치는",
    "미달하는",
    "납부하지 아니",
    "납부하지 않",
    "신고를 하지 아니",
    "신고하지 아니",
    "거짓된 신고",
    "거짓 신고",
    "과태료를 부과",
    "벌금에 처한다",
    "징역",
    "가산금으로 징수",
    "연체금을 징수",
    "독촉하여야",
    "체납처분",
)


CONSEQUENCE_TITLE_TERMS = (
    "부담금 납부",
    "가산금",
    "연체금",
    "독촉",
    "체납처분",
    "과태료",
    "벌칙",
    "손해배상",
    "행정처분",
)


CONCEPT_STOP_WORDS = {
    "한다",
    "하여야",
    "있다",
    "있는",
    "경우",
    "따른",
    "따라",
    "해당",
    "대하여",
    "대한",
    "위하여",
    "위한",
    "필요한",
    "정하는",
    "대통령령",
    "고용노동부장관",
    "이하",
    "각호",
    "각",
    "자는",
    "사람",
}


# ============================================================
# 문자열 정리
# ============================================================

def clean_text(
    value: Any
) -> str:

    if value is None:

        return ""

    text = str(
        value
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# ============================================================
# 비교용 정규화
# ============================================================

def normalize_for_match(
    value: Any
) -> str:

    return clean_text(
        value
    ).lower()


# ============================================================
# 법령명 정규화
# ============================================================

def normalize_law_name(
    value: Any
) -> str:

    return "".join(
        clean_text(
            value
        ).split()
    )


# ============================================================
# 안전한 정수
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
# 조문 키
# ============================================================

def make_article_key(
    article_number: Any,
    sub_article_number: Any = 0
) -> str:

    try:

        article_number = int(
            article_number
        )

    except (
        TypeError,
        ValueError,
    ):

        return ""

    try:

        sub_article_number = int(
            sub_article_number
            or 0
        )

    except (
        TypeError,
        ValueError,
    ):

        sub_article_number = 0

    return (
        f"{article_number}:"
        f"{sub_article_number}"
    )


# ============================================================
# 질문 토큰
# ============================================================

def extract_question_tokens(
    question: str
) -> List[str]:

    question = normalize_for_match(
        question
    )

    raw_tokens = re.findall(
        r"[가-힣A-Za-z0-9]+",
        question
    )

    results = []

    for token in raw_tokens:

        token = token.strip()

        if len(
            token
        ) < 2:

            continue

        if token in QUESTION_STOP_WORDS:

            continue

        if token not in results:

            results.append(
                token
            )

    return results


# ============================================================
# 질문의 법률상 주체
# ============================================================

def extract_question_roles(
    question: str
) -> Set[str]:

    question = normalize_for_match(
        question
    )

    results = set()

    for (
        user_term,
        legal_terms
    ) in LEGAL_ROLE_ALIASES.items():

        if user_term not in question:

            continue

        for legal_term in legal_terms:

            results.add(
                legal_term
            )

    return results


# ============================================================
# 조문 전체 텍스트
# ============================================================

def get_article_text(
    article: Dict[str, Any]
) -> str:

    if not isinstance(
        article,
        dict
    ):

        return ""

    title = clean_text(
        article.get(
            "article_title"
        )
    )

    full_text = clean_text(
        article.get(
            "full_text"
        )
    )

    if not full_text:

        full_text = clean_text(
            article.get(
                "article_content"
            )
        )

    return (
        f"{title} {full_text}"
    ).strip()


# ============================================================
# 조문 앞부분
# ============================================================

def get_article_lead_text(
    article: Dict[str, Any],
    max_length: int = 700
) -> str:

    full_text = clean_text(
        article.get(
            "full_text"
        )
    )

    if not full_text:

        full_text = clean_text(
            article.get(
                "article_content"
            )
        )

    return full_text[
        :max_length
    ]


# ============================================================
# 토큰 매칭
# ============================================================

def count_matches(
    tokens,
    text: str
) -> int:

    text = normalize_for_match(
        text
    )

    return sum(
        1
        for token in tokens
        if token in text
    )


# ============================================================
# 제목 규범 역할
# ============================================================

def detect_title_roles(
    title: str
) -> List[str]:

    title = normalize_for_match(
        title
    )

    results = []

    for (
        role,
        terms
    ) in TITLE_DIRECT_TERMS.items():

        if any(
            term in title
            for term in terms
        ):

            results.append(
                role
            )

    return results


# ============================================================
# 본문 규범 역할
# ============================================================

def detect_normative_roles(
    text: str
) -> List[str]:

    text = normalize_for_match(
        text
    )

    results = []

    for (
        role,
        terms
    ) in NORMATIVE_TERMS.items():

        if any(
            term in text
            for term in terms
        ):

            results.append(
                role
            )

    return results


# ============================================================
# 법적 효과 감지
# ============================================================

def detect_effect_types(
    text: str
) -> List[str]:

    text = normalize_for_match(
        text
    )

    results = []

    for (
        effect_type,
        terms
    ) in LEGAL_EFFECT_TERMS.items():

        if any(
            term in text
            for term in terms
        ):

            results.append(
                effect_type
            )

    return results


# ============================================================
# 강한 법적 효과 여부
# ============================================================

def has_strong_consequence_signal(
    article: Dict[str, Any]
) -> bool:

    title = normalize_for_match(
        article.get(
            "article_title"
        )
    )

    text = normalize_for_match(
        get_article_text(
            article
        )
    )

    if any(
        term in title
        for term in CONSEQUENCE_TITLE_TERMS
    ):

        return True

    if any(
        term in text
        for term in STRONG_CONSEQUENCE_TERMS
    ):

        return True

    return False


# ============================================================
# 조문 참조 번호 추출
# ============================================================

def extract_article_references(
    text: str,
    own_article_number: Optional[int] = None
) -> Set[int]:

    text = clean_text(
        text
    )

    matches = re.findall(
        r"제\s*(\d+)\s*조",
        text
    )

    results = set()

    for value in matches:

        try:

            number = int(
                value
            )

        except (
            TypeError,
            ValueError,
        ):

            continue

        if (
            own_article_number is not None
            and
            number == own_article_number
        ):

            continue

        results.add(
            number
        )

    return results


# ============================================================
# aiSearch seed map
# ============================================================

def build_seed_article_map(
    seed_laws: List[
        Dict[str, Any]
    ],
    primary_law_name: str
) -> Dict[
    str,
    Dict[str, Any]
]:

    primary_name = normalize_law_name(
        primary_law_name
    )

    results = {}

    if not isinstance(
        seed_laws,
        list
    ):

        return results

    for index, item in enumerate(
        seed_laws
    ):

        if not isinstance(
            item,
            dict
        ):

            continue

        item_law_name = normalize_law_name(
            item.get(
                "law_name"
            )
        )

        if (
            primary_name
            and
            item_law_name != primary_name
        ):

            continue

        key = make_article_key(

            item.get(
                "article_number"
            ),

            item.get(
                "sub_article_number",
                0
            ),
        )

        if not key:

            continue

        rank = (
            item.get(
                "final_rank"
            )
            or
            item.get(
                "original_rank"
            )
            or
            (
                index + 1
            )
        )

        results[
            key
        ] = {

            "rank":
                safe_int(
                    rank,
                    index + 1
                ),

            "title":
                clean_text(
                    item.get(
                        "article_title"
                    )
                ),
        }

    return results


# ============================================================
# 개념 토큰
# ============================================================

def extract_concept_tokens(
    text: str
) -> Set[str]:

    text = normalize_for_match(
        text
    )

    raw_tokens = re.findall(
        r"[가-힣A-Za-z0-9]+",
        text
    )

    results = set()

    for token in raw_tokens:

        token = token.strip()

        if len(
            token
        ) < 2:

            continue

        if token in CONCEPT_STOP_WORDS:

            continue

        results.add(
            token
        )

    return results


# ============================================================
# 제목의 법적 주체
# ============================================================

def get_title_subjects(
    title: str
) -> Set[str]:

    title = normalize_for_match(
        title
    )

    return {

        subject

        for subject in KNOWN_LEGAL_SUBJECTS

        if subject in title
    }


# ============================================================
# 질문 주체와 제목 주체 충돌
# ============================================================

def has_subject_conflict(
    article: Dict[str, Any],
    question_roles: Set[str]
) -> bool:

    if not question_roles:

        return False

    title = clean_text(
        article.get(
            "article_title"
        )
    )

    title_subjects = get_title_subjects(
        title
    )

    if not title_subjects:

        return False

    if (
        title_subjects
        &
        question_roles
    ):

        return False

    return True


# ============================================================
# 직접 근거 점수
# ============================================================

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
    ):

        return (
            -1.0,
            {},
        )

    score = 0.0

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
        },
    )


# ============================================================
# 직접 근거
# ============================================================

def find_direct_basis_articles(
    articles: List[
        Dict[str, Any]
    ],
    question: str,
    seed_map: Dict[
        str,
        Dict[str, Any]
    ]
) -> List[
    Dict[str, Any]
]:

    scored = []

    for index, article in enumerate(
        articles
    ):

        if not isinstance(
            article,
            dict
        ):

            continue

        score, details = score_direct_article(

            article=article,

            question=question,

            seed_map=seed_map,
        )

        if score <= 0:

            continue

        scored.append(
            (
                score,
                index,
                article,
                details,
            )
        )

    scored.sort(

        key=lambda item: (
            -item[0],
            item[1],
        )
    )

    results = []

    for (
        score,
        _,
        article,
        details
    ) in scored[
        :DIRECT_BASIS_LIMIT
    ]:

        roles = list(
            dict.fromkeys(

                details.get(
                    "title_roles",
                    []
                )
                +
                details.get(
                    "normative_roles",
                    []
                )
            )
        )

        results.append(
            {
                "article":
                    article,

                "score":
                    score,

                "roles":
                    roles,

                "seed":
                    details.get(
                        "seed",
                        False
                    ),

                "connection_level":
                    0,
            }
        )

    return results


# ============================================================
# 핵심 직접근거(anchor)
# ============================================================

def select_direct_anchors(
    direct_basis: List[
        Dict[str, Any]
    ]
) -> List[
    Dict[str, Any]
]:

    if not direct_basis:

        return []

    top_score = float(
        direct_basis[
            0
        ].get(
            "score",
            0
        )
        or 0
    )

    if top_score <= 0:

        return []

    threshold = (
        top_score
        *
        DIRECT_ANCHOR_RATIO
    )

    return [

        item

        for item in direct_basis

        if float(
            item.get(
                "score",
                0
            )
            or 0
        )
        >= threshold
    ]


# ============================================================
# 조문 번호 집합
# ============================================================

def get_article_numbers(
    items: List[
        Dict[str, Any]
    ]
) -> Set[int]:

    results = set()

    for item in items:

        article = item.get(
            "article",
            {}
        )

        try:

            results.add(
                int(
                    article.get(
                        "article_number"
                    )
                )
            )

        except (
            TypeError,
            ValueError,
        ):

            continue

    return results


# ============================================================
# 조문 개념 집합
# ============================================================

def build_item_concepts(
    items: List[
        Dict[str, Any]
    ]
) -> Set[str]:

    results = set()

    for item in items:

        article = item.get(
            "article",
            {}
        )

        title = clean_text(
            article.get(
                "article_title"
            )
        )

        lead = get_article_lead_text(
            article,
            max_length=1200
        )

        results.update(
            extract_concept_tokens(
                f"{title} {lead}"
            )
        )

    return results


# ============================================================
# 1차 직접 효과
# ============================================================

def find_first_level_consequences(
    articles: List[
        Dict[str, Any]
    ],
    question: str,
    direct_anchors: List[
        Dict[str, Any]
    ],
    seed_map: Dict[
        str,
        Dict[str, Any]
    ]
) -> List[
    Dict[str, Any]
]:

    if not direct_anchors:

        return []

    direct_numbers = get_article_numbers(
        direct_anchors
    )

    direct_keys = {

        make_article_key(

            item.get(
                "article",
                {}
            ).get(
                "article_number"
            ),

            item.get(
                "article",
                {}
            ).get(
                "sub_article_number",
                0
            ),
        )

        for item in direct_anchors
    }

    direct_concepts = build_item_concepts(
        direct_anchors
    )

    question_roles = extract_question_roles(
        question
    )

    results = []

    for article in articles:

        if not isinstance(
            article,
            dict
        ):

            continue

        key = make_article_key(

            article.get(
                "article_number"
            ),

            article.get(
                "sub_article_number",
                0
            ),
        )

        if key in direct_keys:

            continue

        text = get_article_text(
            article
        )

        effect_types = detect_effect_types(
            text
        )

        if not effect_types:

            continue

        if not has_strong_consequence_signal(
            article
        ):

            continue

        if has_subject_conflict(
            article,
            question_roles
        ):

            continue

        own_number = safe_int(
            article.get(
                "article_number"
            ),
            0
        )

        references = extract_article_references(

            text,

            own_article_number=(
                own_number
                if own_number
                else None
            ),
        )

        referenced_direct = (
            references
            &
            direct_numbers
        )

        article_concepts = extract_concept_tokens(
            text
        )

        shared_concepts = (
            article_concepts
            &
            direct_concepts
        )

        is_seed = (
            key in seed_map
        )

        connected = (
            bool(
                referenced_direct
            )
            or
            (
                is_seed
                and
                len(
                    shared_concepts
                ) >= 2
            )
        )

        if not connected:

            continue

        score = 0.0

        if referenced_direct:

            score += 20.0

        if is_seed:

            score += 10.0

        score += (
            min(
                len(
                    shared_concepts
                ),
                8
            )
            * 2.0
        )

        score += (
            len(
                effect_types
            )
            * 2.0
        )

        results.append(
            {
                "article":
                    article,

                "score":
                    score,

                "effect_types":
                    effect_types,

                "references":
                    sorted(
                        references
                    ),

                "referenced_direct_articles":
                    sorted(
                        referenced_direct
                    ),

                "shared_concepts":
                    sorted(
                        shared_concepts
                    ),

                "seed":
                    is_seed,

                "connection_level":
                    1,
            }
        )

    results.sort(

        key=lambda item: (
            -item.get(
                "score",
                0
            ),

            safe_int(
                item.get(
                    "article",
                    {}
                ).get(
                    "article_number"
                ),
                999999
            ),
        )
    )

    return results[
        :FIRST_LEVEL_LIMIT
    ]


# ============================================================
# 2차 후속 효과
# ============================================================

def find_second_level_consequences(
    articles: List[
        Dict[str, Any]
    ],
    question: str,
    direct_anchors: List[
        Dict[str, Any]
    ],
    first_level: List[
        Dict[str, Any]
    ]
) -> List[
    Dict[str, Any]
]:

    if not first_level:

        return []

    first_numbers = get_article_numbers(
        first_level
    )

    first_concepts = build_item_concepts(
        first_level
    )

    question_roles = extract_question_roles(
        question
    )

    excluded_keys = set()

    for collection in (
        direct_anchors,
        first_level,
    ):

        for item in collection:

            article = item.get(
                "article",
                {}
            )

            excluded_keys.add(

                make_article_key(

                    article.get(
                        "article_number"
                    ),

                    article.get(
                        "sub_article_number",
                        0
                    ),
                )
            )

    results = []

    for article in articles:

        if not isinstance(
            article,
            dict
        ):

            continue

        key = make_article_key(

            article.get(
                "article_number"
            ),

            article.get(
                "sub_article_number",
                0
            ),
        )

        if key in excluded_keys:

            continue

        if has_subject_conflict(
            article,
            question_roles
        ):

            continue

        text = get_article_text(
            article
        )

        effect_types = detect_effect_types(
            text
        )

        if not effect_types:

            continue

        if not has_strong_consequence_signal(
            article
        ):

            continue

        own_number = safe_int(
            article.get(
                "article_number"
            ),
            0
        )

        references = extract_article_references(

            text,

            own_article_number=(
                own_number
                if own_number
                else None
            ),
        )

        referenced_first = (
            references
            &
            first_numbers
        )

        article_concepts = extract_concept_tokens(
            text
        )

        shared_concepts = (
            article_concepts
            &
            first_concepts
        )

        connected = (
            bool(
                referenced_first
            )
            or
            len(
                shared_concepts
            ) >= 3
        )

        if not connected:

            continue

        score = 0.0

        if referenced_first:

            score += 20.0

        score += (
            min(
                len(
                    shared_concepts
                ),
                8
            )
            * 2.0
        )

        score += (
            len(
                effect_types
            )
            * 2.0
        )

        results.append(
            {
                "article":
                    article,

                "score":
                    score,

                "effect_types":
                    effect_types,

                "references":
                    sorted(
                        references
                    ),

                "referenced_first_level_articles":
                    sorted(
                        referenced_first
                    ),

                "shared_concepts":
                    sorted(
                        shared_concepts
                    ),

                "connection_level":
                    2,
            }
        )

    results.sort(

        key=lambda item: (
            -item.get(
                "score",
                0
            ),

            safe_int(
                item.get(
                    "article",
                    {}
                ).get(
                    "article_number"
                ),
                999999
            ),
        )
    )

    return results[
        :SECOND_LEVEL_LIMIT
    ]


# ============================================================
# 중복 제거
# ============================================================

def deduplicate_items(
    items: List[
        Dict[str, Any]
    ]
) -> List[
    Dict[str, Any]
]:

    results = []

    seen = set()

    for item in items:

        article = item.get(
            "article",
            {}
        )

        key = make_article_key(

            article.get(
                "article_number"
            ),

            article.get(
                "sub_article_number",
                0
            ),
        )

        if not key:

            continue

        if key in seen:

            continue

        seen.add(
            key
        )

        results.append(
            item
        )

    return results


# ============================================================
# 최종 분석
# ============================================================

def analyze_legal_effects(
    question: str,
    full_law: Dict[str, Any],
    seed_laws: Optional[
        List[
            Dict[str, Any]
        ]
    ] = None,
    primary_law_name: str = "",
) -> Dict[str, Any]:

    if not isinstance(
        full_law,
        dict
    ):

        return {

            "status":
                "error",

            "direct_basis":
                [],

            "direct_anchors":
                [],

            "first_level_consequences":
                [],

            "second_level_consequences":
                [],

            "consequence_basis":
                [],
        }

    articles = full_law.get(
        "articles",
        []
    )

    if not isinstance(
        articles,
        list
    ):

        articles = []

    if not primary_law_name:

        primary_law_name = clean_text(
            full_law.get(
                "law_name"
            )
        )

    seed_map = build_seed_article_map(

        seed_laws=(
            seed_laws
            if isinstance(
                seed_laws,
                list
            )
            else []
        ),

        primary_law_name=(
            primary_law_name
        ),
    )

    direct_basis = find_direct_basis_articles(

        articles=articles,

        question=question,

        seed_map=seed_map,
    )

    direct_anchors = select_direct_anchors(
        direct_basis
    )

    first_level = find_first_level_consequences(

        articles=articles,

        question=question,

        direct_anchors=direct_anchors,

        seed_map=seed_map,
    )

    second_level = find_second_level_consequences(

        articles=articles,

        question=question,

        direct_anchors=direct_anchors,

        first_level=first_level,
    )

    consequence_basis = deduplicate_items(

        first_level
        +
        second_level
    )

    return {

        "status":
            "success",

        "law_name":
            clean_text(
                primary_law_name
            ),

        "direct_basis":
            direct_basis,

        "direct_anchors":
            direct_anchors,

        "first_level_consequences":
            first_level,

        "second_level_consequences":
            second_level,

        "consequence_basis":
            consequence_basis,

        "direct_basis_count":
            len(
                direct_basis
            ),

        "direct_anchor_count":
            len(
                direct_anchors
            ),

        "first_level_count":
            len(
                first_level
            ),

        "second_level_count":
            len(
                second_level
            ),

        "consequence_basis_count":
            len(
                consequence_basis
            ),

        "seed_article_count":
            len(
                seed_map
            ),
    }