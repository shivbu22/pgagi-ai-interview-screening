"""AI Interview Screening System — FastAPI backend.

Pipeline: resume upload -> parse (skills/projects/experience) -> TF-IDF
retrieval over a Mitchell-based knowledge base -> deterministic question
composition -> session stored in SQLite.

Runs fully locally with no external API keys.
"""
import pathlib

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import db
from .generator import ROLES, generate_questions
from .resume_parser import parse_resume
from .retriever import Retriever, load_kb

app = FastAPI(title="AI Interview Screening System", version="1.0.0")

KB = load_kb()
RETRIEVER = Retriever(KB)

FRONTEND_DIST = pathlib.Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"


@app.get("/api/health")
def health():
    return {"status": "ok", "kb_chunks": len(RETRIEVER.chunks),
            "kb_source": KB["meta"]["primary_source"]}


@app.get("/api/roles")
def roles():
    return {"roles": list(ROLES.keys())}


@app.post("/api/sessions")
async def create_session(role: str = Form(...),
                         candidate_name: str = Form(""),
                         resume: UploadFile = File(...)):
    if role not in ROLES:
        raise HTTPException(400, f"Unknown role. Choose one of: {list(ROLES)}")
    data = await resume.read()
    if not data:
        raise HTTPException(400, "Empty file uploaded.")
    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(400, "Resume file too large (max 5 MB).")
    try:
        profile = parse_resume(data, resume.filename or "resume.txt")
    except Exception as exc:  # unreadable PDF etc.
        raise HTTPException(400, f"Could not parse resume: {exc}")
    if profile["char_count"] < 50:
        raise HTTPException(400, "Resume text is too short to screen.")

    query_terms = (ROLES[role]["focus_terms"] + profile["skills"]
                   + ROLES[role]["focus_skills"])
    retrieved = RETRIEVER.retrieve(query_terms, top_k=8)
    questions = generate_questions(profile, role, retrieved, total=10)

    name = candidate_name.strip() or profile["name"]
    sid = db.save_session(name, role, profile, questions)
    session = db.get_session(sid)
    session["retrieved_topics"] = [
        {"topic": c["topic"], "title": c["title"], "score": c["score"]}
        for c in retrieved
    ]
    return session


@app.get("/api/sessions/{sid}")
def get_session(sid: str):
    session = db.get_session(sid)
    if not session:
        raise HTTPException(404, "Session not found.")
    return session


@app.get("/api/sessions")
def sessions():
    return {"sessions": db.list_sessions()}


# --- Static frontend (built Vite SPA) -------------------------------------
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"),
              name="assets")

    @app.get("/")
    def index():
        return FileResponse(FRONTEND_DIST / "index.html")
else:

    @app.get("/")
    def index_missing():
        return {"detail": "Frontend not built yet. Run: cd frontend && npm run build"}
