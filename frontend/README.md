# NyayaAI frontend

React + TypeScript + Vite, connected to the existing public `POST /query` API.
This package contains frontend files only. It does not patch the backend,
change Ollama models, run migrations, or modify legal datasets.

## Install on Windows

The ZIP has `package.json`, `src`, and the other files **at its root**.
Extract its contents directly into `D:\nyaya-ai\frontend`.
Do not create `frontend\nyaya_frontend` or `frontend\frontend`.
If that folder now contains work of your own, keep it and review the package
before copying anything over it.

Your reported Node v24.20.0 meets the package's Node requirement.
The Python virtual environment does not need to be deactivated for npm.

In a PowerShell terminal:

```powershell
Set-Location D:\nyaya-ai\frontend
npm ci
npm run build
npm run dev
```

Run the commands one at a time; resolve an error before continuing.
Open **http://localhost:3000**. Port 3000 is fixed to match the supplied backend's
default CORS origin. Vite will report a conflict rather than silently use another port.

Keep your existing database and backend services running. If the backend is not
already running, use another PowerShell terminal:

```powershell
Set-Location D:\nyaya-ai\backend
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The frontend uses `http://localhost:8000` by default. An `.env` is not required
for this local setup. For a different API address, copy `.env.example` to
`.env.local`, set `VITE_API_BASE_URL`, and restart Vite. The API address can
include a path prefix, for example `/api` for an existing reverse proxy.
Never put secrets in a `VITE_` variable; Vite includes those values in browser code.

If you have customised the backend's CORS settings, ensure they allow the exact
frontend origin you open (`http://localhost:3000`). `127.0.0.1` is a different
browser origin. This package deliberately makes no backend configuration edits.

## First live check: no model tuning needed

1. Select the example **Where should I report my stolen bike?**
2. Leave the location blank and submit. In the supplied analyzer/orchestrator,
   this query follows the missing-jurisdiction route before legal generation.
3. The returned follow-up should ask for location. Select **Add details**, enter
   the full name **Assam**, and submit again.
4. The original question must remain visible and be submitted together with
   `jurisdiction: "Assam"`. The next result should use the authority route.
5. Depending on your database contents, this will display active, verified
   authority records or a clear empty-directory message. This frontend does
   not create or seed records.

The actual backend and database integration must be verified on your machine.
Browser fixture tests do not establish that your live services work end to end.

Model-generated legal answers may still be withheld while model tuning is
paused. A blocked result is a supported outcome, not proof of a frontend defect.

## Included behavior

- Question and optional jurisdiction, using the backend's 2,000 / 100 character limits.
- All seven response routes: legal, follow-up, emergency, authority, civic,
  out-of-scope, and non-RAG fallback.
- Runtime JSON validation, in addition to TypeScript types.
- Explicit blocked-answer handling: a blocked draft is never rendered, even if
  accidentally included in the response. Contradictory failed checks also
  withhold the answer. Evidence-bearing generated answers need all three checks.
- No-evidence informational responses remain visible without claiming that
  answer validation passed.
- Citation source details only for verified records referenced by the answer.
- Emergency and authority entries only when returned as both verified and active.
  No contact numbers, authority records, or legal source records are hardcoded.
- The civic placeholder is labelled as unavailable, not presented as completed guidance.
- Loading state, elapsed time, stop-waiting control, a 12-minute browser timeout,
  network/server errors, and manual retry. There are no automatic query retries.
- Stopping or timing out cancels the browser request; it does not guarantee that
  the server stops its ongoing work. Late results cannot replace newer results.
- Questions remain in memory in the current tab; refreshing clears them.
  This frontend does not persist or log questions. Existing backend retention
  and logging behavior is independent.
- Semantic form labels, keyboard focus handling, reduced-motion support,
  responsive layout, and safe external links. API text is never rendered as HTML.
- No analytics, remote fonts, mock-response toggle, or fabricated production data.

This portfolio-stage interface does not add account screens, saved conversations, streaming,
new backend routes, or deployment configuration. The current API has no
conversation-history endpoint. Follow-ups resubmit the full situation with
the additional location/details.

## Frontend checks

Dependencies are pinned in `package.json` and `package-lock.json`.

Latest reported verification on 28 September 2026:

- TypeScript checking and the production build passed.
- All **33 automated checks passed**.
- Desktop and mobile production-build screenshots were inspected; no browser
  page errors or horizontal mobile overflow were observed.
- Browser tests ran on Chromium 153 after installing the Playwright-managed
  browser with `npx playwright install chromium`.
- These checks used synthetic API fixtures, not your live backend or Ollama.

```powershell
Set-Location D:\nyaya-ai\frontend
npm run build
npx playwright install chromium
npm test
```

Stop the frontend dev server before `npm test`; the test runner starts its own
server on port 3000 and refuses to reuse an unrelated running server. Backend
and Ollama are not needed for these tests: requests are intercepted with
clearly synthetic fixtures defined only under `tests`.

The browser checks cover request shape, every route, null payloads, blocked
draft suppression, failed/missing validation, follow-up context, verified-only
directories, unsafe URLs, network failures, HTTP errors, malformed JSON,
manual retry, cancellation, timeout, text escaping, and mobile width.

The latest reported full backend result is **301 passed**, with six datetime
deprecation warnings. The separate C16 live acceptance matrix passed 7/7 routes.

## Files

- `src/contract.ts`: response schemas and derived TypeScript types.
- `src/api.ts`: HTTP client and safe error messages.
- `src/App.tsx`: form, request lifecycle, and page layout.
- `src/Result.tsx`: route-specific results, validation gates, and sources.
- `src/StartupIntro.tsx`: session-scoped startup introduction with reduced-motion support.
- `src/styles.css`: responsive presentation.
- `src/startup-intro.css`: startup-intro presentation and animation.
- `tests/`: contract, route, presentation, branding, startup, and responsive browser checks.

For deployment later, set the intended API address before building and serve
the generated `dist` folder with an appropriate static host or reverse proxy.
This development package alone is not a production-readiness sign-off.
