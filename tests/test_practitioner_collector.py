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
        published = self._now() - timedelta(hours=1)
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
