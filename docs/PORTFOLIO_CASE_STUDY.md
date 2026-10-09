# NyayaAI portfolio case study

## Problem

People often describe legal and civic problems as situations, not statute names. A conventional chatbot may answer before it knows the jurisdiction, confuse emergency help with legal research, or produce a fluent legal claim without reliable support. NyayaAI explores a safer product pattern for Indian legal and civic assistance.

## My approach

I built an orchestration layer that decides which subsystem should handle a request before invoking a language model. Emergency, missing-jurisdiction, authority-directory, civic, out-of-scope, exact constitutional-reference, and generated legal-answer paths have different safety requirements and therefore different behavior.

For generated legal answers, I combined semantic and lexical retrieval, reranked the fused candidates, attached stable evidence IDs, and ran three independent validation stages after generation. If correction is possible, the system gets one retry over exactly the same evidence. Otherwise it withholds the draft.

## Key engineering decisions

### Route before generation

An emergency response must not wait for a local language model. A directory lookup must not invent an office or phone number. An unavailable constitutional Article must not be replaced with a similar provision. These cases use deterministic or database-backed paths.

### Treat provenance as data

Sources, documents, legal versions, sections, chunks, authorities, and emergency contacts retain provenance and verification state. Retrieval is useful only when the evidence can be traced back to a verified source.

### Fail closed

The system prefers a visible limitation or withheld answer over unsupported confidence. The frontend also validates the response and refuses to show a generated draft when backend status and validation fields disagree.

### Make regressions executable

The project includes focused tests for retrieval normalization, provision qualifiers, penalty grounding, retry feedback, citation checks, routing, emergency behavior, and frontend response handling. Saved-answer regressions turned observed model failures into deterministic test cases.

## Verified outcome

The final reported automated results were 358 passing backend tests, 33 passing frontend tests, and a successful production frontend build. A focused C20 regression suite passed 77 tests. The final live portfolio matrix passed all 14 integrated cases against running PostgreSQL, Ollama, and the backend API with zero failures and zero runtime errors.

The final matrix exercised out-of-scope and civic routing, jurisdiction follow-up, verified and unavailable authority records, fire and immediate personal-safety emergencies, missing and existing constitutional references, the Preamble, theft definition and punishment, and assault without provocation. All generated legal answers in the gate were unblocked only after citation, claim-grounding, and answer-integrity checks passed.

On the development machine, deterministic cases completed in 0.01–0.05 seconds. The generated cases completed in approximately 6–27 seconds. The immediate death-threat route completed in 0.04 seconds and returned the verified active national 112 contact without entering legal retrieval.

## What I would build next

1. Expand legal and authority coverage through a versioned, reviewable ingestion workflow.
2. Replace the civic placeholder with verified service-specific procedures.
3. Add production observability, shared rate limiting, secret management, and deployment automation.
4. Benchmark retrieval and validation on a larger labelled legal evaluation set.
5. Improve model latency without relaxing evidence or validation gates.
6. Resolve branding/licensing questions before making the repository or deployment public.

## Honest boundary

NyayaAI is a strong portfolio-stage system, not a complete Indian legal database or professional legal service. Its value is the architecture, safety boundaries, provenance model, regression discipline, and working end-to-end slice—not a claim of nationwide legal coverage.
