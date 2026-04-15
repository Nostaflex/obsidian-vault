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
