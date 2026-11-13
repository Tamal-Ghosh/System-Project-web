import { Send, X } from 'lucide-react'

export function AssistantPanel({ caseId, onClose }: { caseId?: string; onClose?: () => void }) {
  return <section className="assistant-panel" aria-label="AI Assistant">
    <header className="assistant-heading"><div><h2>AI Assistant</h2><p className="muted small">{caseId ? `Context: ${caseId}` : 'No case selected'}</p></div>{onClose && <button type="button" className="icon-button" onClick={onClose} aria-label="Close assistant"><X size={18} /></button>}</header>
    <div className="assistant-messages" role="log" aria-label="Chat messages" aria-live="polite" />
    <div className="assistant-composer"><label className="sr-only" htmlFor="assistant-message">Message</label><textarea id="assistant-message" placeholder="Type a message…" rows={2} /><button type="button" className="icon-button" disabled aria-label="Send message — assistant not connected" title="Assistant service is not connected"><Send size={18} aria-hidden="true" /></button></div>
    <p className="assistant-service-note">Assistant not connected</p>
  </section>
}
