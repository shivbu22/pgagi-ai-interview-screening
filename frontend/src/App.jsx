import { useEffect, useState } from "react";

const LEVELS = ["Basic", "Intermediate", "Advanced"];

function QuestionCard({ q }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="question">
      <div className="meta">
        <span className="qnum">Q{q.id}</span>
        <span className={`level ${q.level}`}>{q.level}</span>
        <span className="source">{q.source_label}</span>
      </div>
      <p className="qtext">{q.question}</p>
      <button className="hint-toggle" onClick={() => setOpen(!open)}>
        {open ? "Hide model-answer hint" : "Show model-answer hint"}
      </button>
      {open && (
        <div className="hint-box">
          <span className="hint-label">What a strong answer covers</span>
          <p style={{ margin: "6px 0 0" }}>{q.hint}</p>
          {q.key_points && q.key_points.length > 0 && (
            <>
              <span className="hint-label" style={{ display: "block", marginTop: 10 }}>
                Key points from the knowledge base
              </span>
              <ul>
                {q.key_points.map((kp, i) => (
                  <li key={i}>{kp}</li>
                ))}
              </ul>
            </>
          )}
        </div>
      )}
    </div>
  );
}

export default function App() {
  const [roles, setRoles] = useState([]);
  const [role, setRole] = useState("AI/ML Engineer");
  const [name, setName] = useState("");
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [session, setSession] = useState(null);
  const [past, setPast] = useState([]);

  const loadPast = () =>
    fetch("/api/sessions")
      .then((r) => r.json())
      .then((d) => setPast(d.sessions || []))
      .catch(() => {});

  useEffect(() => {
    fetch("/api/roles")
      .then((r) => r.json())
      .then((d) => setRoles(d.roles || []))
      .catch(() => {});
    loadPast();
  }, []);

  async function submit(e) {
    e.preventDefault();
    if (!file) {
      setError("Please choose a resume file (PDF or text).");
      return;
    }
    setBusy(true);
    setError("");
    const fd = new FormData();
    fd.append("role", role);
    fd.append("candidate_name", name);
    fd.append("resume", file);
    try {
      const res = await fetch("/api/sessions", { method: "POST", body: fd });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Request failed");
      setSession(data);
      loadPast();
    } catch (err) {
      setError(String(err.message || err));
    } finally {
      setBusy(false);
    }
  }

  async function openSession(id) {
    const res = await fetch(`/api/sessions/${id}`);
    if (res.ok) setSession(await res.json());
  }

  const step = session ? 3 : 1;

  return (
    <>
      <header className="topbar">
        <div className="topbar-inner">
          <div className="brand">
            Screen<span>wise</span>
          </div>
          <div className="tagline">
            AI interview screening — questions generated from the candidate's
            resume and a machine-learning knowledge base. No external APIs.
          </div>
        </div>
      </header>

      <main>
        <ol className="steps">
          <li className={step === 1 ? "active" : ""}>1. Upload resume</li>
          <li className={step === 1 ? "active" : ""}>2. Pick target role</li>
          <li className={step === 3 ? "active" : ""}>3. Review generated questions</li>
        </ol>

        {!session && (
          <section className="panel">
            <h2>Start a screening session</h2>
            <p className="sub">
              Upload a candidate resume and choose the role they are being
              screened for. The system extracts skills and projects, retrieves
              the most relevant knowledge-base concepts, and composes a
              10-question interview set with model-answer hints.
            </p>
            {error && <div className="error">{error}</div>}
            <form onSubmit={submit}>
              <div className="field">
                <label htmlFor="resume">Resume (PDF or .txt, max 5 MB)</label>
                <input
                  id="resume"
                  type="file"
                  accept=".pdf,.txt"
                  onChange={(e) => setFile(e.target.files[0] || null)}
                />
                {file && <div className="hint-text">Selected: {file.name}</div>}
              </div>
              <div className="field">
                <label htmlFor="role">Target role</label>
                <select id="role" value={role} onChange={(e) => setRole(e.target.value)}>
                  {roles.map((r) => (
                    <option key={r} value={r}>
                      {r}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label htmlFor="cname">Candidate name (optional)</label>
                <input
                  id="cname"
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Detected from the resume if left blank"
                />
              </div>
              <button className="primary" type="submit" disabled={busy}>
                {busy ? "Analysing resume…" : "Generate interview questions"}
              </button>
            </form>

            {past.length > 0 && (
              <div className="sessions">
                <h3>Recent sessions</h3>
                <table>
                  <thead>
                    <tr>
                      <th>Candidate</th>
                      <th>Role</th>
                      <th>Created</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {past.map((s) => (
                      <tr key={s.id}>
                        <td>{s.candidate_name}</td>
                        <td>{s.role}</td>
                        <td>{new Date(s.created_at).toLocaleString()}</td>
                        <td>
                          <button className="linkish" onClick={() => openSession(s.id)}>
                            Open
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        )}

        {session && (
          <>
            <div className="q-head">
              <h2>Interview set — {session.role}</h2>
              <button className="ghost" onClick={() => setSession(null)}>
                New screening session
              </button>
            </div>
            <div className="results">
              <aside className="panel profile-panel">
                <h3>{session.candidate_name}</h3>
                <div className="role-line">{session.role}</div>
                {session.profile.email && (
                  <div style={{ fontSize: 14 }}>{session.profile.email}</div>
                )}
                <h4>Skills extracted from resume</h4>
                <div className="chips">
                  {session.profile.skills.map((s) => (
                    <span className="chip" key={s}>{s}</span>
                  ))}
                </div>
                <h4>Projects detected</h4>
                {session.profile.projects.length > 0 ? (
                  <ul className="proj-list">
                    {session.profile.projects.map((p) => (
                      <li key={p}>{p}</li>
                    ))}
                  </ul>
                ) : (
                  <p style={{ margin: 0, color: "var(--ink-soft)" }}>
                    No project titles detected.
                  </p>
                )}
                {session.retrieved_topics && (
                  <>
                    <h4>Knowledge base topics retrieved</h4>
                    <ul className="kb-list">
                      {session.retrieved_topics.map((t, i) => (
                        <li key={i}>
                          <span>
                            {t.topic} — {t.title}
                          </span>
                          <span className="kb-score">{t.score.toFixed(2)}</span>
                        </li>
                      ))}
                    </ul>
                  </>
                )}
              </aside>
              <section>
                {LEVELS.map((lvl) => {
                  const qs = session.questions.filter((q) => q.level === lvl);
                  if (!qs.length) return null;
                  return (
                    <div key={lvl}>
                      {qs.map((q) => (
                        <QuestionCard key={q.id} q={q} />
                      ))}
                    </div>
                  );
                })}
              </section>
            </div>
          </>
        )}
      </main>

      <footer>
        <div className="foot-inner">
          Screenwise — built for the PGAGI AI/ML Intern take-home assignment.
          Knowledge base: original concept notes based on Tom Mitchell,
          "Machine Learning" (1997). Question generation is fully local and
          deterministic — no LLM API keys required.
        </div>
      </footer>
    </>
  );
}
