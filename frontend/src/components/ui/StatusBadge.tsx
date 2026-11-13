import type { CaseStatus } from '../../contracts'

const labels: Record<CaseStatus, string> = { draft: 'Draft', awaiting_review: 'Awaiting review', reviewed: 'Reviewed' }
export function StatusBadge({ status }: { status: CaseStatus }) {
  return <span className={`status-badge status-badge--${status}`}><i aria-hidden="true" />{labels[status]}</span>
}
