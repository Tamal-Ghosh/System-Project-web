import type { ReactNode } from 'react'
import { Layers3 } from 'lucide-react'

export function EmptyState({ title, description, action, compact = false }: { title: string; description: string; action?: ReactNode; compact?: boolean }) {
  return <div className={`empty-state ${compact ? 'empty-state--compact' : ''}`}>
    <div className="empty-icon"><Layers3 size={23} aria-hidden="true" /></div>
    <h2>{title}</h2><p className="muted">{description}</p>{action}
  </div>
}
