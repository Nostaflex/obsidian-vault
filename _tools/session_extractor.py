#!/usr/bin/env python3
"""
session_extractor.py — Extracteur JSONL pour Session Capture Pipeline.
Fonctions pures, testables indépendamment. Aucune dépendance externe.
"""

import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Optional

# ── Patterns privacy ─────────────────────────────────────────────────────────

PRIVACY_PATTERNS = [
    (r'\.nosync', 'nosync-path'),
    (r'work\.nosync', 'nosync-path'),
    (r'confidentiel', 'confidential-marker'),
    (r'sk-[a-zA-Z0-9\-]{20,}', 'api-key'),
    (r'Bearer\s+\S{10,}', 'bearer-token'),
    (r'password\s*[:=]\s*\S+', 'password'),
    (r'ghp_[a-zA-Z0-9]{36}', 'github-token'),
    (r'-----BEGIN\s+\w+\s+KEY', 'private-key'),
    (r'sk-ant-[a-zA-Z0-9\-]{20,}', 'anthropic-key'),
]

# ── Patterns scoring ──────────────────────────────────────────────────────────

AMPLIFIERS = {'oui', 'go', 'ok', 'yes', 'validé', 'parfait', 'super', 'done',
              'proceed', 'continue', 'allez', 'vas-y'}

CLOSURE_PATTERNS = [
    r'mergé', r'déplacé', r'commité', r'créé', r'supprimé',
    r'pushed', r'merged', r'moved', r'deleted', r'done',
    r'terminé', r'finalisé', r'résolu',
]

PROPOSAL_PATTERNS = [
    r'tu veux', r'vous voulez', r'on peut', r'je propose',
    r'options\s*:', r'approches\s*:', r'deux options',
    r'want to', r'shall i', r'should i',
]

SKIP_PATTERNS = [
    r'^#\s+/',           # skill invocations (# /resume-session)
    r'^<task-notification',  # task notifications XML
    r'^<system-reminder',    # system reminders
    r'^<ide_',               # IDE events
]


def parse_delta(transcript_path: str, last_offset: int) -> list:
    """
    Lit les lignes depuis last_offset dans le JSONL.
    Retourne uniquement les messages user/assistant avec texte substantiel.
    O(delta) — jamais de relecture complète.
    """
    messages = []
    try:
        with open(transcript_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if i < last_offset:
                    continue
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue

                msg_type = d.get('type')
                if msg_type not in ('user', 'assistant'):
                    continue

                content = d.get('message', {}).get('content', [])
                timestamp = d.get('timestamp', '')
                tools_called = []
                text = ''

                if isinstance(content, list):
                    for c in content:
                        if not isinstance(c, dict):
                            continue
                        if c.get('type') == 'text':
                            text += c.get('text', '')
                        elif c.get('type') == 'tool_use':
                            tools_called.append(c.get('name', 'unknown'))
                elif isinstance(content, str):
                    text = content

                text = text.strip()
                if not text and not tools_called:
                    continue

                messages.append({
                    'role': msg_type,
                    'text': text,
                    'tools': tools_called,
                    'timestamp': timestamp,
                    'line': i,
                })
    except (FileNotFoundError, PermissionError):
        pass

    return messages


def apply_privacy_filter(messages: list) -> list:
    """
    Redacte les patterns sensibles dans le texte de chaque message.
    Remplace le message entier par [redacted — privacy filter: {pattern}] si match.
    """
    result = []
    for msg in messages:
        text = msg.get('text', '')
        new_msg = dict(msg)
        for pattern, name in PRIVACY_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                new_msg = {**new_msg, 'text': f'[redacted — privacy filter: {name}]', 'redacted': True}
                break
        result.append(new_msg)
    return result


def score_message(msg: dict, prev_assistant: str = '') -> float:
    """
    Score de valeur décisionnelle 0.0–1.0 pour un message user.
    """
    if msg.get('role') != 'user':
        return 0.0

    text = msg.get('text', '').strip()

    # Skip patterns — score nul immédiat
    for pattern in SKIP_PATTERNS:
        if re.match(pattern, text, re.IGNORECASE | re.DOTALL):
            return 0.0

    text_lower = text.lower().strip('.,!? ')

    # Amplificateur : mot court + contexte dans l'assistant précédent
    if text_lower in AMPLIFIERS or (len(text_lower.split()) <= 3 and any(a in text_lower for a in AMPLIFIERS)):
        if prev_assistant and any(re.search(p, prev_assistant, re.IGNORECASE) for p in PROPOSAL_PATTERNS):
            return 0.85
        if prev_assistant and len(prev_assistant) > 100:
            return 0.6

    # Message trop court sans amplificateur
    if len(text) < 4:
        return 0.0

    score = 0.0

    if len(text) > 20:
        score += 0.3
    if len(text) > 60:
        score += 0.1

    if len(prev_assistant) > 200:
        score += 0.2

    if msg.get('tools'):
        score += 0.3

    return min(score, 1.0)


def detect_decision_closures(messages: list) -> list:
    """
    Retourne les paires (intention, contexte) avec score >= 0.5.
    """
    decisions = []
    prev_assistant_text = ''
    prev_assistant_tools = []

    for msg in messages:
        if msg['role'] == 'assistant':
            prev_assistant_text = msg['text']
            prev_assistant_tools = msg.get('tools', [])
            continue

        score = score_message(msg, prev_assistant=prev_assistant_text)
        if score >= 0.5:
            intention = msg['text'][:120].replace('\n', ' ').strip()

            action_summary = ''
            for pattern in CLOSURE_PATTERNS:
                m = re.search(rf'.{{0,60}}{pattern}.{{0,60}}', prev_assistant_text, re.IGNORECASE)
                if m:
                    action_summary = m.group(0).strip()
                    break
            if not action_summary and prev_assistant_text:
                action_summary = prev_assistant_text[:100].replace('\n', ' ').strip()

            decisions.append({
                'intention': intention,
                'action': action_summary,
                'tools': prev_assistant_tools,
                'timestamp': msg['timestamp'],
                'score': round(score, 2),
            })

    return decisions


def render_wip_delta(decisions: list, session_id: str,
                     last_offset: int, delta_lines: int) -> str:
    """Formate le delta en markdown append-friendly."""
    if not decisions:
        return ''

    lines = [
        f'\n<!-- extractor-debug: last_offset={last_offset}, '
        f'delta={delta_lines}l, decisions_captured={len(decisions)} -->\n'
    ]

    for d in decisions:
        ts = d['timestamp'][:16].replace('T', ' ') if d['timestamp'] else ''
        tools_str = ', '.join(d['tools']) + f' ×{len(d["tools"])}' if d['tools'] else 'aucun'
        lines.append(f"\n## [{ts}] {d['intention'][:80]}")
        if d['action']:
            lines.append(f"**Action** : {d['action'][:120]}")
        lines.append(f"**Tools** : {tools_str}")
        lines.append(f"**Score** : {d['score']}")

    return '\n'.join(lines) + '\n'


def append_to_wip(wip_path: str, content: str) -> None:
    """Append atomique via write-temp + rename."""
    wip_path = Path(wip_path)
    session_id = wip_path.stem.replace('wip-', '')

    if wip_path.exists():
        existing = wip_path.read_text(encoding='utf-8')
    else:
        existing = (
            f'---\ntype: session-wip\n'
            f'session_id: {session_id}\n'
            f'status: in-progress\n'
            f'tags: []\n'
            f'---\n\n'
            f'# Session WIP — {session_id}\n'
        )

    new_content = existing + content

    tmp_fd, tmp_path = tempfile.mkstemp(
        dir=wip_path.parent,
        prefix=f'.tmp-{wip_path.name}-',
        suffix='.md'
    )
    try:
        with os.fdopen(tmp_fd, 'w', encoding='utf-8') as f:
            f.write(new_content)
        os.replace(tmp_path, wip_path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def update_checkpoint(checkpoint_path: str, session_id: str,
                      transcript_path: str, new_offset: int,
                      wip_path: str, started_at: Optional[str] = None) -> None:
    """Écrit l'état courant dans session-checkpoint.json. Atomique."""
    data = {
        'session_id': session_id,
        'last_offset': new_offset,
        'transcript_path': transcript_path,
        'wip_path': wip_path,
        'started_at': started_at or '',
    }
    checkpoint_dir = os.path.dirname(checkpoint_path)
    if not checkpoint_dir:
        checkpoint_dir = '.'
    tmp_fd, tmp_path = tempfile.mkstemp(
        dir=checkpoint_dir,
        prefix='.tmp-checkpoint-'
    )
    try:
        with os.fdopen(tmp_fd, 'w') as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_path, checkpoint_path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def main():
    """Point d'entrée CLI."""
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--transcript', required=True)
    parser.add_argument('--session-id', required=True)
    parser.add_argument('--checkpoint', required=True)
    parser.add_argument('--wip-dir', required=True)
    parser.add_argument('--log', required=True)
    args = parser.parse_args()

    last_offset = 0
    started_at = ''
    try:
        with open(args.checkpoint) as f:
            ck = json.load(f)
            last_offset = ck.get('last_offset', 0)
            started_at = ck.get('started_at', '')
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    try:
        with open(args.transcript) as f:
            current_lines = sum(1 for _ in f)
    except FileNotFoundError:
        _log(args.log, f"ERROR transcript not found: {args.transcript}")
        sys.exit(0)

    messages = parse_delta(args.transcript, last_offset)
    if not messages:
        update_checkpoint(args.checkpoint, args.session_id,
                         args.transcript, current_lines,
                         _wip_path(args.wip_dir, args.session_id),
                         started_at)
        sys.exit(0)

    filtered = apply_privacy_filter(messages)
    decisions = detect_decision_closures(filtered)

    session_short = args.session_id[:6]
    wip_path = _wip_path(args.wip_dir, session_short)

    if decisions:
        content = render_wip_delta(decisions, session_short, last_offset, current_lines - last_offset)
        append_to_wip(wip_path, content)

    update_checkpoint(args.checkpoint, args.session_id, args.transcript,
                     current_lines, str(wip_path), started_at)

    redacted_count = sum(1 for m in filtered if m.get('redacted'))
    _log(args.log,
         f"STOP | session={session_short} | delta={current_lines - last_offset}l | "
         f"decisions={len(decisions)} | redacted={redacted_count}")


def _wip_path(wip_dir: str, session_short: str) -> Path:
    short = session_short[:6]
    return Path(wip_dir) / f"wip-{short}.md"


def _log(log_path: str, message: str) -> None:
    from datetime import datetime, timezone
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    try:
        with open(log_path, 'a') as f:
            f.write(f"{ts} | {message}\n")
    except OSError:
        pass


if __name__ == '__main__':
    main()
