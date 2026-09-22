# ============================================================
# 공식 법령 체계도 JSON Parser
#
# 실제 lsStmd 응답 특성
# - 단일 항목은 dict, 복수 항목은 list로 응답한다.
# - 법률 > 시행령 > 시행규칙 구조가 중첩된다.
# - 행정규칙도 함께 오지만 이번 단계에서는 분리한다.
# - 관련법령은 상하위법과 별도 필드로 올 수 있다.
# ============================================================

import re

from datetime import (
    datetime,
    timezone,
)

from typing import (
    Any,
    Dict,
    List,
    Optional,
    Set,
)


LAW_INFO_NAME_KEYS = (
    "법령명",
    "법령명한글",
)

ADMIN_INFO_NAME_KEYS = (
    "행정규칙명",
)

SENSITIVE_QUERY_PATTERN = re.compile(
    r"([?&](?:OC|serviceKey|apiKey|api_key)=)[^&]+",
    flags=re.IGNORECASE,
)


def normalize_text(
    value: Any,
) -> str:

    if value is None:
        return ""

    if isinstance(value, dict):

        if "content" in value:
            value = value.get(
                "content"
            )

        else:
            return ""

    return re.sub(
        r"\s+",
        " ",
        str(value),
    ).strip()


def ensure_list(
    value: Any,
) -> List[Any]:

    if isinstance(value, list):
        return value

    if value in (
        None,
        "",
    ):
        return []

    return [
        value
    ]


def first_text(
    data: Dict[str, Any],
    keys,
) -> str:

    for key in keys:

        value = normalize_text(
            data.get(key)
        )

        if value:
            return value

    return ""


def sanitize_official_link(
    value: Any,
) -> str:

    link = normalize_text(
        value
    )

    if not link:
        return ""

    link = SENSITIVE_QUERY_PATTERN.sub(
        r"\1[removed]",
        link,
    )

    if link.startswith("/"):
        return (
            "https://www.law.go.kr"
            + link
        )

    return link


def get_system_map_root(
    raw_data: Dict[str, Any],
) -> Dict[str, Any]:

    root = raw_data.get(
        "법령체계도"
    )

    if isinstance(root, dict):
        return root

    return {}


def get_basic_info(
    value: Dict[str, Any],
) -> Dict[str, Any]:

    basic = value.get(
        "기본정보"
    )

    if isinstance(basic, dict):
        return basic

    if any(
        key in value
        for key in (
            *LAW_INFO_NAME_KEYS,
            *ADMIN_INFO_NAME_KEYS,
        )
    ):
        return value

    return {}


def parse_info(
    value: Dict[str, Any],
) -> Dict[str, Any]:

    basic = get_basic_info(
        value
    )

    if not basic:
        return {}

    law_name = first_text(
        basic,
        LAW_INFO_NAME_KEYS,
    )

    admin_name = first_text(
        basic,
        ADMIN_INFO_NAME_KEYS,
    )

    name = law_name or admin_name

    if not name:
        return {}

    is_administrative = bool(
        admin_name
    )

    return {
        "law_name": name,
        "law_type": normalize_text(
            basic.get("법종구분")
        ),
        "law_id": first_text(
            basic,
            (
                "법령ID",
                "행정규칙ID",
            ),
        ),
        "mst": first_text(
            basic,
            (
                "법령일련번호",
                "행정규칙일련번호",
            ),
        ),
        "official_link": sanitize_official_link(
            basic.get("본문상세링크")
        ),
        "is_administrative": is_administrative,
    }


def collect_hierarchy_nodes(
    hierarchy: Any,
    include_administrative: bool = False,
) -> List[Dict[str, Any]]:

    nodes: List[Dict[str, Any]] = []

    def walk(
        value: Any,
        parent_index: Optional[int] = None,
        category: str = "",
        path: Optional[List[str]] = None,
    ) -> None:

        current_path = list(
            path
            or []
        )

        if isinstance(value, list):

            for item in value:
                walk(
                    item,
                    parent_index,
                    category,
                    current_path,
                )

            return

        if not isinstance(value, dict):
            return

        if category == "행정규칙" and not include_administrative:
            return

        info = parse_info(
            value
        )

        current_parent = parent_index

        if info:

            if (
                not info.get("is_administrative")
                or include_administrative
            ):

                current_parent = len(
                    nodes
                )

                nodes.append(
                    {
                        **info,
                        "parent_index": parent_index,
                        "category": category,
                        "path": current_path,
                    }
                )

        for key, child in value.items():

            if key == "기본정보":
                continue

            if key == "행정규칙" and not include_administrative:
                continue

            child_path = [
                *current_path,
                str(key),
            ]

            walk(
                child,
                current_parent,
                str(key),
                child_path,
            )

    walk(
        hierarchy
    )

    return nodes


def node_matches_source(
    node: Dict[str, Any],
    source_law_name: str,
    source_mst: str,
    source_law_id: str,
) -> bool:

    if source_mst and node.get("mst") == source_mst:
        return True

    if source_law_id and node.get("law_id") == source_law_id:
        return True

    return bool(
        source_law_name
        and
        node.get("law_name") == source_law_name
    )


def ancestor_indexes(
    nodes: List[Dict[str, Any]],
    node_index: int,
) -> Set[int]:

    ancestors: Set[int] = set()

    parent = nodes[
        node_index
    ].get(
        "parent_index"
    )

    while isinstance(parent, int):

        if parent in ancestors:
            break

        ancestors.add(
            parent
        )

        parent = nodes[
            parent
        ].get(
            "parent_index"
        )

    return ancestors


def is_descendant(
    nodes: List[Dict[str, Any]],
    node_index: int,
    ancestor_index: int,
) -> bool:

    parent = nodes[
        node_index
    ].get(
        "parent_index"
    )

    visited: Set[int] = set()

    while isinstance(parent, int):

        if parent == ancestor_index:
            return True

        if parent in visited:
            return False

        visited.add(
            parent
        )

        parent = nodes[
            parent
        ].get(
            "parent_index"
        )

    return False


def classify_descendant(
    node: Dict[str, Any],
) -> str:

    law_name = normalize_text(
        node.get("law_name")
    )

    law_type = normalize_text(
        node.get("law_type")
    )

    if law_name.endswith("시행령"):
        return "시행령"

    if law_name.endswith("시행규칙"):
        return "시행규칙"

    if (
        node.get("category") == "시행령"
        and law_type == "대통령령"
    ):
        return "시행령"

    if node.get("category") == "시행규칙":
        return "시행규칙"

    return "하위법령"


def build_relation_item(
    source_law_name: str,
    node: Dict[str, Any],
    relation_type: str,
    retrieved_at: str,
) -> Dict[str, Any]:

    path = [
        normalize_text(item)
        for item in node.get(
            "path",
            [],
        )
        if normalize_text(item)
    ]

    description = (
        "법령 체계도에서 확인된 관계"
    )

    if path:
        description = (
            "법령 체계도 경로: "
            + " > ".join(path)
        )

    return {
        "relation_type": relation_type,
        "source_law_name": source_law_name,
        "target_law_name": normalize_text(
            node.get("law_name")
        ),
        "target_law_id": normalize_text(
            node.get("law_id")
        ),
        "target_mst": normalize_text(
            node.get("mst")
        ),
        "target_law_type": normalize_text(
            node.get("law_type")
        ),
        "ministry": "",
        "article_reference": "",
        "description": description,
        "official_link": sanitize_official_link(
            node.get("official_link")
        ),
        "retrieved_at": retrieved_at,
    }


def parse_direct_related_laws(
    value: Any,
    source_law_name: str,
    retrieved_at: str,
) -> List[Dict[str, Any]]:

    related: List[Dict[str, Any]] = []

    def walk(item: Any) -> None:

        if isinstance(item, list):

            for child in item:
                walk(child)

            return

        if not isinstance(item, dict):
            return

        info = parse_info(
            item
        )

        if info and not info.get(
            "is_administrative"
        ):

            related.append(
                build_relation_item(
                    source_law_name=source_law_name,
                    node={
                        **info,
                        "path": [
                            "관련법령"
                        ],
                    },
                    relation_type="관련법령",
                    retrieved_at=retrieved_at,
                )
            )

            return

        for child in item.values():
            walk(child)

    walk(value)

    return related


def deduplicate_relations(
    relations: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:

    final: List[Dict[str, Any]] = []

    seen = set()

    for relation in relations:

        key = (
            relation.get("relation_type"),
            relation.get("target_mst"),
            relation.get("target_law_id"),
            relation.get("target_law_name"),
        )

        if key in seen:
            continue

        seen.add(key)
        final.append(relation)

    return final


def parse_law_system_map(
    raw_data: Dict[str, Any],
    source_law_name: str,
    source_mst: str = "",
    source_law_id: str = "",
    include_administrative: bool = False,
) -> List[Dict[str, Any]]:

    root = get_system_map_root(
        raw_data
    )

    if not root:
        return []

    source_law_name = normalize_text(
        source_law_name
    )

    source_mst = normalize_text(
        source_mst
    )

    source_law_id = normalize_text(
        source_law_id
    )

    retrieved_at = datetime.now(
        timezone.utc
    ).isoformat()

    nodes = collect_hierarchy_nodes(
        root.get("상하위법"),
        include_administrative=(
            include_administrative
        ),
    )

    source_index = next(
        (
            index
            for index, node in enumerate(nodes)
            if node_matches_source(
                node=node,
                source_law_name=source_law_name,
                source_mst=source_mst,
                source_law_id=source_law_id,
            )
        ),
        None,
    )

    relations: List[Dict[str, Any]] = []

    if source_index is not None:

        ancestors = ancestor_indexes(
            nodes,
            source_index,
        )

        for index, node in enumerate(nodes):

            if index == source_index:
                continue

            relation_type = ""

            if index in ancestors:
                relation_type = "상위법령"

            elif is_descendant(
                nodes,
                index,
                source_index,
            ):
                relation_type = classify_descendant(
                    node
                )

            if not relation_type:
                continue

            relations.append(
                build_relation_item(
                    source_law_name=source_law_name,
                    node=node,
                    relation_type=relation_type,
                    retrieved_at=retrieved_at,
                )
            )

    relations.extend(
        parse_direct_related_laws(
            value=root.get("관련법령"),
            source_law_name=source_law_name,
            retrieved_at=retrieved_at,
        )
    )

    return deduplicate_relations(
        relations
    )
