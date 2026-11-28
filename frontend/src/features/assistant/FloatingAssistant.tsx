import { useEffect, useRef, useState } from 'react'
import { MessageSquare } from 'lucide-react'
import { useLocation } from 'react-router-dom'
import { AssistantPanel } from './AssistantPanel'

export function FloatingAssistant() {
  const [open, setOpen] = useState(false)
  const [wide, setWide] = useState(false)
  const trigger = useRef<HTMLButtonElement>(null), windowRef = useRef<HTMLDivElement>(null)
  const location = useLocation()
  function close() { setOpen(false); trigger.current?.focus() }
  useEffect(() => { setOpen(false) }, [location.pathname])
  useEffect(() => {
    if (!open) return
    windowRef.current?.querySelector<HTMLButtonElement>('button')?.focus()
    function onKey(event: KeyboardEvent) { if (event.key === 'Escape') close() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open])
  return <div className={`floating-assistant ${wide ? 'assistant-wide' : ''}`}>
    <div ref={windowRef} id="assistant-window" className="assistant-window" hidden={!open} inert={!open} role="dialog" aria-modal="false" aria-label="AI Assistant chat">
      <AssistantPanel visible={open} wide={wide} onToggleWide={() => setWide(value => !value)} onClose={close} />
    </div>
    <button ref={trigger} type="button" className="assistant-launcher" onClick={() => open ? close() : setOpen(true)} aria-label={open ? 'Close AI Assistant' : 'Open AI Assistant'} aria-expanded={open} aria-controls="assistant-window"><MessageSquare size={22} strokeWidth={1.7} aria-hidden="true" /></button>
  </div>
}
