import { useEffect, useRef, useState } from 'react'
import { MessageSquare } from 'lucide-react'
import { useMatch } from 'react-router-dom'
import { AssistantPanel } from './AssistantPanel'

export function FloatingAssistant() {
  const [open, setOpen] = useState(false)
  const trigger = useRef<HTMLButtonElement>(null)
  const windowRef = useRef<HTMLDivElement>(null)
  const match = useMatch('/cases/:caseId')
  const caseId = match?.params.caseId !== 'new' ? match?.params.caseId : undefined

  function close() {
    setOpen(false)
    trigger.current?.focus()
  }

  useEffect(() => {
    if (!open) return
    windowRef.current?.querySelector<HTMLButtonElement>('button')?.focus()
    function onKey(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setOpen(false)
        trigger.current?.focus()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open])

  return <div className="floating-assistant">
    {open && <div ref={windowRef} id="assistant-window" className="assistant-window" role="dialog" aria-modal="false" aria-label="AI Assistant chat"><AssistantPanel caseId={caseId} onClose={close} /></div>}
    <button ref={trigger} type="button" className="assistant-launcher" onClick={() => open ? close() : setOpen(true)} aria-label={open ? 'Close AI Assistant' : 'Open AI Assistant'} aria-expanded={open} aria-controls={open ? 'assistant-window' : undefined}><MessageSquare size={22} strokeWidth={1.7} aria-hidden="true" /></button>
  </div>
}
