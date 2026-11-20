import { AlertCircle, CheckCircle2, ChevronDown, ClipboardCheck, FileText, Save } from 'lucide-react'
import { useRef, useState } from 'react'
import type { FormEvent } from 'react'
import type { ClassificationResult } from '../../services/classification'
import { saveAssessment } from '../../services/assessments'
import type { AssessmentDecision, DoctorAssessment, NextAction } from '../../services/assessments'
import { doctorReportHtml, openPrintableReport } from '../../services/reports'
import { PrescriptionPanel } from './PrescriptionPanel'

const decisions: { value: AssessmentDecision; label: string }[] = [
  { value: 'agree', label: 'Agree' },
  { value: 'disagree', label: 'Disagree' },
  { value: 'unsure', label: 'Unsure' },
]

export function DoctorAssessmentPanel({ result, patientName, patientId, imageSnapshot }: { result: ClassificationResult; patientName: string; patientId: string; imageSnapshot: string | null }) {
  const [decision, setDecision] = useState<AssessmentDecision | ''>('')
  const [confidence, setConfidence] = useState(3)
  const [diagnosis, setDiagnosis] = useState('')
  const [differentials, setDifferentials] = useState('')
  const [note, setNote] = useState('')
  const [nextAction, setNextAction] = useState<NextAction>('additional_assessment')
  const [savedAssessment, setSavedAssessment] = useState<DoctorAssessment | null>(null)
  const [status, setStatus] = useState<'idle' | 'saving' | 'saved'>('idle')
  const [error, setError] = useState('')
  const controller = useRef<AbortController | null>(null)

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!decision || status === 'saving') return
    const active = new AbortController()
    controller.current?.abort(); controller.current = active
    setStatus('saving'); setError('')
    try {
      const saved = await saveAssessment(result, {
        patientId,
        patientName,
        imageSnapshot,
        decision,
        confidence,
        suspectedDiagnosis: diagnosis.trim(),
        differentialDiagnoses: differentials.split(',').map(value => value.trim()).filter(Boolean).slice(0, 5),
        clinicalNote: note.trim(),
        nextAction,
      }, active.signal)
      setSavedAssessment(saved)
      setStatus('saved')
    } catch (failure) {
      if (!active.signal.aborted) {
        setStatus('idle')
        setError(failure instanceof Error ? failure.message : 'Assessment could not be saved.')
      }
    }
  }

  return <div className="doctor-workflow"><details className="doctor-assessment clinical-disclosure" open aria-labelledby="doctor-assessment-title">
    <summary className="doctor-assessment__heading"><span className="disclosure-icon"><ClipboardCheck size={22} /></span><div><div className="eyebrow">Clinician review</div><h2 id="doctor-assessment-title">Doctor assessment</h2><p>Record your independent interpretation after reviewing the model output.</p></div><ChevronDown className="disclosure-chevron" size={20} /></summary>
    {status === 'saved' && savedAssessment ? <div className="assessment-saved" role="status"><CheckCircle2 size={24} /><div className="assessment-saved__content"><strong>Assessment saved</strong><p>The clinician report is ready to review and print.</p><div className="assessment-report-actions"><button type="button" className="button button--secondary" onClick={() => openPrintableReport(doctorReportHtml(savedAssessment))}><FileText size={16} />Doctor report</button></div></div></div> : <form onSubmit={submit} className="assessment-form">
      <fieldset><legend>Do you agree with the leading classification?</legend><div className="assessment-decisions">{decisions.map(item => <button key={item.value} type="button" aria-pressed={decision === item.value} className={decision === item.value ? 'selected' : ''} onClick={() => setDecision(item.value)}>{item.label}</button>)}</div></fieldset>
      <label>Clinical confidence<select value={confidence} onChange={event => setConfidence(Number(event.target.value))}><option value={1}>1 — Very uncertain</option><option value={2}>2 — Uncertain</option><option value={3}>3 — Moderate</option><option value={4}>4 — Confident</option><option value={5}>5 — Very confident</option></select></label>
      <div className="assessment-fields assessment-fields--two">
        <label>Suspected diagnosis<input value={diagnosis} maxLength={200} onChange={event => setDiagnosis(event.target.value)} placeholder="Your primary impression" /></label>
        <label>Recommended next action<select value={nextAction} onChange={event => setNextAction(event.target.value as NextAction)}><option value="additional_assessment">Additional assessment</option><option value="routine_follow_up">Routine follow-up</option><option value="dermatology_referral">Dermatology referral</option><option value="biopsy_consideration">Consider biopsy</option><option value="other">Other</option></select></label>
      </div>
      <label>Differential diagnoses<input value={differentials} onChange={event => setDifferentials(event.target.value)} placeholder="Up to five, separated by commas" /></label>
      <label>Clinical note<textarea value={note} maxLength={2000} rows={4} onChange={event => setNote(event.target.value)} placeholder="Optional observations or rationale" /></label>
      {error && <p className="assessment-error" role="alert"><AlertCircle size={16} />{error}</p>}
      <div className="assessment-actions"><p>Model output supports review; it does not replace clinical judgment. Reviewer identity will come from login.</p><button type="submit" className="button button--primary" disabled={!decision || status === 'saving'}><Save size={16} />{status === 'saving' ? 'Saving…' : 'Save assessment'}</button></div>
    </form>}
  </details><PrescriptionPanel result={result} patientName={patientName} patientId={patientId} assessment={savedAssessment} /></div>
}
