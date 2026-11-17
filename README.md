# Screenwise — AI Interview Screening System

A take-home assignment build for the **PGAGI AI/ML Intern** application.

Screenwise generates a tailored technical interview for a candidate from two
grounded sources: **the candidate's own resume** (skills, projects, experience)
and a **retrieval-augmented knowledge base** of machine-learning concepts.
It runs **fully locally with no external API keys** — question generation is
deterministic, so the same resume + role always produces the same interview.

![Generated interview set](assets/shot-3-questions.png)

## What it does

1. **Upload** a resume (PDF or plain text) and pick a target role
   (AI/ML Engineer, Data Scientist, GenAI / LLM Engineer, Data Analyst,
   Computer Vision Engineer, ML Intern).
2. **Parse** — the backend extracts the candidate's name, email, skills
   (40+ term lexicon), project titles, and experience signals.
3. **Retrieve** — a TF-IDF retriever ranks knowledge-base chunks against a
   query built from the role's focus areas plus the candidate's skills.
4. **Generate** — a fixed, deterministic composition builds 10 questions:
   - 5 knowledge-base concept questions (with a difficulty rebalance so the
     set always includes an Advanced question), each carrying a
     model-answer hint and the KB key points a strong answer should cover;
   - 3 resume-grounded questions about the candidate's actual projects and
     skills ("In your project 'MARAT', what was the hardest technical
     problem…");
   - 2 role-focus questions — either depth probes on matched skills or
     honest gap questions for skills the role needs that the resume lacks.
5. **Store** — every session (profile + question set) is saved in SQLite and
   can be reopened from the "Recent sessions" list.

## Knowledge base

The KB's primary source is the topic structure of Tom Mitchell's
*Machine Learning* (McGraw-Hill, 1997). All 16 chunks across 13 topics —
concept learning and version spaces, decision trees (entropy, information
gain, pruning), neural networks (perceptrons, backpropagation), evaluating
hypotheses, Bayesian learning and Naive Bayes, PAC learning / VC dimension,
instance-based learning, genetic algorithms, rule learning, explanation-based
learning / KBANN, and reinforcement learning — are **original concept notes
written for this project**. No book text is reproduced. Each chunk carries a
summary, key points, key terms, and two hand-written interview questions with
model-answer hints, tagged by difficulty (Basic / Intermediate / Advanced).

## Architecture

```
┌──────────────┐   POST /api/sessions    ┌──────────────────────────────┐
│  React SPA   │ ──────────────────────▶ │  FastAPI backend             │
│  (Vite build,│                         │                              │
│   served by  │ ◀────────────────────── │  resume_parser.py  (pypdf)   │
│   FastAPI)   │   session JSON          │  retriever.py      (TF-IDF)  │
└──────────────┘                         │  generator.py      (rules)   │
                                         │  db.py             (SQLite)  │
                                         │  data/knowledge_base.json    │
                                         └──────────────────────────────┘
```

**Stack choice:** the brief allows React/Next.js + FastAPI/Flask. This build
uses a **Vite React SPA served directly by FastAPI** (single process, no
Node runtime needed in production) instead of Next.js — there is no SSR
requirement in an internal screening tool, and one-process deployment keeps
the demo trivially runnable. The backend is modular: parsing, retrieval,
generation, and storage are separate modules with no framework coupling
beyond `main.py`.

**Why no LLM?** The brief's hard constraint is that the system must work with
no external API keys. The generation engine is therefore template- and
retrieval-based: questions are either hand-written against KB chunks
(retrieved by TF-IDF relevance to this candidate + role) or composed from
the candidate's extracted skills/projects. This is fully deterministic and
auditable — an interviewer can see exactly why each question was asked
(every question carries its source label). If an `OPENAI_API_KEY` or
`ANTHROPIC_API_KEY` is present in the environment, a future polish layer
could rephrase questions, but the no-key path is complete on its own.

## Run it

```bash
# Backend + built frontend (single process)
cd backend
python3 -m venv ../.venv && ../.venv/bin/pip install -r requirements.txt
cd ../frontend && npm install && npm run build && cd ..
.venv/bin/uvicorn backend.app.main:app --port 8410
# open http://localhost:8410
```

Or use the helper: `./run.sh` (creates the venv, installs deps, builds the
frontend if needed, and starts the server on port 8410).

Frontend dev mode: `cd frontend && npm run dev` (Vite on :5173, proxies
`/api` to :8410).

## API

| Endpoint | Description |
|---|---|
| `GET /api/health` | Status + KB size |
| `GET /api/roles` | Supported target roles |
| `POST /api/sessions` | Multipart: `resume` file, `role`, optional `candidate_name`. Returns profile, retrieved topics, and the 10-question set |
| `GET /api/sessions` | Recent sessions |
| `GET /api/sessions/{id}` | One stored session |

## Testing

Verified end-to-end with a real resume PDF (upload → role select →
generation): the parser extracted 22 skills and all 4 project titles; the
generated set referenced the candidate's actual projects (MARAT, AI Voice
Receptionist) and retrieved KB topics (neural networks, reinforcement
learning, inductive bias, KBANN) with a Basic/Intermediate/Advanced spread.
Screenshots: `assets/shot-1-home.png` … `shot-4-hint.png`. A narrated
walkthrough is in `demo.mp4`; the full design write-up is in
`project-document.pdf`.

## Limitations

- Resume parsing is heuristic (section headers + layout cues); heavily
  designed multi-column resumes may parse imperfectly.
- The skill lexicon is curated (~45 terms); niche tools not in the lexicon
  are missed.
- TF-IDF retrieval is lexical; a local embedding model would improve
  semantic matching at the cost of a model download.
- Question quality is bounded by the hand-written KB question bank
  (32 questions) plus templates — deliberate, for determinism.

## Project layout

```
backend/
  app/            main.py, resume_parser.py, retriever.py, generator.py, db.py
  data/           knowledge_base.json
  requirements.txt
frontend/
  src/            App.jsx, main.jsx, styles.css
assets/           UI screenshots
docs/             project document source (HTML)
project-document.pdf
demo.mp4
run.sh
```
