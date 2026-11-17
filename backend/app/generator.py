"""Deterministic question generation.

Questions come from three grounded sources, in a fixed composition:
1. Knowledge-base questions attached to retrieved KB chunks (concept depth),
2. Resume-grounded questions built from the candidate's own extracted
   skills and projects,
3. Role-focus questions for skills the role needs that the resume shows.

No external API is used anywhere. If OPENAI_API_KEY / ANTHROPIC_API_KEY is
present in the environment, an optional polish hook exists but the local
path is complete without it (see generator docstring in README)."""

ROLES = {
    "AI/ML Engineer": {
        "focus_terms": ["machine learning", "neural networks", "overfitting",
                        "decision trees", "evaluation", "generalisation",
                        "bayesian", "gradient descent", "model selection"],
        "focus_skills": ["Python", "Machine Learning", "Scikit-learn",
                         "PyTorch", "TensorFlow", "SQL"],
    },
    "Data Scientist": {
        "focus_terms": ["bayesian", "statistics", "evaluation",
                        "hypothesis testing", "naive bayes", "cross-validation",
                        "sample error", "confidence"],
        "focus_skills": ["Python", "SQL", "Statistics", "Pandas",
                         "Data Analysis", "A/B Testing"],
    },
    "GenAI / LLM Engineer": {
        "focus_terms": ["neural networks", "backpropagation", "embeddings",
                        "generalisation", "overfitting", "evaluation",
                        "reinforcement learning"],
        "focus_skills": ["LLM", "RAG", "LangChain", "LangGraph",
                         "Prompt Engineering", "Transformers", "Python"],
    },
    "Data Analyst": {
        "focus_terms": ["statistics", "evaluation", "bayesian",
                        "data analysis", "sample error"],
        "focus_skills": ["SQL", "Python", "Excel", "Tableau",
                         "Data Analysis", "Statistics"],
    },
    "Computer Vision Engineer": {
        "focus_terms": ["neural networks", "convolution", "overfitting",
                        "instance-based", "evaluation", "image"],
        "focus_skills": ["Computer Vision", "OpenCV", "PyTorch",
                         "Deep Learning", "Python"],
    },
    "ML Intern": {
        "focus_terms": ["machine learning", "decision trees", "concept learning",
                        "overfitting", "evaluation", "k-nearest neighbour"],
        "focus_skills": ["Python", "Machine Learning", "Scikit-learn",
                         "Pandas", "SQL"],
    },
}

LEVEL_ORDER = {"Basic": 0, "Intermediate": 1, "Advanced": 2}

RESUME_SKILL_TEMPLATES = [
    ("Your resume lists {skill}. Describe a concrete situation where you used "
     "{skill} and one limitation or failure mode you ran into.",
     "A strong answer names a specific project, the exact way {skill} was used, "
     "and a real limitation (data, performance, or correctness) plus how it was handled."),
    ("How would you explain {skill} to a junior engineer in two minutes, and "
     "what is the most common beginner mistake with it?",
     "Look for an accurate mental model of {skill}, not a definition recital; "
     "the beginner-mistake part reveals depth of hands-on experience."),
]

RESUME_PROJECT_TEMPLATES = [
    ("In your project '{project}', what was the hardest technical problem, and "
     "how did you decide your approach worked?",
     "A strong answer describes the problem concretely, the evaluation used "
     "(metric, baseline, or test), and what evidence showed the approach worked."),
    ("Walk me through the architecture of '{project}': what are the main "
     "components, and what would you redesign first if you rebuilt it today?",
     "Look for a clear component breakdown and honest reflection on trade-offs "
     "made under time or resource constraints."),
]

ROLE_GAP_TEMPLATE = (
    "This role works heavily with {skill}, which does not appear on your "
    "resume. How would you get productive with it in your first two weeks?",
    "A strong answer shows a learning plan grounded in adjacent experience "
    "and a small first deliverable, rather than claiming knowledge they do not have.")


def generate_questions(profile: dict, role: str, retrieved: list,
                       total: int = 10) -> list:
    """Compose the question set deterministically.

    Composition for total=10: 5 KB-concept questions (spread across
    difficulty), 3 resume-grounded, 2 role-focus (gap or depth)."""
    questions = []

    # --- 1. KB-concept questions from retrieved chunks -------------------
    kb_pool = []
    for chunk in retrieved:
        for q in chunk["questions"]:
            kb_pool.append({
                "question": q["q"],
                "level": q["level"],
                "hint": q["hint"],
                "source_type": "knowledge_base",
                "source_label": f"Knowledge base: {chunk['topic']} — {chunk['title']}",
                "key_points": chunk["key_points"],
                "score": chunk["score"],
            })
    # Prefer one question per chunk, harder levels later; deterministic order.
    kb_pool.sort(key=lambda x: (-x["score"], LEVEL_ORDER[x["level"]]))
    seen_chunks = set()
    kb_picked = []
    for q in kb_pool:
        if q["source_label"] in seen_chunks:
            continue
        seen_chunks.add(q["source_label"])
        kb_picked.append(q)
        if len(kb_picked) >= 5:
            break
    if len(kb_picked) < 5:  # allow a second question from top chunks
        for q in kb_pool:
            if q not in kb_picked:
                kb_picked.append(q)
            if len(kb_picked) >= 5:
                break
    kb_picked = kb_picked[:5]
    # Difficulty rebalance: guarantee at least one Advanced KB question.
    if kb_picked and not any(q["level"] == "Advanced" for q in kb_picked):
        advanced = [q for q in kb_pool if q["level"] == "Advanced"
                    and q not in kb_picked]
        if advanced:
            kb_picked[-1] = advanced[0]
    questions.extend(kb_picked)

    # --- 2. Resume-grounded questions ------------------------------------
    resume_qs = []
    skills = profile.get("skills", [])
    projects = profile.get("projects", [])
    for i, project in enumerate(projects[:2]):
        tmpl, hint = RESUME_PROJECT_TEMPLATES[i % len(RESUME_PROJECT_TEMPLATES)]
        resume_qs.append({
            "question": tmpl.format(project=project),
            "level": "Intermediate",
            "hint": hint,
            "source_type": "resume",
            "source_label": f"Resume: project '{project}'",
            "key_points": [],
            "score": None,
        })
    for i, skill in enumerate(skills[:2]):
        tmpl, hint = RESUME_SKILL_TEMPLATES[i % len(RESUME_SKILL_TEMPLATES)]
        resume_qs.append({
            "question": tmpl.format(skill=skill),
            "level": "Basic" if i == 0 else "Intermediate",
            "hint": hint.format(skill=skill),
            "source_type": "resume",
            "source_label": f"Resume: skill '{skill}'",
            "key_points": [],
            "score": None,
        })
    questions.extend(resume_qs[:3])

    # --- 3. Role-focus questions ------------------------------------------
    role_info = ROLES.get(role, {})
    gaps = [s for s in role_info.get("focus_skills", [])
            if s.lower() not in [x.lower() for x in skills]]
    role_qs = []
    for skill in gaps[:2]:
        role_qs.append({
            "question": ROLE_GAP_TEMPLATE.format(skill=skill),
            "level": "Basic",
            "hint": ROLE_GAP_TEMPLATE[1] if isinstance(ROLE_GAP_TEMPLATE, tuple) else
                    "A strong answer shows a learning plan grounded in adjacent "
                    "experience and a small first deliverable.",
            "source_type": "role",
            "source_label": f"Role focus: {role} — {skill}",
            "key_points": [],
            "score": None,
        })
    # If no gaps, deepen on a matched focus skill instead (skipping any
    # skill already used by a resume-grounded question above).
    if not role_qs:
        used = {q["source_label"].split("'")[1].lower()
                for q in resume_qs if "'" in q["source_label"]}
        matched = [s for s in role_info.get("focus_skills", [])
                   if s.lower() in [x.lower() for x in skills]
                   and s.lower() not in used]
        for skill in matched[:2]:
            tmpl, hint = RESUME_SKILL_TEMPLATES[0]
            role_qs.append({
                "question": tmpl.format(skill=skill),
                "level": "Advanced",
                "hint": hint.format(skill=skill),
                "source_type": "role",
                "source_label": f"Role focus: {role} — {skill} (depth)",
                "key_points": [],
                "score": None,
            })
    questions.extend(role_qs[:2])

    questions = questions[:total]
    for i, q in enumerate(questions, start=1):
        q["id"] = i
    return questions
