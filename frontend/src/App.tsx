import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react';
import { QueryError, sendQuery } from './api';
import type { QueryRequest, QueryResponse } from './contract';
import { Result } from './Result';
import { STARTUP_INTRO_SESSION_KEY, StartupIntro } from './StartupIntro';

const REQUEST_TIMEOUT_MS = 12 * 60 * 1000;

const examples = [
  { category: 'Find an authority', text: 'Where should I report my stolen bike?' },
  { category: 'Understand a right', text: 'What does Article 21 of the Constitution protect?' },
  { category: 'Check a provision', text: 'What is the punishment for theft under the BNS?' },
];

const services = [
  {
    number: '01',
    title: 'Understand the legal context',
    description: 'Explore plain-language guidance grounded in the verified legal material currently available to NyayaAI.',
  },
  {
    number: '02',
    title: 'Prepare with confidence',
    description: 'Organise the facts, evidence and next steps that may help when you speak with a qualified professional.',
  },
  {
    number: '03',
    title: 'Find the right support',
    description: 'Locate verified authority and emergency records when the requested service and jurisdiction are covered.',
  },
];

type State =
  | { kind: 'idle' }
  | { kind: 'loading'; request: QueryRequest }
  | { kind: 'success'; response: QueryResponse; request: QueryRequest }
  | { kind: 'error'; message: string; request: QueryRequest };

function shouldShowStartupIntro() {
  try {
    return window.sessionStorage.getItem(STARTUP_INTRO_SESSION_KEY) !== 'true';
  } catch {
    return true;
  }
}

function ArrowIcon() {
  return <svg className="arrow-icon" viewBox="0 0 20 20" aria-hidden="true"><path d="M3 10h13M11 5l5 5-5 5" /></svg>;
}

export function App() {
  const [query, setQuery] = useState('');
  const [jurisdiction, setJurisdiction] = useState('');
  const [state, setState] = useState<State>({ kind: 'idle' });
  const [inputError, setInputError] = useState('');
  const [notice, setNotice] = useState('');
  const [elapsed, setElapsed] = useState(0);
  const [showStartupIntro, setShowStartupIntro] = useState(shouldShowStartupIntro);
  const controller = useRef<AbortController | null>(null);
  const requestNumber = useRef(0);
  const questionInput = useRef<HTMLTextAreaElement>(null);
  const locationInput = useRef<HTMLInputElement>(null);
  const resultPanel = useRef<HTMLElement>(null);
  const loading = state.kind === 'loading';

  const completeStartupIntro = useCallback(() => {
    try {
      window.sessionStorage.setItem(STARTUP_INTRO_SESSION_KEY, 'true');
    } catch {
      // The intro can still complete when browser storage is unavailable.
    }
    setShowStartupIntro(false);
  }, []);

  useEffect(() => () => {
    requestNumber.current += 1;
    controller.current?.abort();
  }, []);

  useEffect(() => {
    if (!loading) return;
    const start = Date.now();
    const timer = window.setInterval(
      () => setElapsed(Math.floor((Date.now() - start) / 1000)),
      1000,
    );
    return () => window.clearInterval(timer);
  }, [loading]);

  useEffect(() => {
    if (state.kind === 'success' || state.kind === 'error') {
      resultPanel.current?.focus();
    }
  }, [state]);

  function focusQuestion() {
    document.querySelector('#question-workspace')?.scrollIntoView({ behavior: 'smooth' });
    window.setTimeout(() => questionInput.current?.focus(), 250);
  }

  function editQuestion() {
    if (
      state.kind === 'success'
      && state.response.analysis.missing_information.some(
        (field) => field.toLowerCase().includes('jurisdiction'),
      )
    ) {
      locationInput.current?.focus();
      return;
    }
    questionInput.current?.focus();
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (controller.current) return;
    const payload: QueryRequest = {
      query: query.trim(),
      jurisdiction: jurisdiction.trim() || null,
    };
    if (!payload.query || payload.query.length > 2000 || (payload.jurisdiction?.length || 0) > 100) {
      setInputError('Enter a question of 1–2,000 characters and a location of up to 100 characters.');
      questionInput.current?.focus();
      return;
    }
    setInputError('');
    setNotice('');
    setElapsed(0);
    const active = new AbortController();
    controller.current = active;
    const id = ++requestNumber.current;
    let timedOut = false;
    const timer = window.setTimeout(() => {
      timedOut = true;
      active.abort();
    }, REQUEST_TIMEOUT_MS);
    setState({ kind: 'loading', request: payload });
    try {
      const response = await sendQuery(payload, active.signal);
      if (id === requestNumber.current) {
        setState({ kind: 'success', response, request: payload });
      }
    } catch (error) {
      if (id !== requestNumber.current) return;
      const message = timedOut
        ? 'The request took too long. Your question is preserved. The server may still be processing it; check before submitting again.'
        : error instanceof QueryError
          ? error.message
          : 'The request could not be completed. Your question is still here.';
      setState({ kind: 'error', message, request: payload });
    } finally {
      window.clearTimeout(timer);
      if (id === requestNumber.current) controller.current = null;
    }
  }

  function cancel() {
    requestNumber.current += 1;
    controller.current?.abort();
    controller.current = null;
    setState({ kind: 'idle' });
    setNotice('Stopped waiting. The server may still be processing your request.');
    questionInput.current?.focus();
  }

  return <>
    <div className={showStartupIntro ? 'app-shell' : 'app-shell app-shell--ready'}>
      <a className="skip-link" href="#question">Skip to question</a>

      <header className="site-header">
        <a className="brand" href="#top" aria-label="NyayaAI home">
          <span className="brand-emblem" role="img" aria-label="Lion Capital of Ashoka, the national emblem of India" />
          <span className="brand-divider" aria-hidden="true" />
          <span className="brand-copy">
            <span className="brand-wordmark">NYAYA<span className="brand-ai">AI</span></span>
            <span className="brand-hindi" lang="hi">न्याय • ज्ञान • सहायता</span>
          </span>
        </a>
        <nav className="site-nav" aria-label="Primary navigation">
          <a href="#services">Services</a>
          <a href="#how-it-works">How it works</a>
          <a href="#legal-resources">Legal resources</a>
        </nav>
        <span className="language-indicator" aria-label="Interface language: English">EN</span>
      </header>

      <main id="top">
        <section className="hero" aria-labelledby="page-title">
          <div className="hero-ring" aria-hidden="true" />
          <div className="hero-copy">
            <div className="eyebrow hero-eyebrow"><span className="accent-line" />Technology in service of justice</div>
            <h1 id="page-title">Legal clarity,<br /><em>within reach.</em></h1>
            <p>NyayaAI helps people explore verified Indian legal information, understand the available context and identify a safer next step.</p>
            <div className="hero-actions">
              <button className="primary hero-primary" type="button" onClick={focusQuestion}>Ask NyayaAI <ArrowIcon /></button>
              <a className="text-action" href="#legal-resources">Explore legal resources</a>
            </div>
            <div className="trust-row" aria-label="NyayaAI safeguards">
              <span><strong aria-hidden="true">✓</strong> Evidence checked before display</span>
              <span className="trust-divider" aria-hidden="true" />
              <span><strong aria-hidden="true">✓</strong> BNS and Constitution coverage</span>
            </div>
          </div>

          <aside className="guidance-preview" aria-label="Example NyayaAI guidance">
            <div className="preview-rule" aria-hidden="true"><span /><span /><span /></div>
            <span className="preview-watermark brand-emblem" aria-hidden="true" />
            <span className="preview-label">An example, grounded</span>
            <blockquote className="preview-question">
              <span className="preview-quote" aria-hidden="true">“</span>
              <p>What does Article 21 of the Constitution protect?</p>
              <footer>Constitution of India · Fundamental rights</footer>
            </blockquote>
            <div className="preview-answer">
              <div className="preview-answer-header">
                <span className="ny-avatar" aria-hidden="true">NY</span>
                <span><strong>NyayaAI guidance</strong><small><i aria-hidden="true" /> Verified-source workflow</small></span>
              </div>
              <p>NyayaAI retrieves the relevant provision, prepares a plain-language response and checks it before display.</p>
              <ol>
                <li><span>1</span>Read the source-grounded summary</li>
                <li><span>2</span>Review the cited legal provision</li>
                <li><span>3</span>Check limitations before acting</li>
              </ol>
              <small className="preview-disclaimer">Information, not legal advice · Sources shown with answers</small>
            </div>
          </aside>
        </section>

        <section className="services-section" id="services" aria-labelledby="services-title">
          <div className="services-intro">
            <span className="section-kicker">Built for clarity</span>
            <h2 id="services-title">Justice begins with<br /><em>understanding.</em></h2>
          </div>
          <div className="service-grid" id="how-it-works">
            {services.map((service) => <article className="service" key={service.number}>
              <span className="service-number">{service.number}</span>
              <h3>{service.title}</h3>
              <p>{service.description}</p>
              <button className="circle-action" type="button" onClick={focusQuestion} aria-label={`Ask NyayaAI: ${service.title}`}><ArrowIcon /></button>
            </article>)}
          </div>
        </section>

        <section className="ask-section" id="question-workspace" aria-labelledby="question-heading">
          <div className="ask-intro">
            <span className="section-kicker">Start with your situation</span>
            <h2>Ask in your own words.</h2>
            <p>Share the situation without names, identity numbers or other sensitive personal details.</p>
          </div>

          <div className="workspace">
            <div className="main-column">
              <section className="question-card">
                <div className="card-heading">
                  <span className="step-number">01</span>
                  <div><h2 id="question-heading">What do you need help with?</h2><p className="muted small">Describe the situation and the kind of information you need.</p></div>
                </div>
                <form onSubmit={submit}>
                  <label htmlFor="question">Your question</label>
                  <textarea id="question" ref={questionInput} value={query} onChange={(event) => { setQuery(event.target.value); setInputError(''); }} placeholder="Tell us what happened and what you would like to understand…" rows={6} maxLength={2000} required disabled={loading} aria-describedby="question-help question-count" aria-invalid={!!inputError} />
                  <div className="input-meta"><span id="question-help">Avoid names, ID numbers and other sensitive details.</span><span id="question-count">{query.length.toLocaleString()} / 2,000</span></div>
                  <div className="location-field">
                    <label htmlFor="jurisdiction">State or jurisdiction <span className="optional">Optional</span></label>
                    <input id="jurisdiction" ref={locationInput} value={jurisdiction} onChange={(event) => setJurisdiction(event.target.value)} placeholder="e.g. Assam" maxLength={100} disabled={loading} aria-describedby="location-help" />
                    <p id="location-help" className="small muted">Use the full name. Authority guidance and source coverage can vary by location.</p>
                  </div>
                  {inputError && <p className="form-error" role="alert">{inputError}</p>}
                  <div className="submit-row">
                    <span className="small muted">Your question stays in the form<br className="desktop-break" /> if a request cannot finish.</span>
                    <button className="primary" type="submit" disabled={loading}>
                      {loading ? 'Working on your question…' : state.kind === 'success' && state.response.route === 'follow_up' ? 'Submit with details' : state.kind === 'error' ? 'Try again' : 'Get guidance'}
                      <ArrowIcon />
                    </button>
                  </div>
                </form>
              </section>

              {notice && <p className="notice" role="status">{notice}</p>}
              {loading && <section className="loading-card" aria-label="Request progress">
                <div className="loader" aria-hidden="true" />
                <div><h2 role="status">Working on your question</h2><p className="muted">Local model responses can take several minutes. You can stop waiting at any time.</p><span className="small muted">Elapsed: {Math.floor(elapsed / 60)}m {elapsed % 60}s</span></div>
                <button className="text-button" type="button" onClick={cancel}>Stop waiting</button>
              </section>}

              {(state.kind === 'success' || state.kind === 'error') && <section className="result-card" ref={resultPanel} tabIndex={-1} aria-labelledby="result-title">
                <div className="submitted-question"><span className="eyebrow">Your question</span><p>{state.request.query}</p>{state.request.jurisdiction && <span className="small muted">Requested location: {state.request.jurisdiction}</span>}</div>
                {state.kind === 'success'
                  ? <Result result={state.response} onEdit={editQuestion} />
                  : <div className="result-body"><div className="result-label warning-label">Request not completed</div><h2 id="result-title">We couldn’t get a response</h2><p role="alert">{state.message}</p><button className="secondary" onClick={() => questionInput.current?.focus()}>Review your question</button></div>}
              </section>}

              {state.kind === 'idle' && <section className="examples" aria-labelledby="examples-heading">
                <h2 id="examples-heading">Try a supported starting point</h2>
                <div className="example-grid">{examples.map((example) => <button type="button" className="example-card" key={example.category} onClick={() => { setQuery(example.text); setInputError(''); questionInput.current?.focus(); }}><span className="eyebrow">{example.category}</span><span>{example.text}</span><ArrowIcon /></button>)}</div>
              </section>}
            </div>

            <aside className="side-column" aria-label="Before using NyayaAI">
              <section className="context-card">
                <span className="mini-mark" aria-hidden="true"><ArrowIcon /></span>
                <h2>A starting point,<br /><em>with context.</em></h2>
                <div className="principle"><span>01</span><div><h3>Tell us the situation</h3><p>Include what happened and the kind of legal or civic information you need.</p></div></div>
                <div className="principle"><span>02</span><div><h3>Add your location</h3><p>The relevant authority and available records can vary by jurisdiction.</p></div></div>
                <div className="principle"><span>03</span><div><h3>Review the evidence</h3><p>Check returned sources, validation results and limitations before acting.</p></div></div>
              </section>
              <section className="boundary-note"><h3>Before you begin</h3><p>NyayaAI provides information, not professional legal advice. Generated answers may be withheld when validation fails.</p><p>For urgent danger, seek immediate local assistance. This app cannot dispatch help.</p></section>
            </aside>
          </div>
        </section>

        <section className="resources-section" id="legal-resources" aria-labelledby="resources-title">
          <div><span className="section-kicker">Current verified scope</span><h2 id="resources-title">A focused legal corpus,<br /><em>clearly disclosed.</em></h2></div>
          <div className="scope-grid">
            <article><span>Legal material</span><strong>Bharatiya Nyaya Sanhita, 2023</strong><strong>Constitution of India</strong></article>
            <article><span>Safety controls</span><strong>Citation validation</strong><strong>Claim-grounding checks</strong><strong>Answer-integrity checks</strong></article>
            <article><span>Known boundary</span><p>Coverage is intentionally limited. NyayaAI does not claim universal legal coverage or replace professional advice.</p></article>
          </div>
        </section>
      </main>

      <footer className="site-footer"><span className="footer-brand">NYAYA<span>AI</span></span><span>Legal clarity begins with verified context.</span><span>Development preview · India</span></footer>
    </div>
    {showStartupIntro && <StartupIntro onComplete={completeStartupIntro} />}
  </>;
}
