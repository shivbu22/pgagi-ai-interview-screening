"""TF-IDF retrieval over the knowledge base.

The retriever ranks KB chunks against a query built from the target role's
focus terms plus the candidate's extracted resume skills. Fully local and
deterministic (scikit-learn TF-IDF, fixed vocabulary order)."""
import json
import pathlib

from sklearn.feature_extraction.text import TfidfVectorizer

KB_PATH = pathlib.Path(__file__).resolve().parent.parent / "data" / "knowledge_base.json"


def load_kb() -> dict:
    return json.loads(KB_PATH.read_text(encoding="utf-8"))


class Retriever:
    def __init__(self, kb: dict):
        self.chunks = []
        for topic in kb["topics"]:
            for chunk in topic["chunks"]:
                self.chunks.append({**chunk, "topic": topic["title"],
                                    "topic_id": topic["id"]})
        docs = [
            " ".join([c["title"], c["summary"], " ".join(c["terms"]),
                      " ".join(c["key_points"])])
            for c in self.chunks
        ]
        self.vectorizer = TfidfVectorizer(stop_words="english",
                                          ngram_range=(1, 2))
        self.matrix = self.vectorizer.fit_transform(docs)

    def retrieve(self, query_terms: list, top_k: int = 8) -> list:
        """Return the top_k chunks for the query, each with a score."""
        if not query_terms:
            return []
        query = " ".join(query_terms)
        qv = self.vectorizer.transform([query])
        scores = (self.matrix @ qv.T).toarray().ravel()
        ranked = sorted(range(len(scores)), key=lambda i: -scores[i])
        return [
            {**self.chunks[i], "score": round(float(scores[i]), 4)}
            for i in ranked[:top_k] if scores[i] > 0
        ]
