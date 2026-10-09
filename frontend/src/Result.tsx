import type { ReactNode } from 'react';
import type { Evidence, QueryResponse } from './contract';

export function safeWebUrl(value: string | null): string | null {
  if (!value) return null;
  try {
    const url = new URL(value);
    return ['http:', 'https:'].includes(url.protocol) && !url.username && !url.password ? url.href : null;
  } catch { return null; }
}

export function displayJurisdiction(value: string): string {
  return value.trim().toUpperCase() === 'IN' ? 'India' : value;
}

export function shouldShowAuthorityFallback(
  verificationNote: string | null | undefined,
  authorityCount: number,
): boolean {
  return !verificationNote && authorityCount === 0;
}

function WebLink({ url, children }: { url: string | null; children: ReactNode }) {
  const href = safeWebUrl(url);
  return href ? <a href={href} target="_blank" rel="noopener noreferrer">{children}<span aria-hidden="true"> ↗</span><span className="sr-only"> (opens a new tab)</span></a> : null;
}

function Points({ title, items }: { title: string; items: string[] }) {
  if (!items.length) return null;
  return <section className="answer-section"><h3>{title}</h3><ul>{items.map((item, index) => <li key={index}>{item}</li>)}</ul></section>;
}

function Sources({ evidence }: { evidence: Evidence[] }) {
  if (!evidence.length) return null;
  return <section className="sources"><h3>Supporting sources</h3><p className="muted small">Source records and verification status are supplied by the backend.</p>
    {evidence.map((source) => <details key={`${source.chunk_id}-${source.citation_id}`}>
      <summary><span className="source-id">{source.citation_id || 'Source'}</span>{source.document_title || source.act_name || source.source_name || 'Retrieved document'}</summary>
      <div className="source-content">
        {source.citation_text && <p>{source.citation_text}</p>}
        <p className="small muted">{[source.source_publisher, source.version_label, source.section_number ? `Section / article ${source.section_number}` : null, source.subsection_number ? `Subsection ${source.subsection_number}` : null, source.clause_number ? `Clause ${source.clause_number}` : null].filter(Boolean).join(' · ')}</p>
        <blockquote>{source.content}</blockquote>
        <WebLink url={source.source_url}>{source.source_name || 'Open source'}</WebLink>
        <p className="small muted">Marked verified by the backend{source.retrieved_at ? ` · Retrieved ${source.retrieved_at}` : ''}</p>
      </div>
    </details>)}
  </section>;
}

function Checks({ result }: { result: QueryResponse }) {
  const checks = result.validation;
  if (!checks) return <p className="small muted">Answer-validation results were not returned.</p>;
  return <details className="checks"><summary>View backend validation results</summary><dl>
    {([
      ['Citation checks', checks.citation_valid],
      ['Claim-grounding checks', checks.claim_grounding_valid],
      ['Answer-integrity checks', checks.answer_integrity_valid],
    ] as const).map(([name, value]) => <div key={name}><dt>{name}</dt><dd>{value === true ? 'Passed' : value === false ? 'Not passed' : 'Not reported'}</dd></div>)}
  </dl><p className="small muted">These automated checks do not guarantee legal accuracy.</p></details>;
}

const headings: Record<QueryResponse['route'], string> = {
  legal: 'Your guidance', emergency: 'Immediate assistance', authority: 'Where to turn',
  follow_up: 'A little more context', civic: 'Service not yet available',
  out_of_scope: 'Outside the current scope', non_rag: 'More information needed',
};

export function Result({ result, onEdit }: { result: QueryResponse; onEdit: () => void }) {
  const v = result.validation;
  const failed = v && [v.citation_valid, v.claim_grounding_valid, v.answer_integrity_valid].includes(false);
  const allPassed = v?.citation_valid === true && v.claim_grounding_valid === true && v.answer_integrity_valid === true;
  const hasLegalEvidence = result.evidence.length > 0 || (result.legal_answer?.citations.length || 0) > 0;
  // The explicit backend block always wins. Also fail closed on contradictory
  // validation or a generated answer with evidence but incomplete safety checks.
  const blocked = result.answer_blocked || (result.route === 'legal' && (failed || (hasLegalEvidence && !allPassed)));

  if (blocked) return <div className="result-body"><div className="result-label warning-label">Answer withheld</div><h2 id="result-title">We couldn’t verify this answer</h2>
    <p>The answer did not pass all required checks, so it has not been displayed. You can add details to your question or seek help from a qualified professional.</p>
    <Checks result={result} /><button className="secondary" onClick={onEdit}>Edit your question</button>
  </div>;

  let content: ReactNode;
  switch (result.route) {
    case 'legal': {
      const answer = result.legal_answer;
      content = !answer ? <p>No legal answer was returned. You can edit your question and try again.</p> : <>
        <p className="answer-summary">{answer.summary}</p>
        {allPassed && <>
          <Points title="Legal basis" items={answer.legal_basis} />
          <Points title="Possible options" items={answer.possible_options} />
          <Points title="Evidence to preserve" items={answer.evidence_to_preserve} />
          <Points title="Next steps" items={answer.next_steps} />
        </>}
        <Points title="Keep in mind" items={answer.caveats} />
        <Checks result={result} />
        <Sources evidence={result.evidence.filter((source) => source.is_verified && source.citation_id !== null && answer.citations.includes(source.citation_id))} />
      </>;
      break;
    }
    case 'follow_up':
      content = <><p className="answer-summary">{result.follow_up_question || 'Please add more detail about your situation or location.'}</p><p className="muted">Your original question is kept in the form. Add the missing details and submit it again.</p><button className="secondary" onClick={onEdit}>Add details</button></>;
      break;
    case 'authority': {
      const data = result.authority_response;
      const authorities = data?.authorities.filter((a) => a.is_verified && a.is_active) || [];
      content = <>
        {data?.verification_note && <p className="muted">{data.verification_note}</p>}
        {shouldShowAuthorityFallback(data?.verification_note, authorities.length) && <p>No active, verified authority record was returned for this request. Check your location or describe the service you need.</p>}
        {authorities.map((a) => <article className="directory-card" key={a.id}>
          <span className="eyebrow">{a.jurisdiction_name}</span><h3>{a.name}</h3><p>{a.service_name}</p>
          {a.description && <p className="muted">{a.description}</p>}
          <div className="link-row"><WebLink url={a.official_portal_url}>Official portal</WebLink><WebLink url={a.complaint_url}>Complaint portal</WebLink></div>
          {a.phone_number && <p className="small">Phone: {a.phone_number}</p>}
          {a.email && <p className="small">Email: {a.email}</p>}
          <details><summary>Source and verification</summary><div className="source-content"><WebLink url={a.primary_source_url}>{a.primary_source_name}</WebLink><br /><WebLink url={a.secondary_source_url}>{a.secondary_source_name || 'Additional source'}</WebLink><p className="small muted">Marked verified by the backend{a.verified_at ? ` · ${a.verified_at}` : ''}</p>{a.verification_notes && <p className="small">{a.verification_notes}</p>}</div></details>
        </article>)}
      </>;
      break;
    }
    case 'emergency': {
      const data = result.emergency_response;
      const contacts = data?.contacts.filter((c) => c.is_verified && c.is_active) || [];
      content = <>
        <div className="emergency-notice"><strong>If you are in immediate danger, seek urgent local assistance.</strong><p>NyayaAI cannot contact or dispatch emergency services for you.</p></div>
        {data?.safety_warning && <p>{data.safety_warning}</p>}
        <Points title="Immediate actions" items={data?.immediate_actions || []} />
        {!contacts.length && <p>No active, verified emergency contacts were returned. Do not wait for this app to obtain urgent help.</p>}
        {contacts.map((c, index) => <article className="directory-card" key={index}><span className="eyebrow">{c.jurisdiction}</span><h3>{c.name}</h3><p className="contact-number">{c.phone_number}</p>
          <WebLink url={c.primary_source_url}>{c.primary_source_name}</WebLink>
          <p className="small muted">Marked verified by the backend{c.verified_at ? ` · ${c.verified_at}` : ''}</p>
          {c.verification_notes && <p className="small">{c.verification_notes}</p>}
        </article>)}
        {data?.verification_note && <p className="small muted">{data.verification_note}</p>}
      </>;
      break;
    }
    case 'civic':
      content = <p>NyayaAI recognised a civic service request, but guidance for this route is not available yet. No service-specific instructions were returned.</p>;
      break;
    case 'out_of_scope':
      content = <p>NyayaAI handles Indian legal and civic questions. Describe the legal issue, public service, or authority you need help with.</p>;
      break;
    case 'non_rag':
      content = <p>No source-grounded answer was returned for this request. Try describing what happened, where it happened, and what help you need.</p>;
      break;
  }

  return <div className="result-body">
    <div className={`result-label ${result.route === 'emergency' ? 'warning-label' : ''}`}>{result.route === 'legal' && !allPassed ? 'Information availability' : result.route.replaceAll('_', ' ')}</div>
    <h2 id="result-title">{headings[result.route]}</h2>
    {result.analysis.jurisdiction && <p className="result-location">Location: {displayJurisdiction(result.analysis.jurisdiction)}</p>}
    {content}
  </div>;
}
