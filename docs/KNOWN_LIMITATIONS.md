# Known limitations and release boundary

## Product scope

- The verified legal corpus currently covers the Bharatiya Nyaya Sanhita, 2023 and the Constitution of India; it is not a complete collection of Indian law.
- Verified authority coverage demonstrated in the current database is limited to India- and Assam-level records.
- The emergency directory currently contains only the verified national 112 record.
- The civic route recognises relevant requests but does not yet provide service-specific procedures.
- The application provides information, not professional legal advice or emergency dispatch.

## Model and retrieval limits

- Generated answers can still be wrong even when automated validation passes.
- Deterministic emergency classification uses a deliberately finite, high-confidence phrase and pattern set; it is not a universal emergency-language detector.
- Local inference latency depends on model size, CPU/GPU split, available memory, and warm-up state.
- The current legal vector column has no approximate-nearest-neighbour index; this is acceptable for the current corpus size but will not scale indefinitely.
- The available evaluation suite is strong regression evidence, not a statistically representative legal-accuracy benchmark.
- Qwen/Gemma tuning experiments are paused; the demonstrated application path uses `llama3.2:3b`.

## Operational limits

- The rate limiter is in memory and therefore not shared across multiple backend instances.
- PostgreSQL is containerised, but the API, frontend, and Ollama are not packaged into a production deployment.
- Centralised monitoring, alerting, backup/restore drills, secret management, TLS termination, and disaster recovery are not configured.
- Python dependencies are declared but not version-locked to a reproducible environment snapshot.
- User-facing account, history, saved-conversation, and streaming interfaces are not implemented.

## Release and branding limits

- The interface currently uses a supplied State Emblem asset. Its legal and policy implications must be reviewed before any public deployment or public repository release.
- The repository has no public software licence. Absence of a licence does not grant public reuse rights.
- The current saffron accent does not meet the desired contrast target for every possible small-text use; avoid expanding it to body text until reviewed.

## Data governance

- Legal and directory data should be updated only through a reviewed, versioned ingestion process.
- Source verification status is a product control, not a permanent guarantee that a source remains current.
- Users are instructed not to submit names, ID numbers, or other sensitive details, but a production service would still need a documented retention, deletion, and incident-response policy.

These limitations are intentionally visible. They define the next engineering work and prevent a portfolio demonstration from being mistaken for a production legal service.
