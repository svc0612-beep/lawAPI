"""Application adapter for the verified multi-turn legal RAG backend.

Qwen is allowed to plan searches and select source units.  It is never allowed
to publish free-form legal claims: ``legal_rag`` verifies and renders the
official source text after the model step.
"""
from functools import lru_cache
import os

from legal_rag import LegalRAG, Settings
from legal_rag.ingest import OfficialAPIRetriever
from legal_rag.store import Store, ConflictError


@lru_cache(maxsize=1)
def get_legal_rag():
    settings = Settings.from_env()
    store = Store(settings.database)

    # A user-facing legal answer must refresh the bounded set of relevant
    # official sources.  Set LEGAL_RAG_APP_ONLINE=0 only for an explicitly
    # offline/test deployment; stale documents still fail closed.
    online = None
    if os.getenv("LEGAL_RAG_APP_ONLINE", "1") == "1":
        online = OfficialAPIRetriever(store)

    return LegalRAG(settings=settings, store=store, online=online)


def create_legal_session(user_id: str) -> str:
    return get_legal_rag().create_session(user_id)


def ask_legal_question(
    user_id: str,
    session_id: str,
    question: str,
    *,
    new_topic: bool = False,
) -> dict:
    rag = get_legal_rag()
    try:
        result = rag.ask(
            user_id=user_id,
            session_id=session_id,
            question=question,
            new_topic=new_topic,
        )
    except ConflictError:
        latest = rag.store.latest_turn(user_id, session_id)
        if not latest or latest["question"] != question:
            raise
        # A browser double-submit must not repeat expensive source/model calls
        # or replace the completed verified answer with an error.
        result = latest["response"]
        result.setdefault("diagnostics", {})["duplicate_submission_reused"] = True
    result["question_type"] = "검증형_RAG_대화"
    result["original_question"] = question
    result["search_query"] = result.get("diagnostics", {}).get("query", question)
    result.setdefault("metadata", {}).update(
        {
            "rag_verified": bool(result.get("verification", {}).get("passed")),
            "model_role": "search_planning_and_evidence_selection_only",
            "legal_applicability": result.get("verification", {}).get(
                "legal_applicability", "not_verified"
            ),
        }
    )
    return result
