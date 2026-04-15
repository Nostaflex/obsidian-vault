---
status: active
type: reference
created: 2026-04-15
tags: [reference, claude, API, prompt-caching, tool-use, batch, files-api, anthropic]
domain: second-brain
---

# Référence — Claude API : Features clés pour architecte solution

## 1. Prompt Caching

Cache les préfixes longs (system prompt, contexte, docs) côté Anthropic.

```python
# Marquer un bloc comme cacheable
{"type": "text", "text": long_context, "cache_control": {"type": "ephemeral"}}
```

- TTL cache : **5 minutes** (inactivity reset)
- Coût lecture cache : ~10% du coût normal input
- Gain typique : -60 à -80% sur sessions longues avec contexte stable
- Éligible : messages system + premiers blocs user si statiques

**Règle** : mettre les documents longs AVANT les questions variables. Le cache se brise au premier token différent.

## 2. Tool Use (Function Calling)

```python
tools = [{
    "name": "get_weather",
    "description": "...",
    "input_schema": {"type": "object", "properties": {...}}
}]
response = client.messages.create(model=..., tools=tools, messages=[...])
# Extraire l'appel outil
if response.stop_reason == "tool_use":
    tool_block = next(b for b in response.content if b.type == "tool_use")
```

- `tool_choice`: `{"type": "auto"}` (défaut), `{"type": "any"}`, `{"type": "tool", "name": "X"}`
- Streaming + tool use : compatible, écouter `content_block_delta` type `input_json_delta`
- Parallel tool calls : Claude peut appeler N outils en une passe → répondre avec N `tool_result` blocs

## 3. Batch API (Messages Batches)

Pour traitement asynchrone de nombreuses requêtes à -50% coût.

```python
batch = client.messages.batches.create(requests=[
    {"custom_id": "req-1", "params": {"model": ..., "messages": [...]}},
    ...
])
# Polling
while batch.processing_status == "in_progress":
    batch = client.messages.batches.retrieve(batch.id)
# Résultats (JSONL stream)
for result in client.messages.batches.results(batch.id):
    print(result.custom_id, result.result)
```

- Max 10 000 requêtes par batch, 256MB total
- Délai : minutes à heures selon charge
- Idéal : nightly enrichment, classification bulk, embeddings fallback

## 4. Files API

Upload une fois, référence multiple fois. Évite re-envoi de gros fichiers.

```python
with open("doc.pdf", "rb") as f:
    file = client.beta.files.upload(file=("doc.pdf", f, "application/pdf"))
# Utiliser dans un message
{"type": "document", "source": {"type": "file", "file_id": file.id}}
```

- Formats supportés : PDF, TXT, MD, images (PNG/JPEG/GIF/WEBP)
- Durée de vie : 30 jours (ou suppression manuelle)
- Usage : RAG pipeline, analyse de corpus, documents de référence stables

## 5. Streaming

```python
with client.messages.stream(model=..., messages=[...]) as stream:
    for text in stream.text_stream:
        print(text, end="", flush=True)
    message = stream.get_final_message()
```

## Points de vigilance

- **Rate limits** : tier-based, surveiller `x-ratelimit-*` headers
- **Context window** : Opus/Sonnet 4.x = 200K tokens input, 8192 output max (sauf extended thinking)
- **Extended thinking** : disponible sur Opus, budget tokens séparé, `thinking` blocks dans la réponse
- **Vision** : images via `image` blocks (base64 ou URL publique), max ~20MB

## Liens

- [[decision-model-selection-claude]]
- Doc officielle : https://docs.anthropic.com/en/api/
