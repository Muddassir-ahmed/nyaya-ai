import { queryResponseSchema, type QueryRequest, type QueryResponse } from './contract';

export class QueryError extends Error {}

function apiBase(): string {
  const raw = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').trim();
  let url: URL;
  try { url = new URL(raw, window.location.origin); }
  catch { throw new QueryError('The API address is not configured correctly.'); }
  if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password || url.search || url.hash) {
    throw new QueryError('The API address is not configured correctly.');
  }
  return url.href.replace(/\/+$/, '');
}

export async function sendQuery(
  payload: QueryRequest,
  signal: AbortSignal,
): Promise<QueryResponse> {
  let response: Response;
  try {
    response = await fetch(`${apiBase()}/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      credentials: 'omit',
      cache: 'no-store',
      body: JSON.stringify(payload),
      signal,
    });
  } catch (error) {
    if (signal.aborted || error instanceof QueryError) throw error;
    throw new QueryError('Could not reach NyayaAI. Check that the backend is running and your connection is available.');
  }

  if (!response.ok) {
    const messages: Record<number, string> = {
      401: 'The server requires sign-in for this request. Please check the backend configuration.',
      403: 'The server did not allow this request.',
      404: 'The question endpoint was not found. Check the API address.',
      422: 'The server could not accept the question. Use 1–2,000 characters and a location of up to 100 characters.',
      429: 'Too many requests. Please wait before trying again.',
    };
    throw new QueryError(messages[response.status] || `NyayaAI could not complete the request (HTTP ${response.status}). Your question is still here.`);
  }

  let json: unknown;
  try { json = await response.json(); }
  catch { throw new QueryError('The server returned an unreadable response. Please try again.'); }
  const parsed = queryResponseSchema.safeParse(json);
  if (!parsed.success) {
    throw new QueryError('The server response did not match the expected format. No answer has been displayed.');
  }
  return parsed.data;
}

// No request or response content is persisted or logged by this client.
// Server-side logging and retention are controlled by the existing backend.
