# ============================================================
# Legal Effect Direct
#
# Direct 근거 탐색의 public entry.
#
# 역할 분리:
# - legal_effect_direct_utils.py  : seed map
# - legal_effect_direct_score.py  : 직접 근거 점수 계산
# - legal_effect_direct_select.py : basis/anchor 선택
#
# 기존 import 호환성을 위해 public 함수를 re-export한다.
# ============================================================

from services.evidence.legal_effect_direct_utils import (
    build_seed_article_map,
)

from services.evidence.legal_effect_direct_score import (
    score_direct_article,
)

from services.evidence.legal_effect_direct_select import (
    find_direct_basis_articles,
    select_direct_anchors,
)


__all__ = [
    "build_seed_article_map",
    "score_direct_article",
    "find_direct_basis_articles",
    "select_direct_anchors",
]
