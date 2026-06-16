"""Tests for embedding utilities."""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.services.knowledge.embedding_utils import cosine_similarity, pack_embedding, unpack_embedding


def test_cosine_similarity_identical_vectors():
    vec = [1.0, 0.0, 0.0]
    assert math.isclose(cosine_similarity(vec, vec), 1.0)


def test_cosine_similarity_orthogonal_vectors():
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == 0.0


def test_pack_unpack_roundtrip():
    vec = [0.1, 0.2, 0.3]
    assert unpack_embedding(pack_embedding(vec)) == vec
