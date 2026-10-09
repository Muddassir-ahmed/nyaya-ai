# Verification evidence

## Final checkpoint

This checkpoint was verified on 1 October 2026 against the local NyayaAI stack on Windows 11 with PostgreSQL, Ollama, FastAPI, and the configured semantic reranker running.

| Verification layer | Result |
|---|---:|
| Focused C20 backend tests | 77 passed |
| Complete backend suite | 358 passed, 0 failed |
| Existing backend warnings | 6 SQLAlchemy `datetime.utcnow()` deprecation warnings |
| C20 corrected live paths | 3/3 passed |
| Final portfolio API gate | 14/14 passed, 0 failed, 0 errors |
| Frontend suite | 33 Playwright tests previously passed |
| Frontend production build | Passed |

The six backend warnings are known deprecation warnings originating from SQLAlchemy schema defaults. They did not fail tests and were not changed as part of the routing/reference correction.

## Final live matrix

| Case | Route | Result | Measured time |
|---|---|---:|---:|
| Unrelated entertainment request | `out_of_scope` | Pass | 0.02 s |
| Generic public-service problem | `civic` | Pass | 0.03 s |
| Missing jurisdiction | `follow_up` | Pass | 0.03 s |
| Verified Assam police authority | `authority` | Pass | 0.05 s |
| Unavailable Nagaland authority | `authority` | Pass | 0.02 s |
| Building fire | `emergency` | Pass | 0.03 s |
| Missing Article 999 | `legal` deterministic limitation | Pass | 0.03 s |
| Theft punishment, BNS Section 303 | `legal` | Pass | 26.47 s |
| Theft definition, BNS Section 303 | `legal` | Pass | 15.46 s |
| Assault without provocation, BNS Section 131 | `legal` | Pass | 16.11 s |
| Constitution Article 21 | `legal` | Pass | 6.62 s |
| Constitutional Preamble | `legal` | Pass | 6.44 s |
| Public water-supply complaint | `civic` | Pass | 0.01 s |
| Immediate death threat | `emergency` | Pass | 0.04 s |

For every generated legal case in the matrix:

- retrieval returned the required provision or constitutional evidence;
- the answer was not blocked;
- citation validation passed;
- claim-grounding validation passed;
- answer-integrity validation passed.

The assault case included BNS Section 131 and excluded Section 122 from the legal basis. The emergency cases did not enter legal retrieval and returned the verified active national 112 record. The unavailable Article case returned no substituted evidence.

## Preserved local evidence

The final machine-readable reports and patch package were archived under:

```text
Private final-audit archive (not included in this repository)
```

The pre-C20 source backup remains under:

```text
Private C20 source backup (not included in this repository)
```

These paths are local audit evidence, not repository dependencies.

## Reverification commands

Backend regression:

```powershell
Set-Location .\backend
.\.venv\Scripts\Activate.ps1
python -m pytest -q
```

Frontend regression:

```powershell
Set-Location .\frontend
npm test
npm run build
```

Counts should be treated as a checkpoint, not a permanently hard-coded guarantee. After future code changes, report the new command output.
