import json
from dataclasses import dataclass
from typing import Optional

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from api.database import get_conn
from api.services.knowledge.approved_sources import resolve_organization

MIN_SCORE = 0.05
DEFAULT_TOP_N = 5


@dataclass
class KnowledgeChunk:
    chunk_id: int
    item_id: int
    slug: str
    title: str
    category: str
    source: str
    source_urls: list
    organization_id: Optional[str]
    organization_name: Optional[str]
    organization_url: Optional[str]
    applicable_age_range: str
    tags: list
    review_status: str
    heading: Optional[str]
    content: str
    score: float


def retrieve(query: str, top_n: int = DEFAULT_TOP_N) -> list:
    """
    Retrieve the top-N most relevant approved knowledge chunks for the query.
    Returns empty list if no chunk scores above MIN_SCORE.
    """
    conn = get_conn()
    try:
        rows = conn.execute(
            """SELECT kc.id as chunk_id, kc.item_id, kc.heading, kc.content,
                      ki.slug, ki.title, ki.category, ki.source, ki.source_urls,
                      ki.organization, ki.applicable_age_range, ki.tags, ki.review_status
               FROM knowledge_chunks kc
               JOIN knowledge_items ki ON kc.item_id = ki.id
               WHERE ki.review_status = 'approved'
               ORDER BY kc.item_id, kc.chunk_index"""
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        return []

    approved_rows = []
    for row in rows:
        source_urls = json.loads(row["source_urls"] or "[]")
        org = resolve_organization(
            row["source"],
            source_urls,
            row["organization"],
        )
        if org:
            approved_rows.append((row, org, source_urls))

    if not approved_rows:
        return []

    texts = [row["content"] for row, _, _ in approved_rows]
    corpus = texts + [query]

    vectorizer = TfidfVectorizer(
        stop_words="english",
        ngram_range=(1, 2),
        min_df=1,
        sublinear_tf=True,
    )
    tfidf_matrix = vectorizer.fit_transform(corpus)

    chunk_vectors = tfidf_matrix[:-1]
    query_vector = tfidf_matrix[-1]

    scores = cosine_similarity(query_vector, chunk_vectors).flatten()
    top_indices = np.argsort(scores)[::-1][:top_n]

    results = []
    for idx in top_indices:
        score = float(scores[idx])
        if score < MIN_SCORE:
            break
        row, org, source_urls = approved_rows[idx]
        results.append(KnowledgeChunk(
            chunk_id=row["chunk_id"],
            item_id=row["item_id"],
            slug=row["slug"],
            title=row["title"],
            category=row["category"],
            source=row["source"],
            source_urls=source_urls,
            organization_id=org.id,
            organization_name=org.name,
            organization_url=org.url,
            applicable_age_range=row["applicable_age_range"],
            tags=json.loads(row["tags"] or "[]"),
            review_status=row["review_status"],
            heading=row["heading"],
            content=row["content"],
            score=score,
        ))

    return results
