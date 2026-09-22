"""SQLite corpus and tenant-isolated, optimistic/idempotent conversation state."""
import json
import math
import re
import sqlite3
import uuid
from collections import Counter
from contextlib import contextmanager
from pathlib import Path
from .types import Document, Hit, digest, utcnow


def tokens(text):
    terms = []
    for word in re.findall(r"[가-힣A-Za-z0-9]+", text.lower()):
        if len(word) > 1:
            terms.append(word)
        if re.search(r"[가-힣]", word):
            for n in (2, 3):
                terms.extend(word[i:i+n] for i in range(min(64, len(word) - n + 1)))
    return terms


class ConflictError(RuntimeError):
    pass


class Store:
    def __init__(self, path):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS documents(id TEXT PRIMARY KEY, body TEXT NOT NULL, length INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS postings(term TEXT NOT NULL, document_id TEXT NOT NULL, frequency INTEGER NOT NULL, PRIMARY KEY(term,document_id));
            CREATE INDEX IF NOT EXISTS posting_documents ON postings(document_id);
            CREATE TABLE IF NOT EXISTS vectors(document_id TEXT NOT NULL, model TEXT NOT NULL, vector TEXT NOT NULL, PRIMARY KEY(document_id,model));
            CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY, user_id TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS turns(session_id TEXT NOT NULL, revision INTEGER NOT NULL, request_id TEXT NOT NULL, question TEXT NOT NULL, response TEXT NOT NULL, created_at TEXT NOT NULL, PRIMARY KEY(session_id,revision), UNIQUE(session_id,request_id));
            CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(id UNINDEXED,title,body);
            """)
            counts = db.execute("SELECT (SELECT count(*) FROM documents),(SELECT count(*) FROM documents_fts)").fetchone()
            missing = db.execute("SELECT d.body FROM documents d WHERE NOT EXISTS (SELECT 1 FROM documents_fts f WHERE f.id=d.id)").fetchall() if counts[0] != counts[1] else []
            for row in missing:
                doc = Document(**json.loads(row[0]))
                db.execute("INSERT INTO documents_fts VALUES (?,?,?)", (doc.id, " ".join(tokens(doc.title)), " ".join(tokens(doc.text))))

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=20)
        db.row_factory = sqlite3.Row
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def upsert(self, document):
        if document.content_hash != digest(document.text):
            raise ValueError("source_hash_mismatch")
        counts = Counter(tokens(document.title + " " + document.text))
        with self.connection() as db:
            self._upsert_db(db, document, counts)

    def _upsert_db(self, db, document, counts=None):
        if document.content_hash != digest(document.text):
            raise ValueError("source_hash_mismatch")
        counts = counts or Counter(tokens(document.title + " " + document.text))
        old = db.execute("SELECT body FROM documents WHERE id=?", (document.id,)).fetchone()
        if old and json.loads(old[0])["content_hash"] != document.content_hash:
            raise ValueError("immutable_document_changed")
        if old:
            previous = json.loads(old[0])
            if previous == document.to_dict():
                return False
            if previous["title"] == document.title:
                db.execute("UPDATE documents SET body=? WHERE id=?", (json.dumps(document.to_dict(), ensure_ascii=False), document.id))
                return True
        db.execute("INSERT OR REPLACE INTO documents VALUES (?,?,?)", (document.id, json.dumps(document.to_dict(), ensure_ascii=False), sum(counts.values())))
        db.execute("DELETE FROM postings WHERE document_id=?", (document.id,))
        db.execute("DELETE FROM documents_fts WHERE id=?", (document.id,))
        db.execute("INSERT INTO documents_fts VALUES (?,?,?)", (document.id, " ".join(tokens(document.title)), " ".join(tokens(document.text))))
        return True

    def upsert_many(self, documents):
        unique = {}
        for document in documents:
            previous = unique.get(document.id)
            if previous and previous.to_dict() != document.to_dict():
                raise ValueError("conflicting_document_in_batch")
            unique[document.id] = document
        documents = list(unique.values())
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            existing = {row["id"]: json.loads(row["body"]) for row in db.execute("SELECT id,body FROM documents")}
            inserts, fts, updates = [], [], []
            for document in documents:
                if document.content_hash != digest(document.text):
                    raise ValueError("source_hash_mismatch")
                previous = existing.get(document.id)
                body = document.to_dict()
                encoded = json.dumps(body, ensure_ascii=False)
                if previous and previous["content_hash"] != document.content_hash:
                    raise ValueError("immutable_document_changed")
                if previous == body:
                    continue
                if previous and previous["title"] == document.title:
                    updates.append((encoded, document.id))
                    continue
                title_terms, text_terms = tokens(document.title), tokens(document.text)
                inserts.append((document.id, encoded, len(title_terms) + len(text_terms)))
                fts.append((document.id, " ".join(title_terms), " ".join(text_terms)))
            db.executemany("UPDATE documents SET body=? WHERE id=?", updates)
            db.executemany("INSERT OR REPLACE INTO documents VALUES (?,?,?)", inserts)
            db.executemany("DELETE FROM documents_fts WHERE id=?", ((row[0],) for row in inserts))
            db.executemany("INSERT INTO documents_fts VALUES (?,?,?)", fts)
            changed = len(updates) + len(inserts)
        return {"received": len(documents), "changed": changed}

    def get(self, document_id):
        with self.connection() as db:
            row = db.execute("SELECT body FROM documents WHERE id=?", (document_id,)).fetchone()
        return Document(**json.loads(row[0])) if row else None

    def documents(self):
        with self.connection() as db:
            rows = db.execute("SELECT body FROM documents ORDER BY id").fetchall()
        return [Document(**json.loads(row[0])) for row in rows]

    def delete_documents(self, document_ids):
        ids = list(dict.fromkeys(document_ids))
        if not ids:
            return 0
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("CREATE TEMP TABLE delete_ids(id TEXT PRIMARY KEY)")
            db.executemany("INSERT INTO delete_ids VALUES (?)", ((key,) for key in ids))
            removed = db.execute("DELETE FROM documents WHERE id IN (SELECT id FROM delete_ids)").rowcount
            db.execute("DELETE FROM postings WHERE document_id IN (SELECT id FROM delete_ids)")
            db.execute("DELETE FROM vectors WHERE document_id IN (SELECT id FROM delete_ids)")
            db.execute("DELETE FROM documents_fts WHERE id IN (SELECT id FROM delete_ids)")
        return removed

    def lexical(self, query, limit=24):
        terms = list(dict.fromkeys(tokens(query)))[:160]
        if not terms:
            return []
        match = " OR ".join('"' + term.replace('"', '""') + '"' for term in terms)
        with self.connection() as db:
            ranked = db.execute("SELECT id,bm25(documents_fts,0,3,1) AS score FROM documents_fts WHERE documents_fts MATCH ? ORDER BY score,id LIMIT ?", (match, limit)).fetchall()
            result = []
            for row in ranked:
                key = row["id"]
                body = db.execute("SELECT body FROM documents WHERE id=?", (key,)).fetchone()[0]
                result.append(Hit(Document(**json.loads(body)), -row["score"], ["fts5_bm25_korean_ngrams"]))
        return result

    def put_vector(self, document_id, model, vector):
        if not vector or not all(isinstance(x, (int, float)) and math.isfinite(x) for x in vector):
            raise ValueError("invalid_embedding")
        if not self.get(document_id):
            raise ValueError("unknown_document")
        with self.connection() as db:
            db.execute("INSERT OR REPLACE INTO vectors VALUES (?,?,?)", (document_id, model, json.dumps(vector)))

    def dense(self, query_vector, model, limit=24):
        norm = math.sqrt(sum(x*x for x in query_vector))
        if not norm or not math.isfinite(norm):
            raise ValueError("invalid_query_embedding")
        with self.connection() as db:
            rows = db.execute("SELECT document_id,vector FROM vectors WHERE model=?", (model,)).fetchall()
        scores = []
        for row in rows:
            vector = json.loads(row["vector"])
            if len(vector) != len(query_vector):
                raise ValueError("embedding_dimension_mismatch")
            dnorm = math.sqrt(sum(x*x for x in vector))
            if dnorm:
                scores.append((sum(a*b for a, b in zip(query_vector, vector)) / (norm * dnorm), row["document_id"]))
        return [Hit(self.get(key), score, ["dense"]) for score, key in sorted(scores, reverse=True)[:limit]]

    def create_session(self, user_id):
        if not isinstance(user_id, str) or not user_id.strip():
            raise ValueError("user_id_required")
        session = uuid.uuid4().hex
        with self.connection() as db:
            db.execute("INSERT INTO sessions VALUES (?,?,0,?)", (session, user_id, utcnow()))
        return session

    def snapshot(self, user_id, session_id, request_id, question, limit=6):
        with self.connection() as db:
            db.execute("BEGIN")
            session = db.execute("SELECT revision FROM sessions WHERE id=? AND user_id=?", (session_id, user_id)).fetchone()
            if not session:
                raise PermissionError("unknown_session")
            prior = db.execute("SELECT question,response FROM turns WHERE session_id=? AND request_id=?", (session_id, request_id)).fetchone()
            if prior and prior["question"] != question:
                raise ConflictError("request_id_reused_for_different_question")
            history = db.execute("SELECT question,response FROM turns WHERE session_id=? ORDER BY revision DESC LIMIT ?", (session_id, limit)).fetchall()
        scoped = []
        scoped_responses = []
        for row in history:
            scoped.append(row["question"])
            resp = json.loads(row["response"])
            scoped_responses.append(resp)
            if resp.get("diagnostics", {}).get("context_reset"):
                break
        # 반환: revision, history 질문 리스트, prior replay, 이전 turn 응답 리스트 (최신순)
        return (
            session["revision"],
            list(reversed(scoped)),
            json.loads(prior["response"]) if prior else None,
            scoped_responses,  # 최신 turn 이 [0]
        )

    def commit_turn(self, user_id, session_id, revision, request_id, question, response):
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            changed = db.execute("UPDATE sessions SET revision=revision+1 WHERE id=? AND user_id=? AND revision=?", (session_id, user_id, revision)).rowcount
            if changed != 1:
                raise ConflictError("session_changed_retry_with_fresh_context")
            db.execute("INSERT INTO turns VALUES (?,?,?,?,?,?)", (session_id, revision + 1, request_id, question, json.dumps(response, ensure_ascii=False), utcnow()))

    def latest_turn(self, user_id, session_id):
        with self.connection() as db:
            if not db.execute(
                "SELECT 1 FROM sessions WHERE id=? AND user_id=?",
                (session_id, user_id),
            ).fetchone():
                raise PermissionError("unknown_session")
            row = db.execute(
                "SELECT question,response FROM turns WHERE session_id=? ORDER BY revision DESC LIMIT 1",
                (session_id,),
            ).fetchone()
        if not row:
            return None
        return {"question": row["question"], "response": json.loads(row["response"])}

    def delete_session(self, user_id, session_id):
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            if not db.execute("SELECT 1 FROM sessions WHERE id=? AND user_id=?", (session_id, user_id)).fetchone():
                raise PermissionError("unknown_session")
            db.execute("DELETE FROM turns WHERE session_id=?", (session_id,))
            db.execute("DELETE FROM sessions WHERE id=?", (session_id,))
