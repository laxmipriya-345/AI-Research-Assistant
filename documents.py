"""
Chat with Documents
--------------------
Handles ingesting uploaded files (pdf / docx / txt / md), chunking them,
and retrieving the most relevant chunks for a query using TF-IDF cosine
similarity (no external embedding API required, works fully offline).
"""
import os
import uuid

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from config import UPLOADS_DIR, DOC_CHUNK_SIZE, DOC_CHUNK_OVERLAP, DOC_TOP_K
from memory import get_db


def _extract_text(filepath: str) -> str:
    ext = os.path.splitext(filepath)[1].lower()
    if ext == ".pdf":
        from pypdf import PdfReader
        reader = PdfReader(filepath)
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    elif ext == ".docx":
        import docx
        d = docx.Document(filepath)
        return "\n".join(p.text for p in d.paragraphs)
    else:  # .txt, .md, and other plain-text formats
        with open(filepath, "r", errors="ignore") as f:
            return f.read()


def _chunk_text(text: str, size=DOC_CHUNK_SIZE, overlap=DOC_CHUNK_OVERLAP) -> list:
    chunks = []
    start = 0
    text = " ".join(text.split())  # normalize whitespace
    while start < len(text):
        end = start + size
        chunks.append(text[start:end])
        start = end - overlap
    return [c for c in chunks if c.strip()]


def ingest_document(session_id: str, uploaded_filename: str, tmp_path: str) -> dict:
    """Save the file, chunk it, and store chunks in SQLite for later retrieval."""
    ext = os.path.splitext(uploaded_filename)[1]
    stored_name = f"{uuid.uuid4().hex}{ext}"
    stored_path = os.path.join(UPLOADS_DIR, stored_name)
    os.replace(tmp_path, stored_path)

    text = _extract_text(stored_path)
    chunks = _chunk_text(text)

    with get_db() as db:
        for i, chunk in enumerate(chunks):
            db.execute(
                "INSERT INTO documents (session_id, filename, chunk_index, content) VALUES (?, ?, ?, ?)",
                (session_id, uploaded_filename, i, chunk),
            )

    return {"filename": uploaded_filename, "chunks": len(chunks)}


def list_documents(session_id: str) -> list:
    with get_db() as db:
        rows = db.execute(
            "SELECT DISTINCT filename FROM documents WHERE session_id = ?", (session_id,)
        ).fetchall()
        return [r["filename"] for r in rows]


def search_documents(session_id: str, query: str, top_k: int = DOC_TOP_K) -> list:
    """Return the top_k most relevant chunks (with source filename) for a query."""
    with get_db() as db:
        rows = db.execute(
            "SELECT filename, content FROM documents WHERE session_id = ?", (session_id,)
        ).fetchall()

    if not rows:
        return []

    corpus = [r["content"] for r in rows]
    vectorizer = TfidfVectorizer(stop_words="english")
    try:
        matrix = vectorizer.fit_transform(corpus + [query])
    except ValueError:
        return []  # empty vocabulary (e.g. all stopwords)

    similarities = cosine_similarity(matrix[-1], matrix[:-1]).flatten()
    ranked = sorted(zip(similarities, rows), key=lambda x: x[0], reverse=True)

    results = []
    for score, row in ranked[:top_k]:
        if score <= 0:
            continue
        results.append({"filename": row["filename"], "content": row["content"], "score": float(score)})
    return results
