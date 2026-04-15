# tests/test_practitioner_collector.py
import sys
import json
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock
import urllib.error

sys.path.insert(0, str(Path(__file__).parent.parent))

import practitioner_collector as pc


class TestScoreArticle:
    def _now(self):
        return datetime.now(timezone.utc)

    def test_keyword_match_in_title_raises_score(self):
        published = self._now() - timedelta(hours=1)
        score = pc.score_article(
            title="Deploying to Cloud Run with Terraform",
            summary="A guide to GCP Cloud Run.",
            domain="gcp",
            published_date=published,
        )
        assert score >= 0.5, f"Expected score >= 0.5 for GCP title match, got {score}"

    def test_no_keyword_match_gives_low_score(self):
        published = self._now() - timedelta(days=30)
        score = pc.score_article(
            title="Recipe: The Perfect Sourdough Bread",
            summary="How to bake a perfect sourdough loaf at home.",
            domain="gcp",
            published_date=published,
        )
        assert score <= 0.3, f"Expected score <= 0.3 for off-domain content, got {score}"

    def test_old_article_gets_recency_penalty(self):
        recent = self._now() - timedelta(hours=1)
        old = self._now() - timedelta(days=30)
        score_recent = pc.score_article("Cloud Run Guide", "GCP Cloud Run tutorial", "gcp", recent)
        score_old = pc.score_article("Cloud Run Guide", "GCP Cloud Run tutorial", "gcp", old)
        assert score_recent > score_old, "Recent article should score higher than old one"

    def test_score_capped_at_1(self):
        published = self._now()
        score = pc.score_article(
            title="gcp cloud run gke bigquery vertex ai cloud sql",
            summary="gcp google cloud cloud run gke bigquery vertex ai pubsub spanner cloud sql cloud functions",
            domain="gcp",
            published_date=published,
        )
        assert score <= 1.0


class TestParseRss:
    FIXTURE_PATH = Path(__file__).parent / "fixtures" / "sample_rss.xml"

    def test_parse_valid_rss_returns_articles(self):
        xml_content = self.FIXTURE_PATH.read_bytes()
        articles = pc.parse_rss_content(xml_content)
        assert len(articles) == 2
        assert articles[0]["title"] == "Deploying to Cloud Run with Terraform"
        assert articles[0]["url"] == "https://example.com/cloud-run-terraform"
        assert "cloud run" in articles[0]["summary"].lower()
        assert isinstance(articles[0]["published_date"], datetime)

    def test_parse_malformed_xml_returns_empty(self):
        malformed = b"<rss><channel><item><title>Broken</title>"  # not closed
        articles = pc.parse_rss_content(malformed)
        assert articles == []

    def test_parse_empty_feed_returns_empty(self):
        empty = b'<?xml version="1.0"?><rss version="2.0"><channel></channel></rss>'
        articles = pc.parse_rss_content(empty)
        assert articles == []

    def test_parse_valid_atom_returns_articles(self):
        atom_fixture = Path(__file__).parent / "fixtures" / "sample_atom.xml"
        xml_content = atom_fixture.read_bytes()
        articles = pc.parse_rss_content(xml_content)
        assert len(articles) == 1
        assert articles[0]["title"] == "Kubernetes Operators Best Practices"
        assert articles[0]["url"] == "https://example.com/k8s-operators"
        assert isinstance(articles[0]["published_date"], datetime)
        # Verify date was actually parsed (not utcnow fallback)
        # The Atom date is 2026-04-14 so it should be in the past
        assert articles[0]["published_date"] < datetime.utcnow()


class TestFetchHn:
    def _make_hn_response(self, hits: list) -> bytes:
        return json.dumps({"hits": hits}).encode()

    def test_fetch_hn_returns_articles_above_min_points(self):
        hits = [
            {"title": "How we scaled Firestore at Firebase", "url": "https://firebase.blog/scale",
             "objectID": "111", "points": 120,
             "created_at_i": int((datetime.now(timezone.utc) - timedelta(hours=2)).timestamp()),
             "story_text": ""},
            {"title": "Low quality post", "url": "https://example.com/low",
             "objectID": "222", "points": 10,
             "created_at_i": int((datetime.now(timezone.utc) - timedelta(hours=2)).timestamp()),
             "story_text": ""},
        ]
        response_bytes = self._make_hn_response(hits)

        with patch("urllib.request.urlopen") as mock_open:
            mock_resp = MagicMock()
            mock_resp.read.return_value = response_bytes
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_open.return_value = mock_resp

            articles = pc.fetch_hn("firebase", since_days=7)

        assert len(articles) == 1
        assert articles[0]["title"] == "How we scaled Firestore at Firebase"

    def test_fetch_hn_network_error_returns_empty(self):
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("timeout")):
            articles = pc.fetch_hn("firebase", since_days=7)
        assert articles == []

    def test_fetch_hn_deduplicates_same_url(self):
        """Same URL returned by two keywords should appear only once."""
        hits = [
            {"title": "Firestore scaling tips", "url": "https://firebase.blog/firestore",
             "objectID": "333", "points": 80,
             "created_at_i": int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp()),
             "story_text": ""},
        ]
        response_bytes = self._make_hn_response(hits)

        call_count = 0
        def mock_urlopen(req, timeout=None):
            nonlocal call_count
            call_count += 1
            mock_resp = MagicMock()
            mock_resp.read.return_value = response_bytes
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            return mock_resp

        with patch("urllib.request.urlopen", side_effect=mock_urlopen):
            articles = pc.fetch_hn("firebase", since_days=7)

        # firebase has 3 keywords — same URL across all calls should yield 1 article
        assert len(articles) == 1

    def test_fetch_hn_fallback_url_when_no_external_url(self):
        """Hit with no external url but valid objectID should use HN item URL."""
        hits = [
            {"title": "Firebase tips", "url": None,
             "objectID": "999", "points": 75,
             "created_at_i": int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp()),
             "story_text": "Some text"},
        ]
        response_bytes = json.dumps({"hits": hits}).encode()

        with patch("urllib.request.urlopen") as mock_open:
            mock_resp = MagicMock()
            mock_resp.read.return_value = response_bytes
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_open.return_value = mock_resp

            articles = pc.fetch_hn("firebase", since_days=7)

        assert len(articles) == 1
        assert articles[0]["url"] == "https://news.ycombinator.com/item?id=999"

    def test_fetch_hn_missing_created_at_defaults_to_now(self):
        """Hit with missing created_at_i should get utcnow() as published_date, not epoch."""
        hits = [
            {"title": "Firebase scaling", "url": "https://firebase.blog/test",
             "objectID": "888", "points": 60,
             "story_text": ""},
            # Note: no created_at_i field
        ]
        response_bytes = json.dumps({"hits": hits}).encode()

        with patch("urllib.request.urlopen") as mock_open:
            mock_resp = MagicMock()
            mock_resp.read.return_value = response_bytes
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_open.return_value = mock_resp

            articles = pc.fetch_hn("firebase", since_days=7)

        assert len(articles) == 1
        # Should NOT be epoch (1970)
        epoch = datetime(1970, 1, 2)  # small buffer for timezone differences
        assert articles[0]["published_date"] > epoch


class TestFormatAsMarkdown:
    def _make_article(self, **kwargs):
        defaults = {
            "title": "Cloud Run: Zero to Production",
            "url": "https://cloud.google.com/blog/cloud-run",
            "summary": "A deep dive into Cloud Run deployment patterns.",
            "published_date": datetime(2026, 4, 14, 10, 0, 0),
            "relevance_score": 0.72,
            "tier": "A",
            "keywords": ["cloud run", "serverless"],
            "paper_id": "prac-a3f2c1b8",
        }
        defaults.update(kwargs)
        return defaults

    def test_frontmatter_contains_required_fields(self):
        article = self._make_article()
        md = pc.format_as_markdown(article, domain="gcp")
        assert "type: paper" in md
        assert "domain: gcp" in md
        assert 'paper_id: "prac-' in md
        assert "source: practitioner" in md
        assert 'source_url: "https://cloud.google.com/blog/cloud-run"' in md
        assert "relevance_score: 0.72" in md
        assert "tier: A" in md
        assert 'date: "2026-04-14"' in md
        assert "cloud run" in md  # keyword present
        assert "collected:" in md
        assert "Cloud Run: Zero to Production" in md

    def test_prac_paper_id_is_stable_and_prefixed(self):
        url = "https://cloud.google.com/blog/cloud-run"
        id1 = pc.prac_paper_id(url)
        id2 = pc.prac_paper_id(url)
        assert id1 == id2
        assert id1.startswith("prac-")
        assert len(id1) == len("prac-") + 8  # prac- + 8 hex chars

    def test_prac_paper_id_different_urls_differ(self):
        id1 = pc.prac_paper_id("https://example.com/a")
        id2 = pc.prac_paper_id("https://example.com/b")
        assert id1 != id2

    def test_format_as_markdown_has_source_url_comment(self):
        article = self._make_article()
        md = pc.format_as_markdown(article, domain="gcp")
        assert "<!-- source-url:" in md
        assert "https://cloud.google.com/blog/cloud-run" in md

    def test_format_as_markdown_title_with_quotes_escaped(self):
        article = self._make_article(title='Cloud Run "Serverless" Guide')
        md = pc.format_as_markdown(article, domain="gcp")
        # Title in frontmatter: double quotes replaced by single quotes
        for line in md.split("\n"):
            if line.startswith("title:"):
                assert '"Cloud Run "Serverless" Guide"' not in line  # no unescaped inner quotes
                assert "Cloud Run 'Serverless' Guide" in line  # single quotes substituted
                break

    def test_format_as_markdown_summary_truncated_at_800(self):
        long_summary = "x" * 1200
        article = self._make_article(summary=long_summary)
        md = pc.format_as_markdown(article, domain="gcp")
        # Summary in body should be at most 800 chars (from [:800] in format_as_markdown)
        # The Résumé line contains the summary
        for line in md.split("\n"):
            if line.startswith("**Résumé :**"):
                summary_content = line.replace("**Résumé :** ", "")
                assert len(summary_content) <= 800
                break


class TestSaveArticles:
    def _make_article(self, url="https://cloud.google.com/blog/test"):
        return {
            "title": "Cloud Run Best Practices",
            "url": url,
            "summary": "Best practices for Cloud Run on GCP.",
            "published_date": datetime(2026, 4, 14, 10, 0, 0),
        }

    def test_save_article_creates_file(self, tmp_path):
        seen: set = set()
        articles = [self._make_article()]
        stats = pc.save_articles(articles, "gcp", seen, min_score=0.0, raw_dir=tmp_path)
        assert stats["saved"] == 1
        files = list((tmp_path / "gcp").glob("*.md"))
        assert len(files) == 1

    def test_duplicate_article_not_saved_twice(self, tmp_path):
        seen: set = set()
        articles = [self._make_article()]
        pc.save_articles(articles, "gcp", seen, min_score=0.0, raw_dir=tmp_path)
        stats2 = pc.save_articles(articles, "gcp", seen, min_score=0.0, raw_dir=tmp_path)
        assert stats2["saved"] == 0
        assert stats2["duplicates"] == 1

    def test_tier_c_article_not_saved(self, tmp_path):
        seen: set = set()
        articles = [{
            "title": "Recipe: Sourdough Bread",
            "url": "https://example.com/sourdough",
            "summary": "How to bake sourdough.",
            "published_date": datetime(2026, 1, 1),
        }]
        stats = pc.save_articles(articles, "gcp", seen, min_score=0.3, raw_dir=tmp_path)
        assert stats["saved"] == 0
        assert stats["tier_c_filtered"] == 1

    def test_dry_run_does_not_write_files(self, tmp_path):
        seen: set = set()
        articles = [self._make_article()]
        stats = pc.save_articles(articles, "gcp", seen, min_score=0.0,
                                 raw_dir=tmp_path, dry_run=True)
        files = list(tmp_path.glob("**/*.md"))
        assert len(files) == 0
        assert stats["saved"] == 0
        assert stats["would_save"] == 1

    def test_load_save_seen_ids_roundtrip(self, tmp_path):
        seen_file = tmp_path / "seen.txt"
        original = {"prac-abc12345", "arxiv:2401.12345"}
        pc.save_seen_ids(original, seen_ids_file=seen_file)
        loaded = pc.load_seen_ids(seen_ids_file=seen_file)
        assert loaded == original

    def test_save_articles_adds_to_seen_ids(self, tmp_path):
        seen: set = set()
        articles = [self._make_article()]
        pc.save_articles(articles, "gcp", seen, min_score=0.0, raw_dir=tmp_path)
        expected_id = pc.prac_paper_id("https://cloud.google.com/blog/test")
        assert expected_id in seen

    def test_file_exists_heals_seen_ids(self, tmp_path):
        """If file exists on disk but not in seen_ids, seen_ids should be healed."""
        seen: set = set()
        articles = [self._make_article()]
        # First save — creates file
        pc.save_articles(articles, "gcp", seen, min_score=0.0, raw_dir=tmp_path)
        assert pc.prac_paper_id("https://cloud.google.com/blog/test") in seen

        # Simulate seen_ids loss (restore from backup)
        seen.clear()
        # Second save — file exists but seen is empty
        stats2 = pc.save_articles(articles, "gcp", seen, min_score=0.0, raw_dir=tmp_path)
        # Should NOT create a second file, should heal seen_ids
        files = list((tmp_path / "gcp").glob("*.md"))
        assert len(files) == 1  # still only 1 file
        assert pc.prac_paper_id("https://cloud.google.com/blog/test") in seen  # healed
