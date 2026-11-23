import type { ClassificationResult } from './classification'

export interface AssistantCitation {
  chunk_id: string
  heading: string
  reference_urls?: string[]
  source?: { title?: string; source_url?: string; version?: string; document_type?: string }
}
export interface AssistantMessage { role: 'Doctor' | 'Assistant'; text: string; id?: string; citations?: AssistantCitation[]; notice?: string }
const sessionKey = 'dermascope.assistant.case'

export function rememberAssistantCase(result: ClassificationResult) {
  if (!result.assistant_access_token) return
  try { sessionStorage.setItem(sessionKey, JSON.stringify({id: result.analysis_id, token: result.assistant_access_token})) } catch { /* Storage can be disabled. */ }
}
export async function restoreAssistantCase(signal: AbortSignal): Promise<ClassificationResult | null> {
  let saved: {id: string; token: string}
  try { saved = JSON.parse(sessionStorage.getItem(sessionKey) || 'null') } catch { return null }
  if (!saved || typeof saved.id !== 'string' || typeof saved.token !== 'string') return null
  const response = await fetch(`/api/v1/chat/case/${encodeURIComponent(saved.id)}`, {signal, headers: {'X-Case-Token': saved.token}})
  if (response.status === 403 || response.status === 404) { sessionStorage.removeItem(sessionKey); return null }
  if (!response.ok) throw new Error('Saved conversation could not be restored.')
  const data = await response.json()
  if (data.analysis_id !== saved.id || !Array.isArray(data.scores)) throw new Error('Invalid saved conversation.')
  return {...data, assistant_access_token: saved.token} as ClassificationResult
}
export function citationLinks(citation: AssistantCitation): string[] {
  const candidates = citation.reference_urls?.length ? citation.reference_urls : [citation.source?.source_url || '']
  const links: string[] = []
  for (const value of candidates) {
    try {
      const url = new URL(value, window.location.origin)
      if (url.username || url.password) continue
      if (value.startsWith('/api/v1/model/reference') && url.origin === window.location.origin && url.pathname === '/api/v1/model/reference') links.push(url.pathname + url.search)
      else if (value.toLowerCase().startsWith('https://') && url.protocol === 'https:') links.push(url.href)
    } catch { /* Unusable source identifiers remain plain text. */ }
  }
  return [...new Set(links)]
}
export async function askAssistant(question: string, result: ClassificationResult, signal: AbortSignal): Promise<{text: string; id: string; citations: AssistantCitation[]; notice?: string}> {
  if (!result.assistant_access_token) throw new Error('Run classification again to start an assistant session.')
  const response = await fetch('/api/v1/chat/query', { method: 'POST', signal,
    headers: {'Content-Type': 'application/json', 'X-Case-Token': result.assistant_access_token},
    body: JSON.stringify({analysis_id: result.analysis_id, question}) })
  const data = await response.json()
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Assistant request failed.')
  if (data.analysis_id !== result.analysis_id || data.input_hash !== result.input_hash || data.model_version !== result.model_version) throw new Error('Assistant evidence does not match this analysis.')
  return {text: data.answer, id: data.message_id, citations: Array.isArray(data.citations) ? data.citations : [], notice: typeof data.notice==='string' ? data.notice : undefined}
}
export async function assistantHistory(result: ClassificationResult, signal: AbortSignal) {
  if (!result.assistant_access_token) return []
  const response = await fetch(`/api/v1/chat/history/${result.analysis_id}`, {signal, headers: {'X-Case-Token': result.assistant_access_token}})
  if (!response.ok) throw new Error('Chat history could not be loaded.')
  return response.json() as Promise<{id: string; question: string; response: {answer: string; citations?: AssistantCitation[]; notice?: string}}[]>
}
export async function rateAssistant(result: ClassificationResult, messageId: string, rating: 'helpful' | 'unhelpful') {
  const response = await fetch('/api/v1/chat/feedback', {method: 'POST', headers: {'Content-Type': 'application/json', 'X-Case-Token': result.assistant_access_token ?? ''}, body: JSON.stringify({analysis_id: result.analysis_id, message_id: messageId, rating})})
  if (!response.ok) throw new Error('Feedback could not be saved.')
}
