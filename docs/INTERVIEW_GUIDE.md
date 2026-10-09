# NyayaAI interview guide

## Thirty-second explanation

NyayaAI is a situation-aware Indian legal and civic assistant. It routes emergencies and directory requests before generation, asks for jurisdiction when it matters, retrieves verified legal evidence with hybrid search, and validates every generated legal answer for citations, claim grounding, and rule integrity. If those checks do not pass, the answer is withheld.

## Two-minute walkthrough

1. Start with a stolen-bike question without a location. Show that the app asks for jurisdiction instead of guessing.
2. Add Assam. Show the verified authority-directory result without invoking legal generation.
3. Ask about punishment for theft. Explain hybrid retrieval, evidence IDs, local generation, three validators, and the fail-closed result contract.
4. Ask for Article 999. Show the deterministic unavailable-reference response and explain why semantic substitution would be unsafe.
5. Ask for Article 21 to contrast valid exact resolution with the unavailable-reference path.
6. Mention that fire and high-confidence immediate-threat queries bypass the language model and return only verified emergency records.

## Likely technical questions

### Why not send every query to the LLM?

Different requests have different failure costs. Emergency guidance, exact references, and authority contacts should be deterministic or database-backed. Routing reduces latency, hallucination risk, and unnecessary model use.

### Why use both vector and lexical retrieval?

Vector search handles paraphrases; full-text search preserves exact legal terms and identifiers. Reciprocal-rank fusion combines rankings without assuming their score scales are comparable, and a CrossEncoder then reranks the smaller candidate set.

### What does jurisdiction-aware mean here?

The analyzer tracks whether location is required. The orchestrator can request missing jurisdiction before looking up an authority, and directory results are filtered to verified, active records for the requested jurisdiction or an explicit fallback policy.

### How do you reduce hallucinations?

The system limits generation to verified evidence, assigns evidence IDs, validates citations, checks material claims against that evidence, checks qualified legal rules for integrity, permits only one evidence-locked correction, and withholds the result on final failure.

### Why is the retry safe?

It cannot retrieve new material or change the evidence set. The validator feedback identifies a bounded correction, the answer is regenerated against the same evidence, and every validator runs again.

### How is an unavailable Article handled?

Exact Constitution references use structured lookup. If the requested Article is not in the loaded verified version, NyayaAI says so. It does not infer a nearby Article through semantic similarity.

### How do you avoid treating every threat question as an emergency?

The immediate-threat rule is narrow and conjunctive. It looks for threat language, a violent-harm verb, a first-person target, and an immediate-time marker. A statement about a threat last year and a general question about punishment for threats remain legal-information cases rather than emergency cases.

### What bug did the exact-reference regression catch?

The earlier Article grammar allowed free-standing letters after a number, so “Article 21 of” could be parsed as the identifier `21 of`. The corrected grammar accepts bounded identifiers such as `21A`, `239AA`, and hyphenated suffixes while stopping before ordinary following words.

### Why local Ollama models?

They keep the development pipeline local and make model choice inspectable. The tradeoff is latency and hardware sensitivity; the warmed legal acceptance query took roughly 26 seconds on the tested machine.

### What happens if the model or reranker is unavailable?

Deterministic routes do not need legal generation. Model-dependent requests surface controlled failures or withheld outputs. Startup warm-up makes availability visible early but does not turn an inference failure into invented guidance.

### What security controls exist?

The backend uses JWT authentication, password hashing, request IDs, CORS configuration, security headers, request-size limits, and rate limiting. The frontend treats API data as untrusted, validates it with Zod, renders text rather than HTML, and rejects unsafe source URLs.

### What is not production-ready?

Coverage is limited, civic guidance is a placeholder, the rate limiter is in-memory, deployment and central observability are not configured, dependency versions are not fully locked for Python, and the State Emblem/public-release question is unresolved.

### How was it tested?

There are unit, service, API, regression, and browser tests. The final reported results were 358 backend tests and 33 frontend tests. A focused C20 suite passed 77 tests, C20 live verification passed 3/3, and the final portfolio matrix passed 14/14 cases with zero failures and zero errors.

## Design tradeoffs to discuss

| Decision | Benefit | Cost |
|---|---|---|
| Local models | Privacy-oriented development and no hosted inference dependency | Slower responses and hardware variance |
| Fail-closed validation | Safer legal output | Some useful drafts are withheld |
| Verified-only directories | Prevents fabricated contacts | Sparse coverage produces explicit empty results |
| Structured exact references | Prevents nearby-provision substitution | Requires high-quality structured ingestion |
| Single controlled retry | Corrects bounded formatting/grounding errors | Adds latency when the first draft fails |

## Demo cautions

- Start PostgreSQL, Ollama, and the backend before the frontend.
- Warm models before a timed demo.
- Use the verified final portfolio cases rather than improvising unsupported jurisdictions.
- Describe the app as information and a development preview, not legal advice.
- Do not claim nationwide coverage or production deployment.
- Do not publish the repository until emblem usage and software licensing are resolved.
