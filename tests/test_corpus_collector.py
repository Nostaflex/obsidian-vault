# tests/test_corpus_collector.py
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from corpus_collector import canonical_paper_id, normalize_arxiv_id


class TestCanonicalPaperId:
    def test_arxiv_paper_returns_prefixed_normalized_id(self):
        result = canonical_paper_id("2401.12345v2", "Some Title")
        assert result == "arxiv:2401.12345"

    def test_arxiv_paper_no_version_returns_prefixed_id(self):
        result = canonical_paper_id("2401.12345", "Some Title")
        assert result == "arxiv:2401.12345"

    def test_semantic_scholar_no_arxiv_returns_s2_hash(self):
        title = "Efficient IoT Edge Computing with Federated Learning"
        expected_hash = hashlib.md5(title.lower().strip().encode()).hexdigest()[:16]
        result = canonical_paper_id("", title)
        assert result == f"s2:{expected_hash}"

    def test_s2_hash_is_deterministic(self):
        title = "The Same Title"
        result1 = canonical_paper_id("", title)
        result2 = canonical_paper_id("", title)
        assert result1 == result2

    def test_s2_hash_case_insensitive(self):
        result_lower = canonical_paper_id("", "federated learning")
        result_upper = canonical_paper_id("", "Federated Learning")
        assert result_lower == result_upper

    def test_arxiv_takes_priority_over_title(self):
        result = canonical_paper_id("2401.99999", "Federated Learning")
        assert result.startswith("arxiv:")
        assert "s2:" not in result
