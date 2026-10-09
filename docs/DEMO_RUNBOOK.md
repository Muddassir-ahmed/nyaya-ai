# NyayaAI demo runbook

## Before the demo

Confirm that Docker Desktop and Ollama are running. The configured local models are `llama3.2:3b` for generation and `nomic-embed-text` for embeddings.

Start PostgreSQL:

```powershell
Set-Location <repository-root>
docker compose up -d postgres
docker ps --filter "name=nyaya-postgres"
```

Start the backend in a separate terminal:

```powershell
Set-Location .\backend
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload
```

Wait for `Application startup complete.` Model preloading can make startup slower than deterministic request handling.

Start the frontend in another terminal:

```powershell
Set-Location .\frontend
npm run dev
```

Open `http://localhost:3000` and confirm `http://127.0.0.1:8000/health` reports healthy.

## Recommended five-minute sequence

1. Ask: `Where should I report my stolen bike?`
   - Explain that the system requests jurisdiction instead of guessing.
2. Supply `Assam`.
   - Show the verified Assam Police authority record and provenance.
3. Ask: `What is the punishment for theft?`
   - Show Section 303 evidence and the three passing validators.
4. Ask: `What does Article 999 of the Constitution of India say?`
   - Show the deterministic not-found response and lack of substituted evidence.
5. Ask: `What does Article 21 of the Constitution of India say?`
   - Contrast successful exact structured resolution with the previous case.
6. Explain, rather than simulate at length, that a fire or immediate death-threat query bypasses the LLM and uses verified emergency records.

## Optional safety demonstration

Use this exact non-live demonstration sentence:

```text
Someone is threatening to kill me right now and is standing outside my home.
```

Expected behavior: `emergency` route, no legal retrieval, police emergency category, deterministic immediate actions, and the verified active 112 record.

Do not present the application as an emergency-dispatch service. It cannot place calls or dispatch assistance.

## Talking points

- Routing happens before generation.
- Exact references and directories are structured, not invented by the LLM.
- Legal generation uses hybrid retrieval and stable evidence IDs.
- Citation, claim-grounding, and integrity validation all gate display.
- One evidence-locked correction is allowed; a second invalid draft is withheld.
- Coverage is deliberately limited and visibly documented.

## Demo recovery

- If the frontend reports a network failure, check `/health` and confirm the backend terminal is still running.
- If a generated request is slow, run `ollama ps` and allow the configured model to warm.
- If PostgreSQL is unavailable, check `docker ps` and `/health/db`.
- Do not switch models or modify data immediately before a portfolio demonstration.
