import os
import shutil
import tempfile

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

import memory
import documents
import notes as notes_store
import agent
from models import (
    SessionCreate, SessionOut, ChatRequest, ChatResponse, ChatStep,
    NoteCreate, NoteOut, MessageOut,
)

app = FastAPI(title="AI Research Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

memory.init_db()

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")


# ---------- Sessions ----------

@app.post("/api/sessions", response_model=SessionOut)
def create_session(payload: SessionCreate):
    return memory.create_session(payload.title or "New Research Session")


@app.get("/api/sessions")
def list_sessions():
    return memory.list_sessions()


@app.get("/api/sessions/{session_id}")
def get_session(session_id: str):
    session = memory.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    return session


# ---------- Conversation memory ----------

@app.get("/api/sessions/{session_id}/history", response_model=list[MessageOut])
def get_history(session_id: str):
    if not memory.get_session(session_id):
        raise HTTPException(404, "Session not found")
    return memory.get_messages(session_id)


# ---------- Chat with Documents (upload) ----------

@app.post("/api/sessions/{session_id}/documents")
async def upload_document(session_id: str, file: UploadFile = File(...)):
    if not memory.get_session(session_id):
        raise HTTPException(404, "Session not found")

    suffix = os.path.splitext(file.filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    result = documents.ingest_document(session_id, file.filename, tmp_path)
    return result


@app.get("/api/sessions/{session_id}/documents")
def list_documents(session_id: str):
    return documents.list_documents(session_id)


# ---------- Multi-step reasoning chat (web search + documents + memory) ----------

@app.post("/api/sessions/{session_id}/chat", response_model=ChatResponse)
def chat(session_id: str, payload: ChatRequest):
    if not memory.get_session(session_id):
        raise HTTPException(404, "Session not found")

    answer, steps = agent.chat(
        session_id,
        payload.message,
        use_web_search=payload.use_web_search,
        use_documents=payload.use_documents,
    )
    return ChatResponse(answer=answer, steps=[ChatStep(**s) for s in steps])


# ---------- Research Notes ----------

@app.get("/api/sessions/{session_id}/notes", response_model=list[NoteOut])
def get_notes(session_id: str):
    return notes_store.list_notes(session_id)


@app.post("/api/sessions/{session_id}/notes", response_model=NoteOut)
def create_note(session_id: str, payload: NoteCreate):
    return notes_store.add_note(session_id, payload.title, payload.content)


@app.delete("/api/sessions/{session_id}/notes/{note_id}")
def remove_note(session_id: str, note_id: int):
    ok = notes_store.delete_note(session_id, note_id)
    if not ok:
        raise HTTPException(404, "Note not found")
    return {"deleted": True}


# ---------- Frontend static files ----------

app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/")
def root():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
