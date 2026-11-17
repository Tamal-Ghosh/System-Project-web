import { AlertCircle, ClipboardCheck, LoaderCircle } from 'lucide-react'
import { useEffect, useState } from 'react'
import { getAssessments } from '../../services/assessments'
import type { DoctorAssessment } from '../../services/assessments'

const decisionLabels = { agree: 'Agreed', disagree: 'Disagreed', unsure: 'Unsure' }
const actionLabels = {
  routine_follow_up: 'Routine follow-up', dermatology_referral: 'Dermatology referral',
  biopsy_consideration: 'Consider biopsy', additional_assessment: 'Additional assessment', other: 'Other',
}

export function ReviewsPage() {
  const [reviews, setReviews] = useState<DoctorAssessment[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    const controller = new AbortController()
    getAssessments(controller.signal).then(setReviews).catch(failure => {
      if (failure?.name !== 'AbortError') setError(failure instanceof Error ? failure.message : 'Reviews could not be loaded.')
    }).finally(() => setLoading(false))
    return () => controller.abort()
  }, [])

  return <div className="reviews-page">
    <div className="clinical-page-heading"><div><div className="eyebrow">Clinical oversight</div><h1>Reviews</h1><p>Doctor assessments recorded after model analysis.</p></div></div>
    {loading && <div className="reviews-state"><LoaderCircle className="spin" size={24} />Loading reviews…</div>}
    {error && <div className="reviews-state reviews-state--error"><AlertCircle size={24} /><strong>Reviews unavailable</strong><p>{error}</p></div>}
    {!loading && !error && reviews.length === 0 && <div className="reviews-state"><ClipboardCheck size={30} /><strong>No assessments yet</strong><p>Complete a classification and save the doctor's review to see it here.</p></div>}
    {!loading && !error && reviews.length > 0 && <div className="reviews-list">{reviews.map(review => <article className="review-card" key={review.id}>
      <header><div><span className={`review-decision review-decision--${review.decision}`}>{decisionLabels[review.decision]}</span><h2>{review.suspected_diagnosis || review.leading_class}</h2><p>Model: {review.leading_class}</p></div><time dateTime={review.created_at}>{new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(review.created_at))}</time></header>
      <div className="review-facts"><div><span>Review identity</span><strong>{review.reviewer_name || 'Authentication pending'}</strong></div><div><span>Confidence</span><strong>{review.confidence}/5</strong></div><div><span>Next action</span><strong>{actionLabels[review.next_action]}</strong></div></div>
      {review.differential_diagnoses.length > 0 && <p><strong>Differentials:</strong> {review.differential_diagnoses.join(', ')}</p>}
      {review.clinical_note && <p className="review-note">{review.clinical_note}</p>}
      <footer>Analysis {review.analysis_id.slice(0, 8)} · {review.model_version}</footer>
    </article>)}</div>}
  </div>
}
