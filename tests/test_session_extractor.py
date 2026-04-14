"""Tests unitaires pour _tools/session-extractor.py"""
import json
import os
import sys
import tempfile
import pytest
from pathlib import Path

# Ajouter _tools au path
sys.path.insert(0, str(Path(__file__).parent.parent / "_tools"))
from session_extractor import (
    parse_delta,
    apply_privacy_filter,
    score_message,
    detect_decision_closures,
    render_wip_delta,
    append_to_wip,
    update_checkpoint,
)

FIXTURES = Path(__file__).parent / "fixtures"


# ── parse_delta ──────────────────────────────────────────────────────────────

def test_parse_delta_reads_only_new_lines():
    """Vérifie que seules les lignes depuis last_offset sont lues."""
    path = FIXTURES / "session-short.jsonl"
    all_msgs = parse_delta(str(path), 0)
    partial = parse_delta(str(path), 4)
    assert len(partial) < len(all_msgs)

def test_parse_delta_returns_user_and_assistant():
    """Vérifie que user et assistant sont retournés, pas les autres types."""
    path = FIXTURES / "session-short.jsonl"
    msgs = parse_delta(str(path), 0)
    roles = {m["role"] for m in msgs}
    assert roles <= {"user", "assistant"}

def test_parse_delta_empty_file():
    """Pas d'exception sur fichier vide."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        f.write("")
        tmp = f.name
    try:
        result = parse_delta(tmp, 0)
        assert result == []
    finally:
        os.unlink(tmp)


# ── apply_privacy_filter ─────────────────────────────────────────────────────

def test_privacy_filter_api_key():
    """sk-ant-xxx est redacté."""
    msgs = [{"role": "user", "text": "token: sk-ant-api03-xxxxxxxxxxx", "timestamp": "", "tools": []}]
    result = apply_privacy_filter(msgs)
    assert "sk-ant" not in result[0]["text"]
    assert "[redacted" in result[0]["text"]

def test_privacy_filter_nosync():
    """work.nosync est redacté."""
    path = FIXTURES / "session-privacy.jsonl"
    msgs = parse_delta(str(path), 0)
    filtered = apply_privacy_filter(msgs)
    texts = " ".join(m["text"] for m in filtered)
    assert "work.nosync" not in texts

def test_privacy_filter_preserves_clean_messages():
    """Messages sans patterns sensibles sont préservés intacts."""
    msgs = [{"role": "user", "text": "quelle est l'architecture gpparts ?", "timestamp": "", "tools": []}]
    result = apply_privacy_filter(msgs)
    assert result[0]["text"] == "quelle est l'architecture gpparts ?"


# ── score_message ────────────────────────────────────────────────────────────

def test_score_amplifier_go_after_proposal():
    """'go tier A' après réponse assistant longue = score >= 0.5."""
    msg = {"role": "user", "text": "go tier A", "timestamp": "", "tools": []}
    prev = "22 fichiers S-tier déplacés. Tu veux aussi les A ? Je peux déplacer les A-tier maintenant si tu le souhaites."
    score = score_message(msg, prev_assistant=prev)
    assert score >= 0.5

def test_score_skill_invocation_zero():
    """Message commençant par '# /' = score 0.0."""
    msg = {"role": "user", "text": "# /resume-session — Contexte rapide\n\nObjectif token-efficient", "timestamp": "", "tools": []}
    score = score_message(msg, prev_assistant="")
    assert score == 0.0

def test_score_short_no_context_zero():
    """Message ultra-court sans contexte assistant = score < 0.5."""
    msg = {"role": "user", "text": "ok", "timestamp": "", "tools": []}
    score = score_message(msg, prev_assistant="")
    assert score < 0.5


# ── detect_decision_closures ─────────────────────────────────────────────────

def test_detect_zero_decisions_empty_session():
    """Session sans décisions → liste vide."""
    msgs = [
        {"role": "user", "text": "ok", "timestamp": "2026-04-15T10:00:00Z", "tools": []},
        {"role": "assistant", "text": "...", "timestamp": "2026-04-15T10:00:01Z", "tools": []},
    ]
    filtered = apply_privacy_filter(msgs)
    decisions = detect_decision_closures(filtered)
    assert decisions == []


# ── append_to_wip ────────────────────────────────────────────────────────────

def test_append_atomicity():
    """append_to_wip crée et appende correctement, 2 appels successifs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        wip_path = os.path.join(tmpdir, "wip-test.md")
        append_to_wip(wip_path, "## Decision 1\nContenu\n")
        append_to_wip(wip_path, "## Decision 2\nContenu\n")
        content = open(wip_path).read()
        assert "Decision 1" in content
        assert "Decision 2" in content
