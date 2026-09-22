PLAN = {
    "type": "object", "additionalProperties": False,
    "required": ["query", "needs_clarification", "questions", "follow_up"],
    "properties": {"query": {"type": "string", "minLength": 1, "maxLength": 2000},
                   "needs_clarification": {"type": "boolean"}, "follow_up": {"type": "boolean"},
                   "questions": {"type": "array", "maxItems": 3, "items": {"type": "string", "maxLength": 300}}},
}
RANK = {
    "type": "object", "additionalProperties": False, "required": ["scores"],
    "properties": {"scores": {"type": "array", "maxItems": 24,
                              "items": {"type": "integer", "minimum": 0, "maximum": 3}}},
}
SELECTION = {
    "type": "object", "additionalProperties": False, "required": ["status", "evidence_indices"],
    "properties": {"status": {"enum": ["answer", "clarify", "abstain"]},
                   "evidence_indices": {"type": "array", "maxItems": 4, "uniqueItems": True,
                                        "items": {"type": "integer", "minimum": 0, "maximum": 3}}},
}
DRAFT = {
    "type": "object", "additionalProperties": False, "required": ["status", "claims", "questions"],
    "properties": {"status": {"enum": ["answer", "clarify", "abstain"]},
                   "claims": {"type": "array", "maxItems": 4, "items": {
                       "type": "object", "additionalProperties": False, "required": ["evidence_id", "text", "quote"],
                       "properties": {"evidence_id": {"type": "string"}, "text": {"type": "string", "minLength": 1}, "quote": {"type": "string", "minLength": 1}},
                   }}, "questions": {"type": "array", "maxItems": 3, "items": {"type": "string", "maxLength": 300}}},
}
