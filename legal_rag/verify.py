"""Deterministic publication gate. It verifies quotations, not legal entailment."""
from datetime import datetime, timezone
from urllib.parse import urlparse, parse_qs
import jsonschema
from .schemas import DRAFT
from .types import digest

DRAFT_VALIDATOR = jsonschema.Draft202012Validator(DRAFT)


def document_errors(document, now=None):
    now = now or datetime.now(timezone.utc)
    errors = []
    if document.kind not in {"statute", "precedent", "administrative_rule", "local_ordinance"}:
        errors.append("non_primary_source")
    if digest(document.text) != document.content_hash:
        errors.append("source_hash_mismatch")
    if document.metadata.get("origin") != "moleg_api":
        errors.append("untrusted_ingestion")
    try:
        url = urlparse(document.url)
        port = url.port
    except ValueError:
        return errors + ["untrusted_source_url"]
    query = parse_qs(url.query)
    if url.scheme != "https" or url.hostname not in {"law.go.kr", "www.law.go.kr"} or url.username or url.password or port not in {None, 443}:
        errors.append("untrusted_source_url")
    if document.kind == "statute" and (url.path != "/LSW/lsInfoP.do" or query.get("lsiSeq") != [document.version]):
        errors.append("source_version_url_mismatch")
    if document.kind == "precedent" and (url.path != "/LSW/precInfoP.do" or query.get("precSeq") != [document.source_id]):
        errors.append("source_case_url_mismatch")
    if document.kind == "administrative_rule" and (url.path != "/LSW/admRulInfoP.do" or query.get("admRulSeq") != [document.version]):
        errors.append("source_administrative_rule_url_mismatch")
    if document.kind == "local_ordinance" and (url.path != "/LSW/ordinInfoP.do" or query.get("ordinSeq") != [document.version]):
        errors.append("source_local_ordinance_url_mismatch")
    try:
        retrieved = datetime.fromisoformat(document.retrieved_at)
        expires = datetime.fromisoformat(document.fresh_until)
        if retrieved.tzinfo is None or expires.tzinfo is None or expires <= retrieved:
            raise ValueError("invalid timestamps")
        if expires <= now:
            errors.append("stale_source")
        if (retrieved - now).total_seconds() > 300:
            errors.append("future_retrieval_timestamp")
        if document.kind in {"statute", "administrative_rule", "local_ordinance"}:
            start = datetime.strptime(document.valid_from, "%Y%m%d").date()
            if start > now.date():
                errors.append("not_yet_effective")
            if document.valid_to and datetime.strptime(document.valid_to, "%Y%m%d").date() <= now.date():
                errors.append("expired_version")
            allowed_units = {"complete_article"} if document.kind != "administrative_rule" else {"complete_article", "complete_document"}
            if document.metadata.get("unit") not in allowed_units:
                errors.append("incomplete_statutory_unit")
            if document.kind == "administrative_rule" and not all(document.metadata.get(k) for k in ("rule_type", "issuing_authority")):
                errors.append("missing_administrative_rule_identity")
            if document.kind == "local_ordinance" and not all(document.metadata.get(k) for k in ("rule_type", "local_government")):
                errors.append("missing_local_ordinance_identity")
        elif document.kind == "precedent":
            if not all(document.metadata.get(k) for k in ("case_number", "court", "decision_date")):
                errors.append("missing_case_identity")
            else:
                date = str(document.metadata["decision_date"]).replace("-", "").replace(".", "")
                if datetime.strptime(date, "%Y%m%d").date() > now.date():
                    errors.append("future_case_decision")
    except (ValueError, TypeError):
        errors.append("invalid_source_dates")
    return errors


def verify_draft(draft, documents, now=None):
    try:
        DRAFT_VALIDATOR.validate(draft)
    except (jsonschema.ValidationError, TypeError):
        return {"passed": False, "errors": ["invalid_draft_schema"], "claims": [], "mode": "exact_source_units"}
    evidence = {d.id: d for d in documents}
    errors, validated, used = [], [], set()
    if draft["status"] != "answer":
        if draft["claims"]:
            errors.append("claims_in_non_answer")
        return {"passed": not errors, "errors": errors, "claims": [], "mode": "exact_source_units"}
    if not draft["claims"]:
        errors.append("empty_answer")
    for claim in draft["claims"]:
        key = claim["evidence_id"]
        if key not in evidence:
            errors.append("unknown_citation")
            continue
        if key in used:
            errors.append("duplicate_citation")
        used.add(key)
        document = evidence[key]
        errors.extend(document_errors(document, now))
        if claim["quote"] != document.text:
            errors.append("quote_not_complete_source_unit")
        if claim["text"] != claim["quote"]:
            errors.append("unsupported_generated_paraphrase")
        validated.append({"evidence_id": key, "text": document.text, "url": document.url,
                          "title": document.title, "content_hash": document.content_hash,
                          "kind": document.kind, "valid_from": document.valid_from,
                          "retrieved_at": document.retrieved_at, "version": document.version})
    return {"passed": not errors, "errors": sorted(set(errors)), "claims": validated if not errors else [],
            "mode": "exact_source_units", "legal_applicability": "not_verified"}
