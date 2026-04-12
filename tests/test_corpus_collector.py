# tests/test_corpus_collector.py
import hashlib
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from corpus_collector import canonical_paper_id, normalize_arxiv_id, save_papers


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


class TestSavePapersDedup:
    def test_s2_paper_deduplicated_across_calls(self, tmp_path):
        """The BS-1 regression test: same S2 paper (no arxiv_id) must not be saved twice."""
        paper = {
            "title": "Efficient IoT Edge Computing with Federated Learning",
            "abstract": "An abstract.",
            "arxiv_id": "",
            "authors": ["Alice"],
            "date": "2026-01-01",
            "source": "Semantic Scholar",
            "source_url": "https://semanticscholar.org/paper/abc",
            "citation_count": 5,
        }
        seen: set = set()
        s1 = save_papers([paper], "ai", seen, [], 0.0, raw_dir=tmp_path)
        s2 = save_papers([paper], "ai", seen, [], 0.0, raw_dir=tmp_path)
        assert s1["saved"] == 1, f"First run should save 1 paper, got {s1['saved']}"
        assert s2["saved"] == 0, f"Second run should save 0 (duplicate), got {s2['saved']}"
        assert s2["duplicates"] == 1, f"Should count 1 duplicate, got {s2['duplicates']}"

    def test_arxiv_paper_deduplicated_across_calls(self, tmp_path):
        """arXiv papers deduplicate correctly via canonical arxiv: key."""
        paper = {
            "title": "Attention Is All You Need",
            "abstract": "Abstract.",
            "arxiv_id": "1706.03762v5",
            "authors": ["Vaswani"],
            "date": "2017-06-12",
            "source": "arXiv",
            "source_url": "https://arxiv.org/abs/1706.03762",
            "citation_count": 90000,
        }
        seen: set = set()
        s1 = save_papers([paper], "ai", seen, [], 0.0, raw_dir=tmp_path)
        # Same paper, different version suffix — must still deduplicate
        paper_v2 = {**paper, "arxiv_id": "1706.03762v1"}
        s2 = save_papers([paper_v2], "ai", seen, [], 0.0, raw_dir=tmp_path)
        assert s1["saved"] == 1
        assert s2["duplicates"] == 1


class TestCanonicalPaperIdEdgeCases:
    def test_empty_title_raises(self):
        import pytest
        with pytest.raises(ValueError, match="non-empty"):
            canonical_paper_id("", "")

    def test_whitespace_only_title_raises(self):
        import pytest
        with pytest.raises(ValueError, match="non-empty"):
            canonical_paper_id("", "   ")

    def test_whitespace_arxiv_id_uses_s2_branch(self):
        """Whitespace-only arxiv_id must not take the arxiv branch."""
        result = canonical_paper_id("   ", "A Real Title")
        assert result.startswith("s2:")

    def test_unicode_title_is_stable(self):
        """Unicode titles produce consistent hashes."""
        r1 = canonical_paper_id("", "Étude sur les réseaux IoT")
        r2 = canonical_paper_id("", "Étude sur les réseaux IoT")
        assert r1 == r2
        assert r1.startswith("s2:")
