import { useEffect, useRef, useState } from 'react'
import { Send, X, Bot, Maximize2, Minimize2, RotateCcw, BookOpen, ThumbsUp, ThumbsDown } from 'lucide-react'
import { useAnalysisSession } from '../analysis/AnalysisSession'
import { askAssistant, assistantHistory, rateAssistant, citationLinks } from '../../services/assistant'
import type { AssistantMessage, AssistantCitation } from '../../services/assistant'
import type { ClassificationResult } from '../../services/classification'

function Sources({ citations }: { citations: AssistantCitation[] }) {
  const unique = new Map<string, { title: string; heading: string }>()
  for (const citation of citations) for (const url of citationLinks(citation)) {
    if (!unique.has(url)) unique.set(url, { title: citation.source?.title || citation.heading || 'Reference', heading: citation.heading })
  }
  if (!unique.size) return null
  return <details className="assistant-sources"><summary><BookOpen size={14} />Sources ({unique.size})</summary><ol>{[...unique].map(([url, source]) => <li key={url}><a href={url} target="_blank" rel="noopener noreferrer">{source.title}</a>{source.heading !== source.title && <small>{source.heading}</small>}</li>)}</ol></details>
}

function Feedback({ result, messageId }: { result: ClassificationResult; messageId: string }) {
  const [rating, setRating] = useState(''), [busy, setBusy] = useState(false), [error, setError] = useState('')
  async function rate(value: 'helpful' | 'unhelpful') {
    if (busy || rating) return
    setBusy(true); setError('')
    try { await rateAssistant(result, messageId, value); setRating(value) }
    catch { setError('Feedback was not saved. Try again.') }
    finally { setBusy(false) }
  }
  return <div className="assistant-feedback">{rating ? <span className="assistant-feedback-saved">Feedback saved</span> : <>
    <button type="button" aria-label="Mark answer helpful" disabled={busy} onClick={() => rate('helpful')}><ThumbsUp size={13} />Helpful</button>
    <button type="button" aria-label="Mark answer not helpful" disabled={busy} onClick={() => rate('unhelpful')}><ThumbsDown size={13} />Not helpful</button>
  </>}{error && <span role="alert">{error}</span>}</div>
}

export function AssistantPanel({ visible = true, wide, onToggleWide, onClose }: { visible?: boolean; wide?: boolean; onToggleWide?: () => void; onClose?: () => void }) {
  const { assistantCase: result, assistantRestoring, assistantRestoreError, retryAssistantRestore } = useAnalysisSession()
  const [conversationId, setConversationId] = useState<string>()
  const [question, setQuestion] = useState(''), [messages, setMessages] = useState<AssistantMessage[]>([])
  const [busy, setBusy] = useState(false), [error, setError] = useState('')
  const [loading, setLoading] = useState(false), [historyError, setHistoryError] = useState(''), [reload, setReload] = useState(0)
  const request = useRef<AbortController | null>(null), log = useRef<HTMLDivElement>(null)
  const lastQuestion = useRef(''), composing = useRef(false)
  const usable = !!result?.assistant_access_token
  const visibleMessages = conversationId === result?.analysis_id ? messages : []
  useEffect(() => {
    setConversationId(result?.analysis_id)
    request.current?.abort(); setBusy(false); setQuestion(''); setMessages([]); setError(''); setHistoryError('')
    const controller = new AbortController()
    if (!result?.assistant_access_token) { setLoading(false); return () => controller.abort() }
    setLoading(true)
    assistantHistory(result, controller.signal).then(rows => {
      if (!Array.isArray(rows)) throw new Error('Invalid conversation history.')
      if (!controller.signal.aborted) setMessages(rows.flatMap(row => [
        { role: 'Doctor' as const, text: row.question },
        { role: 'Assistant' as const, text: row.response.answer, id: row.id, citations: row.response.citations || [], notice: row.response.notice },
      ]))
    }).catch(() => { if (!controller.signal.aborted) setHistoryError('Conversation history could not be loaded.') })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => { controller.abort(); request.current?.abort() }
  }, [result?.analysis_id, result?.assistant_access_token, reload])
  useEffect(() => {
    if (visible && log.current) log.current.scrollTo({ top: log.current.scrollHeight, behavior: 'smooth' })
  }, [visible, messages, busy, error])
  async function send(text = question, retry = false) {
    const clean = text.trim()
    if (!result?.assistant_access_token || !clean || busy || loading) return
    const controller = new AbortController(); request.current = controller
    lastQuestion.current = clean; setBusy(true); setError(''); setQuestion('')
    if (!retry) setMessages(previous => [...previous, { role: 'Doctor', text: clean }])
    try {
      const answer = await askAssistant(clean, result, controller.signal)
      if (!controller.signal.aborted) setMessages(previous => [...previous, { role: 'Assistant', text: answer.text, id: answer.id, citations: answer.citations, notice: answer.notice }])
    } catch (failure) { if (!controller.signal.aborted) setError(failure instanceof Error ? failure.message : 'The answer could not be completed. Please retry.') }
    finally { if (!controller.signal.aborted) setBusy(false) }
  }
  return <section className="assistant-panel" aria-label="AI Assistant">
    <header className="assistant-heading"><div className="assistant-title"><span className="assistant-avatar"><Bot size={21} /></span><div><h2>AI Assistant</h2><p>Review the result. Explore the evidence.</p></div></div><div className="assistant-heading-actions">
      {onToggleWide && <button type="button" className="icon-button assistant-resize" onClick={onToggleWide} aria-label={wide ? 'Compact chat' : 'Expand chat'}>{wide ? <Minimize2 size={17} /> : <Maximize2 size={17} />}</button>}
      {onClose && <button type="button" className="icon-button" onClick={onClose} aria-label="Close assistant"><X size={19} /></button>}
    </div></header>
    <div className="assistant-context">{result ? <>Current analysis <code>{result.analysis_id.slice(0,8)}</code><span>{result.leading_class}</span></> : assistantRestoring ? 'Restoring your conversation…' : 'No active analysis'}</div>
    <div ref={log} className="assistant-messages" role="log" aria-label="Chat messages" aria-live="polite">
      {(loading || assistantRestoring) && <p className="assistant-loading" role="status">Loading conversation…</p>}
      {assistantRestoreError && <div className="assistant-recovery" role="alert"><p>{assistantRestoreError}</p><button type="button" onClick={retryAssistantRestore}>Retry saved conversation</button></div>}
      {!result && !assistantRestoring && !assistantRestoreError && <div className="assistant-empty"><Bot size={30} /><h3>Start with an analysis</h3><p>Upload a lesion image and run classification. Your result will connect here automatically.</p></div>}
      {result && !usable && <p role="status">This analysis has no assistant session. Run classification again to reconnect.</p>}
      {historyError && <div className="assistant-recovery" role="alert"><p>{historyError}</p><button type="button" onClick={() => setReload(value => value+1)}>Reload conversation</button></div>}
      {usable && !loading && !messages.length && <div className="assistant-empty"><h3>How can I help with this analysis?</h3><p>Ask about the model output or the available evidence.</p><div className="assistant-suggestions">{['Show the prediction','Explain uncertainty','Tell details about the prediction class','What are the limitations?'].map(text => <button key={text} type="button" disabled={busy} onClick={() => send(text)}>{text}</button>)}</div></div>}
      {visibleMessages.map((message, index) => <article className={`assistant-bubble assistant-bubble--${message.role.toLowerCase()}`} key={`${result?.analysis_id}-${message.id || index}`}>
        <strong className="assistant-role">{message.role === 'Doctor' ? 'You' : 'Assistant'}</strong>
        {message.notice && <div className="assistant-reference-notice">{message.notice}</div>}
        <div className="assistant-answer">{message.text.split(/\n\s*\n/).map((paragraph, i) => <p key={i}>{paragraph}</p>)}</div>
        {!!message.citations?.length && <Sources citations={message.citations} />}
        {message.role === 'Assistant' && message.id && result && <Feedback result={result} messageId={message.id} />}
      </article>)}
      {busy && <p className="assistant-thinking" role="status">Preparing your answer…</p>}
      {error && <div className="assistant-error" role="alert"><p>{error}</p><button type="button" disabled={busy} onClick={() => send(lastQuestion.current,true)}><RotateCcw size={14} />Try again</button></div>}
    </div>
    <form className="assistant-composer" onSubmit={event => { event.preventDefault(); send() }}><label className="sr-only" htmlFor="assistant-message">Message</label><textarea id="assistant-message" value={question} onChange={event => setQuestion(event.target.value)} disabled={!usable || loading || assistantRestoring} maxLength={2000} placeholder={usable ? 'Ask about this analysis…' : 'Run classification to connect…'} rows={2} onCompositionStart={() => {composing.current=true}} onCompositionEnd={() => {composing.current=false}} onKeyDown={event => { if (event.key==='Enter' && !event.shiftKey && !event.nativeEvent.isComposing && !composing.current) { event.preventDefault(); send() } }} /><button type="submit" className="assistant-send" disabled={!usable || loading || assistantRestoring || busy || !question.trim()} aria-label="Send message"><Send size={18} /></button></form>
    <p className="assistant-service-note">Case-grounded assistant · Verify answers with the linked sources</p>
  </section>
}
