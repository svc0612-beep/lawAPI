"""Public Python API: plan -> retrieve -> rerank -> generate -> verify -> commit."""
import re
import uuid
import html
import jsonschema
from datetime import datetime, timezone
from .config import Settings
from .model import OllamaJSONModel, OllamaEmbedder, ModelError
from .store import Store, ConflictError
from .schemas import PLAN, SELECTION
from .retrieval import Retriever
from .verify import verify_draft
from .types import Result
from .scope import exact_request, explicit_law_name
from services.law.summary_focus import focus_summary, extract_focus_terms, focus_labels

import os as _os


def _debug(msg):
    """
    환경변수 LAWMATE_DEBUG=1 일 때만 [DEBUG] 로그를 stderr 로 출력.
    Streamlit 콘솔에서 파이프라인 흐름을 즉시 추적하고 싶을 때 켠다.
    - 프로덕션 기본은 로그 없음 (성능·노이즈 방지)
    - 진단 필요 시: PowerShell 에서 $env:LAWMATE_DEBUG="1" 설정 후 재실행
    """
    if _os.environ.get("LAWMATE_DEBUG"):
        try:
            print(f"[DEBUG] {msg}", flush=True)
        except Exception:
            pass


def _prettify_summary(text_str):
    """
    profile summary 안의 [섹션 이름] 마커를 실제 개행 + 굵은 헤더로
    변환한다. 사용자가 죽 이어진 한 줄로 보지 않고 섹션 구분이 명확한
    답변을 볼 수 있게 하기 위함.
    - '[협의이혼 절차] (1) ...'  →  '\n\n**협의이혼 절차**\n\n(1) ...'
    """
    import re as _re_local
    s = str(text_str or "")
    s = _re_local.sub(r"\s*\[([^\]]+)\]\s*", r"\n\n**\1**\n\n", s)
    return s.strip()


SEARCH_REQUEST = re.compile(
    r"(?:찾아|검색|보여|원문|조문|법령|관련\s*법|판례|해석례|어떤\s*법|무슨\s*법)"
)
SOURCE_MANIPULATION = re.compile(
    r"(?:지어내|꾸며|날조|출처\s*무시|근거\s*없이|가짜\s*판례)"
)
FOLLOW_UP_HINT = re.compile(
    # (a) 문두 지시·연결어
    r"^(?:그럼|그러면|그래서|그리고|"
    r"그\s*(?:경우|사건|사람|법|조문|것|거|건|때|쪽)|"
    r"그거|그건|그것|이거|이건|이것|"
    r"위(?:\s*(?:조항|조문|법|사건|경우))?|"
    r"앞(?:의|서)|방금|아까|"
    r"더|또|추가로|자세히|그럼\s*(?:만약|만일))|"
    # (b) 당사자 지칭 + 조건 표현
    r"(?:피해자|가해자|당사자|회사|근로자|배우자|자녀|상속인)가?\s*.*(?:면|경우|때)[?？]?$"
)
NEW_TOPIC_HINT = re.compile(r"(?:새\s*주제|새\s*질문|다른\s*질문|별개(?:의)?\s*사건)")


def explicit_search_request(question):
    return bool(SEARCH_REQUEST.search(question)) and not SOURCE_MANIPULATION.search(question)


def _strip_quotes(text):
    """
    Streamlit UI 가 사용자 입력을 따옴표(", ') 로 감싸는 경우가 있어
    정규식 매칭 실패를 방지하기 위한 정제 헬퍼.
    앞뒤의 큰따옴표·작은따옴표·공백을 반복 제거한다.
    """
    s = str(text or "")
    while s:
        stripped = s.strip().strip('"').strip("'").strip("\u201c").strip("\u201d").strip("\u2018").strip("\u2019")
        if stripped == s:
            break
        s = stripped
    return s


def likely_follow_up(question, history):
    """
    지시대명사·연결어로 시작하거나, 이전 대화가 있는 상태에서
    다음 중 하나에 해당하면 후속 질문으로 판정한다.
     - 조사(은/는/이/가/...) + 물음표로 끝나는 짧은 질문(20자 이하)
     - FOCUS_KEYWORDS(대리인·위자료·청구기간 등)의 명사를 포함하는
       짧은 질문(15자 이하) 예: '대리인 꼭 필요해?', '위자료 얼마?'
    Streamlit UI 가 입력에 따옴표를 붙이는 케이스는 _strip_quotes 로 정제.
    """
    q = _strip_quotes(question)
    if not history or NEW_TOPIC_HINT.search(q):
        return False
    # 명시적 지시대명사·연결어 감지
    if FOLLOW_UP_HINT.search(q):
        return True
    # 짧은 조사형 후속 질문 감지 (history 있을 때만)
    if len(q) <= 20 and re.search(r"[?？]$", q) and re.search(r"(?:은|는|이|가|을|를|도|만|도|과|와)\s*(?:\S{0,10})[?？]$", q):
        return True
    # 짧은 질문에 FOCUS_KEYWORDS 명사가 포함되면 후속 질문일 확률 높음
    # 예: "대리인 꼭 필요해?" -> "대리인" 매칭
    if len(q) <= 15 and re.search(r"[?？]$", q):
        try:
            from services.law.summary_focus import FOCUS_KEYWORDS
            if any(key in q for key in FOCUS_KEYWORDS.keys()):
                return True
        except ImportError:
            pass
    return False


def literal_facts(messages):
    facts = {}
    for i, message in enumerate(messages):
        for key, pattern in [("age", r"(?<!\d)(\d{1,2})\s*(?:살|세)(?=$|[\s,.!?]|이|인|였|입|의|가|는|를|에|미만|이상)"),
                             ("workers", r"(?:근로자|직원|상시근로자)(?:가|는|수는)?\s*(\d+)\s*명")]:
            matches = re.findall(pattern, message)
            if matches:
                facts[key] = {"value": matches[-1], "source_user_turn": i, "status": "user_assertion"}
    return facts


def markdown_text(text):
    return re.sub(r"([\\`*{}\[\]()#+!_])", r"\\\1", html.escape(text))


class LegalRAG:
    def __init__(self, settings=None, model=None, store=None, online=None):
        self.settings = settings or Settings.from_env()
        self.store = store or Store(self.settings.database)
        self.model = model or OllamaJSONModel(self.settings.model, self.settings.ollama_url, self.settings.timeout_seconds)
        embedder = OllamaEmbedder(self.settings.embedding_model, self.settings.ollama_url) if self.settings.embedding_model else None
        self.retriever = Retriever(self.store, self.settings, self.model, embedder)
        if online is None and self.settings.online_retrieval:
            from .ingest import OfficialAPIRetriever
            online = OfficialAPIRetriever(self.store)
        self.online = online

    def create_session(self, user_id):
        return self.store.create_session(user_id)

    def ask(self, user_id, session_id, question, request_id=None, new_topic=False):
        if not isinstance(question, str) or not question.strip() or len(question) > self.settings.max_question_chars:
            raise ValueError("question_length_invalid")
        question = question.strip()
        request_id = request_id or uuid.uuid4().hex
        if not isinstance(request_id, str) or not request_id or len(request_id) > 128:
            raise ValueError("request_id_invalid")
        revision, history, replay, prior_responses = self.store.snapshot(user_id, session_id, request_id, question, self.settings.history_turns)
        if replay:
            if replay.get("diagnostics", {}).get("new_topic", False) != new_topic:
                raise ConflictError("request_id_reused_with_different_context")
            return replay
        if new_topic:
            history = []
        bounded, used = [], len(question)
        for message in reversed(history):
            if used + len(message) > self.settings.max_context_chars:
                break
            bounded.append(message)
            used += len(message)
        truncated = len(bounded) < len(history)
        history = list(reversed(bounded))
        response = Result("abstain", session_id, request_id, "확인 가능한 근거가 부족해 답변을 보류합니다.")
        response.diagnostics = {"pipeline_version": "legal-rag-v1", "model": self.settings.model,
                                "new_topic": new_topic, "context_reset": new_topic,
                                "history_user_turns": len(history), "history_truncated": truncated,
                                "corpus_scope": "ingested_official_documents_only"}
        try:
            response.diagnostics["stage"] = "plan"
            direct = exact_request(question, index=self.retriever.exact_index) is not None
            if direct:
                # An explicit law/article identity is safer and faster when it
                # bypasses the model entirely.
                plan = {"query": question, "follow_up": False, "needs_clarification": False, "questions": []}
                response.diagnostics["plan_strategy"] = "exact_reference"
            else:
                # Qwen proposes an additional search query for both the first
                # natural-language turn and later follow-ups.  The original
                # user text is still included in retrieval below, so the model
                # cannot silently replace or narrow the user's issue.
                plan = self.model.generate("plan", {"question": question, "user_history": history,
                                                   "facts": literal_facts(history + [question])}, PLAN)
                response.diagnostics["plan_strategy"] = "multiturn_model" if history else "standalone_model_expansion"
            jsonschema.validate(plan, PLAN)
            source_text = " ".join(history[-2:] + [question])
            plan_limit = max(80, len(source_text) * 4)
            original_law = explicit_law_name(question)
            planned_law = explicit_law_name(plan["query"])
            if len(plan["query"]) > plan_limit:
                plan["query"] = question
                response.diagnostics["plan_sanitized"] = "excessive_expansion"
            elif original_law and planned_law and original_law != planned_law:
                plan["query"] = question
                response.diagnostics["plan_sanitized"] = "law_identity_changed"
            if not history:
                plan["follow_up"] = False
            elif likely_follow_up(question, history):
                # The small local model can miss short elliptical Korean
                # follow-ups.  This bounded rule only restores context; it
                # never creates a legal fact or conclusion.
                plan["follow_up"] = True
                response.diagnostics["follow_up_guard"] = "deterministic_context_restore"
            if explicit_search_request(question) or plan["follow_up"]:
                # A request to locate sources is answerable as retrieval even
                # when case-specific facts are insufficient for application.
                plan["needs_clarification"] = False
            scope = history if plan["follow_up"] else []
            response.diagnostics["context_reset"] = new_topic or not plan["follow_up"]
            facts = literal_facts(scope + [question])
            response.diagnostics.update(query=plan["query"], facts=facts, follow_up=plan["follow_up"])
            allowed_numbers = {int(n) for n in re.findall(r"\d+", " ".join(scope + [question]))}
            query_facts = literal_facts([plan["query"]])
            changed_facts = any(key in facts and value["value"] != facts[key]["value"] for key, value in query_facts.items())
            if re.search(r"(?:19|20)\d{2}\s*(?:년|[-./])|작년|재작년|지난해|예전|개정\s*전|\d+\s*(?:년|개월|달|일)\s*전", " ".join(scope + [question])):
                response.status = "temporal_review_required"
                response.answer = "시점이 지정된 사건은 당시 시행법과 개정 부칙 확인이 필요합니다. 현재 확보한 자료만으로 적용법이나 처벌을 답하지 않습니다."
            elif changed_facts or {int(n) for n in re.findall(r"\d+", plan["query"])} - allowed_numbers:
                response.status = "clarify"
                response.answer = "검색 질문을 원래 사실관계와 일치시키지 못했습니다. 사건과 확인하려는 내용을 다시 구체적으로 알려주세요."
            elif plan["needs_clarification"]:
                response.status = "clarify"
                response.answer = "답변에 필요한 사실관계가 명확하지 않습니다. 누구의 어떤 행위인지와 사건 발생 시점을 알려주세요."
                response.questions = ["이전 사건에 대한 후속 질문인가요, 새로운 사건인가요?", "확인하려는 행위와 사건 발생일을 알려주세요."]
            else:
                online_terms = []
                term_sources = {}
                if self.online:
                    # Online expansion starts from user-authored text and a
                    # bounded prior context, not from a model rewrite.
                    online_query = " ".join((scope[-2:] if plan["follow_up"] else []) + [question])
                    if direct and hasattr(self.online, "refresh_exact"):
                        response.diagnostics["online"] = self.online.refresh_exact(question)
                    else:
                        response.diagnostics["online"] = self.online.refresh(online_query, current_question=question)

                    # ---- follow-up hint 컨텍스트 이어받기 ----
                    # follow-up 이면서 현재 질문으로 profile 매칭이 실패해
                    # hint_summaries 가 비었으면, 직전 turn 의 hint 를 재활용.
                    # 조문·판례 retrieval 도 이전 profile 의 terms 에 의존하므로
                    # query_terms 와 query_term_sources 까지 함께 이어받는다.
                    _debug(f"question={question!r}, follow_up={plan.get('follow_up')}, "
                           f"prior_responses={len(prior_responses)}, "
                           f"current_hints={len(response.diagnostics.get('online', {}).get('hint_summaries') or [])}")
                    if plan.get("follow_up") and prior_responses:
                        _cur_online = response.diagnostics["online"] or {}
                        if not (_cur_online.get("hint_summaries") or []):
                            for _prev in prior_responses:
                                _prev_online = ((_prev or {}).get("diagnostics") or {}).get("online") or {}
                                _prev_hs = _prev_online.get("hint_summaries") or []
                                if _prev_hs:
                                    _cur_online["hint_summaries"] = _prev_hs
                                    # profile / 사건종류 힌트
                                    if not _cur_online.get("hint_profiles"):
                                        _cur_online["hint_profiles"] = _prev_online.get("hint_profiles") or []
                                    if not _cur_online.get("preferred_case_types"):
                                        _cur_online["preferred_case_types"] = _prev_online.get("preferred_case_types") or []
                                    # 조문 검색에 쓰이는 query_terms 도 이어받는다.
                                    # 없으면 retrieval_query 가 좁아져 조문 미발견 -> abstain
                                    if not _cur_online.get("query_terms"):
                                        _cur_online["query_terms"] = _prev_online.get("query_terms") or []
                                    if not _cur_online.get("query_term_sources"):
                                        _cur_online["query_term_sources"] = _prev_online.get("query_term_sources") or {}
                                    response.diagnostics["online"] = _cur_online
                                    response.diagnostics["hint_context_inherited_from_prior_turn"] = True
                                    break

                    online_terms = response.diagnostics["online"].get("query_terms", [])
                    term_sources = response.diagnostics["online"].get("query_term_sources", {})
                    self.retriever.refresh_exact_index()
                reviewed_terms = [
                    term for term in term_sources.get("reviewed_hints", [])
                    if isinstance(term, str) and term.strip()
                ]
                preserved_context = scope[-2:] if plan["follow_up"] else []
                retrieval_query = " ".join(preserved_context + [question, plan["query"]] + online_terms)
                response.diagnostics["retrieval_query"] = retrieval_query
                response.diagnostics["validated_expansion_terms"] = online_terms
                response.diagnostics["trusted_expansion_terms"] = reviewed_terms
                if self.online:
                    response.diagnostics["query_term_sources"] = term_sources
                hits, diagnostics = self.retriever.retrieve(
                    retrieval_query,
                    trusted_terms=reviewed_terms,
                )
                response.diagnostics.update(diagnostics)
                response.diagnostics["stage"] = "rerank"
                if diagnostics.get("exact_request"):
                    evidence = [hits[0].document] if len(hits) == 1 else []
                    rank_diagnostics = {"reranker": "exact_identity", "selected_count": len(evidence),
                                        "reason": "exact_single_source" if evidence else "missing_or_ambiguous_version"}
                else:
                    evidence, rank_diagnostics = self.retriever.rerank(
                        retrieval_query,
                        hits,
                        original_question=question,
                        # Only human-reviewed mappings may bridge a lifestyle
                        # phrase to a legal article title.  A Qwen proposal can
                        # improve recall but cannot by itself authorize output.
                        planned_query=" ".join(reviewed_terms) if reviewed_terms else None,
                        trusted_terms=reviewed_terms,
                    )
                response.diagnostics.update(rank_diagnostics)
                if evidence:
                    response.diagnostics["stage"] = "generate"
                    if diagnostics.get("exact_request"):
                        selection = {"status": "answer", "evidence_indices": [0]}
                        response.diagnostics["generation"] = "exact_requested_source"
                    else:
                        selection = self.model.generate("generate", {"question": question, "query": plan["query"], "facts": facts,
                            "evidence": [{"index": i, "title": d.title, "text": d.text, "kind": d.kind} for i, d in enumerate(evidence)]}, SELECTION)
                        response.diagnostics["generation"] = "qwen_evidence_selection"
                    jsonschema.validate(selection, SELECTION)
                    # The model selects evidence; the server supplies original text.
                    # No free-form model text is eligible for publication.
                    draft = {"status": selection["status"], "claims": [], "questions": []}
                    for index in selection["evidence_indices"]:
                        if index >= len(evidence):
                            draft["claims"].append({"evidence_id": "unknown", "text": "invalid", "quote": "invalid"})
                        else:
                            d = evidence[index]
                            draft["claims"].append({"evidence_id": d.id, "text": d.text, "quote": d.text})
                    verified = verify_draft(draft, evidence)
                    response.diagnostics["stage"] = "verify"
                    response.verification = verified
                    if not verified["passed"]:
                        response.status = "verification_failed"
                        response.answer = "생성된 답변이 원문 검증을 통과하지 못해 공개하지 않습니다."
                    elif draft["status"] == "answer":
                        response.status = "grounded_excerpt"
                        response.citations = verified["claims"]

                        # ---------------------------------------------------------
                        # 통일된 답변 템플릿 (2026-09-21)
                        # 1. 핵심 요약 (hint_summaries 또는 기본 안내)
                        # 2. 근거 조문 (시행일 포함)
                        # 3. 관련 판례 (검증된 판례만, 있을 때)
                        # 4. 참고 문헌 (국회도서관, 있을 때)
                        # 5. 유의사항 (항상)
                        # ---------------------------------------------------------
                        online = response.diagnostics.get("online", {}) or {}
                        hint_summaries = online.get("hint_summaries", []) or []
                        verified_precedents = online.get("precedents", []) or []
                        bibliography = online.get("bibliography", []) or []

                        def _fmt_date(value):
                            s = str(value or "").strip()
                            if len(s) == 8 and s.isdigit():
                                return f"{s[:4]}-{s[4:6]}-{s[6:]}"
                            return s

                        sections = []

                        # 1. 핵심 요약 (follow-up이면 초점 섹션만 발췌)
                        _is_follow_up = bool(plan.get("follow_up"))
                        _focus_terms = tuple(online.get("query_terms", []) or ())
                        _focused_summaries = [
                            focus_summary(s, question, follow_up=_is_follow_up, extra_terms=_focus_terms)
                            for s in hint_summaries
                        ] if hint_summaries else []

                        # focus 배지 조립: 실제로 축소가 적용된 경우에만
                        _focus_badge = ""
                        if _is_follow_up and _focused_summaries and hint_summaries:
                            _shrunk = any(
                                len(f) < len(o)
                                for f, o in zip(_focused_summaries, hint_summaries)
                            )
                            if _shrunk:
                                # 배지엔 대표 명사(key)만 노출 (유사어 나열은 검색용)
                                _focus_names = focus_labels(question, _focus_terms)
                                if _focus_names:
                                    # 대표 명사 2개까지만 표시 (너무 길어지지 않게)
                                    _label = " · ".join(_focus_names[:2])
                                    _focus_badge = f"> 🔎 이 답변은 **{_label}** 을(를) 중심으로 초점을 맞춘 요약입니다.\n\n"

                        if _focused_summaries:
                            _pretty = [_prettify_summary(s) for s in _focused_summaries]
                            sections.append(
                                "### 📌 핵심 요약\n\n"
                                + _focus_badge
                                + "\n\n".join(_pretty)
                            )
                        else:
                            sections.append(
                                "### 📌 핵심 요약\n\n"
                                "질문과 관련된 법령 원문을 찾았습니다. "
                                "구체적인 요건과 처벌은 아래 조문 원문에서 확인하세요."
                            )

                        # 2. 근거 조문
                        article_lines = ["### 📎 근거 조문"]
                        for idx, claim in enumerate(response.citations, 1):
                            title = markdown_text(claim.get("title", ""))
                            valid_from = _fmt_date(claim.get("valid_from", ""))
                            header = f"**[{idx}] {title}**"
                            if valid_from:
                                header += f" · 시행 {valid_from}"
                            article_lines.append(header)
                            article_lines.append(
                                "\n".join("> " + markdown_text(line) for line in claim["text"].splitlines())
                            )
                            article_lines.append(f"[국가법령정보센터 원문]({claim['url']})")
                        sections.append("\n\n".join(article_lines))

                        # 3. 관련 판례 (최대 3건, 없으면 안내)
                        if not verified_precedents:
                            _prec_notice_lines = ["### ⚖️ 관련 판례"]
                            if bibliography:
                                _prec_notice_lines.append(
                                    "이번 조회에서 대법원·헌법재판소의 검증된 판례를 확보하지 못했습니다. "
                                    "아래 **참고 문헌** 섹션의 국회도서관 자료와 조문 원문을 함께 참고하세요."
                                )
                            else:
                                _prec_notice_lines.append(
                                    "이번 조회에서 관련 판례를 확보하지 못했습니다. "
                                    "판례의 존재 여부를 조회에서 확정할 수 없다는 뜻이며, "
                                    "구체 사건에 대해서는 법률 전문가와 상의하세요."
                                )
                            sections.append("\n\n".join(_prec_notice_lines))
                        if verified_precedents:
                            prec_lines = ["### ⚖️ 관련 판례"]
                            for prec in verified_precedents[:3]:
                                court = prec.get("court_name", "")
                                case_number = prec.get("case_number", "")
                                dd = _fmt_date(prec.get("decision_date", ""))
                                case_type = prec.get("case_type", "")

                                header_parts = [x for x in [court, case_number] if x]
                                header = "- **" + " ".join(header_parts) + "**"
                                if dd:
                                    header += f" ({dd})"
                                if case_type:
                                    header += f" · {case_type}"
                                prec_lines.append(header)

                                summary_text = str(prec.get("summary", "") or "")
                                summary_text = re.sub(r"<br\s*/?>", " ", summary_text, flags=re.I)
                                summary_text = re.sub(r"\s+", " ", summary_text).strip()
                                if summary_text:
                                    if len(summary_text) > 220:
                                        summary_text = summary_text[:220] + "…"
                                    prec_lines.append(f"  > {summary_text}")

                                link = prec.get("official_link", "")
                                if link:
                                    prec_lines.append(f"  [판례 원문 열기]({link})")
                            sections.append("\n\n".join(prec_lines))

                        # 4. 참고 문헌 (있을 때)
                        if bibliography:
                            biblio_lines = ["### 📚 참고 문헌"]
                            for b in bibliography[:3]:
                                b_title = markdown_text(str(b.get("title", "") or ""))[:120]
                                b_url = b.get("url", "")
                                if b_url:
                                    biblio_lines.append(f"- {b_title} — [국회도서관]({b_url})")
                                else:
                                    biblio_lines.append(f"- {b_title}")
                            sections.append("\n\n".join(biblio_lines))

                        # 5. 유의사항 (항상)
                        sections.append(
                            "### ⚠️ 유의사항\n\n"
                            "사건 발생일·구체적 사실관계에 따라 적용 법령과 결론이 달라질 수 있습니다. "
                            "위 조문 원문은 법정형·요건을 확인할 수 있는 자료이며, "
                            "실제 선고형·양형은 개별 사건마다 다릅니다. "
                            "최종 판단은 법률 전문가와 상의하세요."
                        )

                        response.answer = "\n\n".join(sections)
                    else:
                        # Qwen이 status="answer" 반환 못 했더라도
                        # rerank된 evidence 가 있으면 자동으로 답변 조립
                        # (rerank는 이미 관련성 검증된 후보만 통과시킴)
                        if evidence:
                            # 재-verify: 첫 두 개 evidence 로 draft 재구성
                            _auto_draft = {
                                "status": "answer",
                                "claims": [
                                    {"evidence_id": d.id, "text": d.text, "quote": d.text}
                                    for d in evidence[:min(2, len(evidence))]
                                ],
                                "questions": [],
                            }
                            _auto_verified = verify_draft(_auto_draft, evidence)
                            if _auto_verified["passed"]:
                                # 자동 답변 성공 → grounded_excerpt 로 승격
                                response.status = "grounded_excerpt"
                                response.verification = _auto_verified
                                response.citations = _auto_verified["claims"]
                                response.diagnostics["auto_selection"] = "qwen_status_not_answer_fallback"

                                # 위 grounded_excerpt 블록과 동일한 렌더링
                                online = response.diagnostics.get("online", {}) or {}
                                hint_summaries = online.get("hint_summaries", []) or []
                                verified_precedents = online.get("precedents", []) or []
                                bibliography = online.get("bibliography", []) or []

                                def _fmt_date_auto(value):
                                    s = str(value or "").strip()
                                    if len(s) == 8 and s.isdigit():
                                        return f"{s[:4]}-{s[4:6]}-{s[6:]}"
                                    return s

                                sections = []
                                # follow-up이면 초점 섹션만 발췌
                                _is_follow_up2 = bool(plan.get("follow_up"))
                                _focus_terms2 = tuple(online.get("query_terms", []) or ())
                                _focused_summaries2 = [
                                    focus_summary(s, question, follow_up=_is_follow_up2, extra_terms=_focus_terms2)
                                    for s in hint_summaries
                                ] if hint_summaries else []

                                # focus 배지 (auto-fallback 경로)
                                _focus_badge2 = ""
                                if _is_follow_up2 and _focused_summaries2 and hint_summaries:
                                    _shrunk2 = any(
                                        len(f) < len(o)
                                        for f, o in zip(_focused_summaries2, hint_summaries)
                                    )
                                    if _shrunk2:
                                        _focus_names2 = focus_labels(question, _focus_terms2)
                                        if _focus_names2:
                                            _label2 = " · ".join(_focus_names2[:2])
                                            _focus_badge2 = f"> 🔎 이 답변은 **{_label2}** 을(를) 중심으로 초점을 맞춘 요약입니다.\n\n"

                                if _focused_summaries2:
                                    _pretty2 = [_prettify_summary(s) for s in _focused_summaries2]
                                    sections.append("### 📌 핵심 요약\n\n" + _focus_badge2 + "\n\n".join(_pretty2))
                                else:
                                    sections.append(
                                        "### 📌 핵심 요약\n\n"
                                        "질문과 관련된 법령 원문을 찾았습니다. "
                                        "구체적인 요건과 처벌은 아래 조문 원문에서 확인하세요."
                                    )

                                article_lines = ["### 📎 근거 조문"]
                                for idx, claim in enumerate(response.citations, 1):
                                    title = markdown_text(claim.get("title", ""))
                                    valid_from = _fmt_date_auto(claim.get("valid_from", ""))
                                    header = f"**[{idx}] {title}**"
                                    if valid_from:
                                        header += f" · 시행 {valid_from}"
                                    article_lines.append(header)
                                    article_lines.append(
                                        "\n".join("> " + markdown_text(line) for line in claim["text"].splitlines())
                                    )
                                    article_lines.append(f"[국가법령정보센터 원문]({claim['url']})")
                                sections.append("\n\n".join(article_lines))

                                if not verified_precedents:
                                    _prec_notice_lines2 = ["### ⚖️ 관련 판례"]
                                    if bibliography:
                                        _prec_notice_lines2.append(
                                            "이번 조회에서 대법원·헌법재판소의 검증된 판례를 확보하지 못했습니다. "
                                            "아래 **참고 문헌** 섹션의 국회도서관 자료와 조문 원문을 함께 참고하세요."
                                        )
                                    else:
                                        _prec_notice_lines2.append(
                                            "이번 조회에서 관련 판례를 확보하지 못했습니다. "
                                            "판례의 존재 여부를 조회에서 확정할 수 없다는 뜻이며, "
                                            "구체 사건에 대해서는 법률 전문가와 상의하세요."
                                        )
                                    sections.append("\n\n".join(_prec_notice_lines2))
                                if verified_precedents:
                                    prec_lines = ["### ⚖️ 관련 판례"]
                                    for prec in verified_precedents[:3]:
                                        court = prec.get("court_name", "")
                                        case_number = prec.get("case_number", "")
                                        dd = _fmt_date_auto(prec.get("decision_date", ""))
                                        case_type = prec.get("case_type", "")
                                        header_parts = [x for x in [court, case_number] if x]
                                        header = "- **" + " ".join(header_parts) + "**"
                                        if dd:
                                            header += f" ({dd})"
                                        if case_type:
                                            header += f" · {case_type}"
                                        prec_lines.append(header)
                                        summary_text = str(prec.get("summary", "") or "")
                                        summary_text = re.sub(r"<br\s*/?>", " ", summary_text, flags=re.I)
                                        summary_text = re.sub(r"\s+", " ", summary_text).strip()
                                        if summary_text:
                                            if len(summary_text) > 220:
                                                summary_text = summary_text[:220] + "…"
                                            prec_lines.append(f"  > {summary_text}")
                                        link = prec.get("official_link", "")
                                        if link:
                                            prec_lines.append(f"  [판례 원문 열기]({link})")
                                    sections.append("\n\n".join(prec_lines))

                                if bibliography:
                                    biblio_lines = ["### 📚 참고 문헌"]
                                    for b in bibliography[:3]:
                                        b_title = markdown_text(str(b.get("title", "") or ""))[:120]
                                        b_url = b.get("url", "")
                                        if b_url:
                                            biblio_lines.append(f"- {b_title} — [국회도서관]({b_url})")
                                        else:
                                            biblio_lines.append(f"- {b_title}")
                                    sections.append("\n\n".join(biblio_lines))

                                sections.append(
                                    "### ⚠️ 유의사항\n\n"
                                    "사건 발생일·구체적 사실관계에 따라 적용 법령과 결론이 달라질 수 있습니다. "
                                    "위 조문 원문은 법정형·요건을 확인할 수 있는 자료이며, "
                                    "실제 선고형·양형은 개별 사건마다 다릅니다. "
                                    "최종 판단은 법률 전문가와 상의하세요."
                                )
                                response.answer = "\n\n".join(sections)
                            else:
                                # verify 실패 → 기존 fallback
                                response.status = draft["status"]
                                response.answer = "근거 또는 사실관계가 충분하지 않습니다. 사건 발생 시점, 행위와 조건을 추가로 확인해야 합니다."
                        else:
                            response.status = draft["status"]
                            response.answer = "근거 또는 사실관계가 충분하지 않습니다. 사건 발생 시점, 행위와 조건을 추가로 확인해야 합니다."
        except (ModelError, jsonschema.ValidationError) as error:
            response.status = "model_error"
            response.answer = "모델 응답을 정상적으로 검증할 수 없어 답변을 보류합니다."
            safe_codes = {"model_timeout", "model_schema_error", "incomplete_generation", "invalid_reranker_citation", "model_transport_or_schema_error"}
            response.diagnostics["failure"] = str(error) if str(error) in safe_codes else "model_transport_schema_or_ranking_error"
        # ---- context_carryover fallback ----
        # follow-up 이면서 hint 이어받기가 성공했는데도 verify/SELECTION 이
        # 실패해 abstain 이면, 이어받은 요약만이라도 사용자에게 노출한다.
        # 이 요약은 이전 turn 에서 이미 검증된 조문에 근거한 정형 요약이므로
        # 새 사실을 만들어내지 않으며, 초점 배지로 어떤 세부 주제에 답하는지
        # 명시한다.
        if (
            response.status in ("abstain", "clarify")
            and response.diagnostics.get("hint_context_inherited_from_prior_turn")
        ):
            _online = response.diagnostics.get("online") or {}
            _hint_summaries = _online.get("hint_summaries") or []
            if _hint_summaries:
                _query_terms = tuple(_online.get("query_terms") or ())
                _focused = [
                    focus_summary(s, question, follow_up=True, extra_terms=_query_terms)
                    for s in _hint_summaries
                ]
                _focus_names = focus_labels(question, _query_terms)
                _badge = ""
                if _focus_names:
                    _label = " · ".join(_focus_names[:2])
                    _badge = f"> 🔎 이 답변은 **{_label}** 을(를) 중심으로 초점을 맞춘 요약입니다.\n\n"
                _pretty_c = [_prettify_summary(s) for s in _focused]
                _summary_block = "### 📌 핵심 요약\n\n" + _badge + "\n\n".join(_pretty_c)
                _notice = (
                    "### ⚠️ 유의사항\n\n"
                    "이번 질문에는 새로 검증한 조문·판례를 붙이지 못했습니다. "
                    "위 요약은 직전 대화에서 이미 검증된 내용을 이어 보여드리는 것이며, "
                    "구체 사건 적용은 조문 원문을 직접 확인해야 합니다."
                )
                response.status = "context_carryover"
                response.answer = _summary_block + "\n\n" + _notice
                response.diagnostics["carryover_reason"] = "hint_inherited_but_verify_failed"
                _debug(f"context_carryover fallback triggered: profile={_online.get('hint_profiles')}")

        # ---- advisory_summary fallback ----
        # 첫 질문(follow-up 아님)이고 profile 매칭은 성공(hint_summaries 있음)
        # 인데도 Qwen 이 clarify 로 판정한 경우.
        # 사용자에게 "사실관계 알려주세요" 만 던지지 말고 매칭된 profile 요약
        # (사람이 검토한 정형 텍스트)을 참조 정보로 제시하고, 사실관계를 함께
        # 물어본다. 조문·판례 없이 요약만 노출하므로 새 법률 결론을
        # 생성하지 않는다.
        if (
            response.status in ("clarify", "abstain")
            and not response.diagnostics.get("hint_context_inherited_from_prior_turn")
            and not response.diagnostics.get("follow_up")
        ):
            _online = response.diagnostics.get("online") or {}
            _hint_summaries = _online.get("hint_summaries") or []
            # online.refresh 가 hint 를 못 저장했으면 여기서 직접 search_hints 재실행.
            # (Ollama 실패, 캐시 부재 등으로 online.hint_summaries 가 비는 케이스 대비)
            if not _hint_summaries:
                try:
                    from services.law.search_hints import search_hints as _sh
                    _direct_hints = _sh(question)
                    _hint_summaries = _direct_hints.get("summaries") or []
                    if _hint_summaries:
                        response.diagnostics["advisory_hints_recovered_directly"] = True
                except Exception:
                    pass
            if _hint_summaries:
                _pretty_a = [_prettify_summary(s) for s in _hint_summaries]
                _summary_block = "### 📌 핵심 요약\n\n" + "\n\n".join(_pretty_a)
                # 기존 clarify 안내(response.questions)가 있으면 그대로 활용
                _questions = getattr(response, "questions", []) or []
                _q_lines = ""
                if _questions:
                    _q_lines = "\n\n**정확한 답변을 위해 알려주세요**\n" + "\n".join(f"- {q}" for q in _questions)
                _notice = (
                    "### ⚠️ 유의사항\n\n"
                    "구체적인 사실관계가 명확하지 않아 아래 요약을 참조로 제시합니다. "
                    "위 요약은 사람이 검토한 정형 안내이며, 이번 질문의 구체 사건에 그대로 적용된다는 뜻은 아닙니다. "
                    "실제 법 적용은 사건별 사실관계·시점·개별 요건에 따라 달라집니다."
                    + _q_lines
                )
                response.status = "advisory_summary"
                response.answer = _summary_block + "\n\n" + _notice
                response.diagnostics["carryover_reason"] = "clarify_with_matched_profile"
                _debug(f"advisory_summary fallback triggered: recovered_directly={response.diagnostics.get('advisory_hints_recovered_directly', False)}")

        data = response.to_dict()
        self.store.commit_turn(user_id, session_id, revision, request_id, question, data)
        return data
