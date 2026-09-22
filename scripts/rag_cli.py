"""Backend administration and terminal smoke client; no UI dependency."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from legal_rag.config import Settings
from legal_rag.engine import LegalRAG
from legal_rag.store import Store
from legal_rag.ingest import ingest_api_cache


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["ingest", "session", "ask", "stats", "embed"])
    parser.add_argument("--user", default="local-developer")
    parser.add_argument("--session")
    parser.add_argument("--question")
    parser.add_argument("--request-id")
    parser.add_argument("--new-topic", action="store_true")
    args = parser.parse_args()
    settings = Settings.from_env()
    store = Store(settings.database)
    if args.command == "ingest":
        print(json.dumps(ingest_api_cache(store), ensure_ascii=False))
    elif args.command == "stats":
        from collections import Counter
        from legal_rag.verify import document_errors
        documents = store.documents()
        print(json.dumps({"documents": len(documents), "kinds": dict(Counter(d.kind for d in documents)),
                          "fresh_valid": sum(not document_errors(d) for d in documents)}, ensure_ascii=False))
    elif args.command == "embed":
        if not settings.embedding_model:
            raise SystemExit("Set LEGAL_RAG_EMBEDDING_MODEL to an installed embedding model first.")
        from legal_rag.model import OllamaEmbedder
        embedder = OllamaEmbedder(settings.embedding_model, settings.ollama_url)
        for document in store.documents():
            vector = embedder.embed([document.title + "\n" + document.text])[0]
            store.put_vector(document.id, settings.embedding_model, vector)
        print("Embedding index complete")
    else:
        rag = LegalRAG(settings, store=store)
        if args.command == "session":
            print(rag.create_session(args.user))
        elif not args.session or not args.question:
            parser.error("ask requires --session and --question")
        else:
            result = rag.ask(args.user, args.session, args.question, args.request_id, args.new_topic)
            print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
