from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    database: str = "data/legal_rag.sqlite3"
    model: str = "qwen3:1.7b-q4_K_M"
    ollama_url: str = "http://127.0.0.1:11434"
    timeout_seconds: int = 180
    retrieval_k: int = 24
    evidence_k: int = 2
    max_context_chars: int = 6000
    history_turns: int = 6
    max_question_chars: int = 4000
    online_retrieval: bool = False
    embedding_model: str = ""

    @classmethod
    def from_env(cls):
        return cls(database=os.getenv("LEGAL_RAG_DB", cls.database),
                   model=os.getenv("LEGAL_RAG_MODEL", cls.model),
                   ollama_url=os.getenv("LEGAL_RAG_OLLAMA_URL", cls.ollama_url),
                   online_retrieval=os.getenv("LEGAL_RAG_ONLINE", "0") == "1",
                   embedding_model=os.getenv("LEGAL_RAG_EMBEDDING_MODEL", ""))
