"""Conservative lexical topic gate; explicitly not a semantic/legal verifier."""
import re

STOP = {"관련", "관한", "대한", "원문", "조문", "법령", "판례", "내용", "질문", "법과", "법", "관해",
        "찾아줘", "찾아주세요", "보여줘", "알려줘", "알려주세요", "설명해줘", "어떻게", "어떤", "있는",
        "경우", "다른", "사람", "사람의", "때", "그", "그건", "그리고", "정정할게", "이야", "나이", "법원", "번호"}


def query_terms(question, law_names=()):
    text = re.sub(r"제\s*\d+\s*조(?:\s*의\s*\d+)?", " ", question)
    for name in sorted(law_names, key=len, reverse=True):
        text = text.replace(name, " ")
    # Remove a user-facing alias when the document carries the canonical law
    # name (for example, ``헌법`` -> ``대한민국헌법``).  Otherwise the alias
    # itself becomes an issue word and rejects the correct article title.
    try:
        from agents.query_analyzer import LAW_NAME_ALIASES
        for alias, canonical in LAW_NAME_ALIASES.items():
            if canonical in law_names:
                text = text.replace(alias, " ")
    except ImportError:
        pass
    terms = []
    for word in re.findall(r"[가-힣]+", text):
        word = re.sub(r"(?:을|를|은|는|이|가|에|의)$", "", word) if len(word) > 2 else word
        if len(word) >= 2 and word not in STOP and not word.endswith(("줘", "주세요", "인가요", "이야")):
            terms.append(word)
    return list(dict.fromkeys(terms))


def title_anchor(document, question):
    name = document.metadata.get("law_name", "")
    terms = query_terms(question, [name] if name else [])
    title = document.title.replace(name, "") if name else document.title
    compact_title = re.sub(r"\s+|의", "", title)
    # Literal title anchor is intentionally strict. Synonyms require validated
    # semantic retrieval/gold data rather than trusting a model relevance score.
    return bool(terms) and all(term in title or term in compact_title for term in terms)


def build_exact_index(documents):
    normative = {"statute", "administrative_rule", "local_ordinance"}
    index = {}
    for document in documents:
        if document.kind not in normative:
            continue
        name = document.metadata.get("law_name", "")
        number = document.metadata.get("article_number")
        if name and number is not None:
            index.setdefault(name, {}).setdefault((int(number), int(document.metadata.get("sub_article_number") or 0)), []).append(document)
    return index


def explicit_law_name(question, law_names=()):
    """Return the canonical law name explicitly present in user text."""
    compact = re.sub(r"\s+", "", question)
    literal = [
        name for name in law_names
        if name and re.sub(r"\s+", "", name) in compact
    ]
    if literal:
        return max(literal, key=lambda name: len(re.sub(r"\s+", "", name)))
    # A subordinate statute must not collapse to its parent merely because a
    # known parent-law alias is a prefix of the full name.
    subordinate = re.search(
        r"([가-힣A-Za-z0-9ㆍ·]{1,40}법)\s*(시행령|시행규칙)(?=$|[^가-힣])",
        question,
    )
    if subordinate:
        return f"{subordinate.group(1)} {subordinate.group(2)}"
    try:
        from agents.query_analyzer import extract_law_name
        return extract_law_name(question)
    except ImportError:
        return None


def exact_request(question, documents=None, index=None):
    compact = re.sub(r"\s+", "", question)
    index = index if index is not None else build_exact_index(documents or [])
    canonical = explicit_law_name(question, index.keys())
    if canonical in index:
        names = [canonical]
    else:
        names = [name for name in index if name and re.sub(r"\s+", "", name) in compact]
    if not names:
        return None
    name = max(names, key=len)
    article = re.search(r"제?\s*(\d+)\s*조(?:\s*의\s*(\d+))?", question)
    if not article:
        return None
    number, sub = int(article[1]), int(article[2] or 0)
    return sorted(index[name].get((number, sub), []), key=lambda d: d.id)
