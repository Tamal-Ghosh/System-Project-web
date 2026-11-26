import { AlertCircle, ArrowLeft, FileText, LoaderCircle, Save } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import { useAnalysisSession } from '../analysis/AnalysisSession'
import { getAssessments, saveAssessment, updateAssessment } from '../../services/assessments'
import type { AssessmentDecision, DoctorAssessment, NextAction } from '../../services/assessments'
import { parseReportDetails, serializeReportDetails } from '../../services/reports'

const decisions: { value: AssessmentDecision; label: string }[] = [
  { value: 'agree', label: 'Agree' },
  { value: 'disagree', label: 'Disagree' },
  { value: 'unsure', label: 'Unsure' },
]

const ABCDE_AND_DERMOSCOPY_FLAGS = [
  'A: Asymmetry',
  'B: Irregular / notched border',
  'C: Color variegation',
  'D: Diameter > 6 mm',
  'E: Evolving / recent change',
  'Atypical pigment network',
  'Irregular dots / globules',
  'Blue-white veil',
  'Atypical vascular pattern',
  'Ulceration / crusting',
]

const DEFAULT_SAFETY_ADVICE =
  'Advised to monitor for ABCDE changes (asymmetry, border, color, diameter, evolution), bleeding, or ulceration and seek prompt review.'

export function MakeReportPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { reportId } = useParams<{ reportId: string }>()
  const isEditMode = Boolean(reportId)
  const routeReport = (location.state as { report?: DoctorAssessment } | null)?.report

  const { result, patientName, patientId, age, sex, site, reportImageSnapshot } = useAnalysisSession()
  const [editingReport, setEditingReport] = useState<DoctorAssessment | null>(routeReport ?? null)
  const [loadingEdit, setLoadingEdit] = useState(isEditMode && !routeReport)

  const initialDetails = parseReportDetails(routeReport?.clinical_note)

  const [clinicName, setClinicName] = useState(initialDetails?.clinicName || 'DermaScope Clinical Unit')
  const [clinicAddress, setClinicAddress] = useState(initialDetails?.clinicAddress || '')
  const [clinicContact, setClinicContact] = useState(initialDetails?.clinicContact || '')

  const [duration, setDuration] = useState(initialDetails?.duration || '')
  const [reportedChanges, setReportedChanges] = useState(initialDetails?.reportedChanges || '')
  const [symptoms, setSymptoms] = useState(initialDetails?.symptoms || '')
  const [relevantHistory, setRelevantHistory] = useState(initialDetails?.relevantHistory || '')

  const [abcdeFlags, setAbcdeFlags] = useState<string[]>(initialDetails?.abcdeFlags ?? [])
  const [keyFindings, setKeyFindings] = useState(initialDetails?.keyFindings || '')
  const [observations, setObservations] = useState(
    initialDetails?.observations || (!initialDetails && routeReport?.clinical_note ? routeReport.clinical_note : '')
  )
  const [measurements, setMeasurements] = useState(initialDetails?.measurements || 'Not measured')
  const [associatedObservations, setAssociatedObservations] = useState(initialDetails?.associatedObservations || 'Not assessed')

  const [decision, setDecision] = useState<AssessmentDecision | ''>(routeReport?.decision || 'agree')
  const [confidence, setConfidence] = useState(routeReport?.confidence ?? 4)
  const [diagnosis, setDiagnosis] = useState(routeReport?.suspected_diagnosis || routeReport?.leading_class || result?.leading_class || '')
  const [differentials, setDifferentials] = useState(routeReport?.differential_diagnoses?.join(', ') || '')
  const [triage, setTriage] = useState<'Routine' | 'Priority' | 'Urgent'>(initialDetails?.triage || 'Routine')
  const [nextAction, setNextAction] = useState<NextAction>(routeReport?.next_action || 'routine_follow_up')
  const [followUpPlan, setFollowUpPlan] = useState(initialDetails?.followUpPlan || '')
  const [safetyNetAdvice, setSafetyNetAdvice] = useState(initialDetails?.safetyNetAdvice || DEFAULT_SAFETY_ADVICE)

  const [aiEvidenceReview, setAiEvidenceReview] = useState(initialDetails?.aiEvidenceReview || '')
  const [reviewedBy, setReviewedBy] = useState(initialDetails?.reviewedBy || '')
  const [reviewStatus, setReviewStatus] = useState<'Pending' | 'Signed'>(initialDetails?.reviewStatus || 'Pending')

  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const controller = useRef<AbortController | null>(null)

  useEffect(() => {
    if (!isEditMode || routeReport || !reportId) return
    const abort = new AbortController()
    setLoadingEdit(true)
    getAssessments(abort.signal)
      .then(rows => {
        const found = rows.find(item => item.id === reportId)
        if (!found) {
          setError('Report not found.')
          return
        }
        setEditingReport(found)
        const details = parseReportDetails(found.clinical_note)
        setClinicName(details?.clinicName || 'DermaScope Clinical Unit')
        setClinicAddress(details?.clinicAddress || '')
        setClinicContact(details?.clinicContact || '')
        setDuration(details?.duration || '')
        setReportedChanges(details?.reportedChanges || '')
        setSymptoms(details?.symptoms || '')
        setRelevantHistory(details?.relevantHistory || '')
        setAbcdeFlags(details?.abcdeFlags ?? [])
        setKeyFindings(details?.keyFindings || '')
        setObservations(details?.observations || (!details && found.clinical_note ? found.clinical_note : ''))
        setMeasurements(details?.measurements || 'Not measured')
        setAssociatedObservations(details?.associatedObservations || 'Not assessed')
        setDecision(found.decision)
        setConfidence(found.confidence)
        setDiagnosis(found.suspected_diagnosis || found.leading_class)
        setDifferentials(found.differential_diagnoses.join(', '))
        setTriage(details?.triage || 'Routine')
        setNextAction(found.next_action)
        setFollowUpPlan(details?.followUpPlan || '')
        setSafetyNetAdvice(details?.safetyNetAdvice || DEFAULT_SAFETY_ADVICE)
        setAiEvidenceReview(details?.aiEvidenceReview || '')
        setReviewedBy(details?.reviewedBy || '')
        setReviewStatus(details?.reviewStatus || 'Pending')
      })
      .catch(failure => {
        if (failure?.name !== 'AbortError') setError(failure instanceof Error ? failure.message : 'Report could not be loaded.')
      })
      .finally(() => setLoadingEdit(false))
    return () => abort.abort()
  }, [isEditMode, reportId, routeReport])

  function toggleFlag(flag: string) {
    setAbcdeFlags(previous =>
      previous.includes(flag) ? previous.filter(item => item !== flag) : [...previous, flag]
    )
  }

  if (loadingEdit) {
    return (
      <div className="reports-page">
        <div className="reviews-state"><LoaderCircle className="spin" size={24} />Loading report…</div>
      </div>
    )
  }

  if (!isEditMode && !result) {
    return (
      <div className="reports-page">
        <div className="clinical-page-heading">
          <div>
            <div className="eyebrow">Skin lesion examination report</div>
            <h1>Make Report</h1>
            <p>Run a lesion classification on the dashboard first to create a report.</p>
          </div>
          <Link to="/dashboard" className="button button--secondary"><ArrowLeft size={16} />Back to dashboard</Link>
        </div>
        <div className="reviews-state">
          <FileText size={30} />
          <strong>No active analysis</strong>
          <p>Go to the dashboard, upload a lesion image, and run classification before creating a report.</p>
          <Link to="/dashboard" className="button button--primary">Go to dashboard</Link>
        </div>
      </div>
    )
  }

  if (isEditMode && !editingReport) {
    return (
      <div className="reports-page">
        <div className="clinical-page-heading">
          <div>
            <div className="eyebrow">Skin lesion examination report</div>
            <h1>Edit Report</h1>
          </div>
          <Link to="/reports" className="button button--secondary"><ArrowLeft size={16} />Back to reports</Link>
        </div>
        <div className="reviews-state reviews-state--error">
          <AlertCircle size={24} />
          <strong>Report unavailable</strong>
          <p>{error || 'The requested report could not be found.'}</p>
        </div>
      </div>
    )
  }

  const activePatientName = isEditMode ? (editingReport!.patient_name || 'Not recorded') : (patientName.trim() || 'Not recorded')
  const activePatientId = isEditMode ? (editingReport!.patient_id || 'N/A') : (patientId.trim() || 'N/A')
  const activeAge = isEditMode ? editingReport!.patient_metadata.age : (age || result!.metadata.age)
  const activeSex = isEditMode ? editingReport!.patient_metadata.sex : (sex || result!.metadata.sex)
  const activeSite = isEditMode ? editingReport!.patient_metadata.site : (site || result!.metadata.site)
  const activeImage = isEditMode ? editingReport!.image_snapshot : reportImageSnapshot
  const activeLeadingClass = isEditMode ? editingReport!.leading_class : result!.leading_class
  const activeAnalysisId = isEditMode ? editingReport!.analysis_id : result!.analysis_id
  const activeModelVersion = isEditMode ? editingReport!.model_version : result!.model_version
  const activeScores = isEditMode ? editingReport!.model_scores : result!.scores
  const leadingScore = ((activeScores.find(item => item.label === activeLeadingClass)?.score ?? 0) * 100).toFixed(1)

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!decision || saving) return
    const active = new AbortController()
    controller.current?.abort()
    controller.current = active
    setSaving(true)
    setError('')

    let xaiMethod = initialDetails?.xaiMethod
    let xaiTargetClass = initialDetails?.xaiTargetClass
    try {
      const storedXai = localStorage.getItem(`xai_evidence_${activeAnalysisId}`)
      if (storedXai) {
        const parsedXai = JSON.parse(storedXai)
        xaiMethod = parsedXai.method
        xaiTargetClass = parsedXai.targetClass
      }
    } catch { /* Ignore storage errors */ }

    const packedNote = serializeReportDetails({
      clinicName,
      clinicAddress,
      clinicContact,
      duration,
      reportedChanges,
      symptoms,
      relevantHistory,
      abcdeFlags,
      keyFindings,
      observations,
      measurements,
      associatedObservations,
      triage,
      followUpPlan,
      safetyNetAdvice,
      aiEvidenceReview,
      reviewedBy,
      reviewStatus,
      xaiMethod,
      xaiTargetClass,
    })

    const parsedDifferentials = differentials.split(',').map(value => value.trim()).filter(Boolean).slice(0, 5)

    try {
      if (isEditMode && editingReport) {
        await updateAssessment(editingReport.id, {
          decision,
          confidence,
          suspectedDiagnosis: diagnosis.trim() || activeLeadingClass,
          differentialDiagnoses: parsedDifferentials,
          clinicalNote: packedNote,
          nextAction,
        }, active.signal)
      } else if (result) {
        await saveAssessment(result, {
          patientId: patientId.trim(),
          patientName: patientName.trim(),
          imageSnapshot: reportImageSnapshot,
          decision,
          confidence,
          suspectedDiagnosis: diagnosis.trim() || result.leading_class,
          differentialDiagnoses: parsedDifferentials,
          clinicalNote: packedNote,
          nextAction,
        }, active.signal)
      }
      navigate('/reports')
    } catch (failure) {
      if (!active.signal.aborted) {
        setSaving(false)
        setError(failure instanceof Error ? failure.message : 'Report could not be saved.')
      }
    }
  }

  return (
    <div className="reports-page">
      <div className="clinical-page-heading">
        <div>
          <div className="eyebrow">Skin lesion / dermoscopy examination report</div>
          <h1>{isEditMode ? 'Edit Report' : 'Make Report'}</h1>
          <p>{isEditMode ? 'Update the clinical findings and save changes.' : 'Select abnormal clinical features, document impression & plan, and save to Reports.'}</p>
        </div>
        <Link to={isEditMode ? '/reports' : '/dashboard'} className="button button--secondary">
          <ArrowLeft size={16} />{isEditMode ? 'Back to reports' : 'Back to dashboard'}
        </Link>
      </div>

      <form onSubmit={submit} className="assessment-form" style={{ display: 'grid', gap: '18px' }}>
        <section className="doctor-assessment" style={{ padding: '20px' }}>
          <h2 style={{ marginTop: 0, fontSize: '15px' }}>1. Hospital / Clinic Header</h2>
          <div className="assessment-fields assessment-fields--two">
            <label>
              Hospital / Clinic name
              <input value={clinicName} maxLength={100} onChange={event => setClinicName(event.target.value)} placeholder="Hospital / Clinic name" />
            </label>
            <label>
              Telephone / Email
              <input value={clinicContact} maxLength={100} onChange={event => setClinicContact(event.target.value)} placeholder="Phone or email" />
            </label>
          </div>
          <label>
            Clinic address
            <input value={clinicAddress} maxLength={140} onChange={event => setClinicAddress(event.target.value)} placeholder="Dermatology & Diagnostic Assessment Unit address" />
          </label>
        </section>

        <section className="doctor-assessment" style={{ padding: '20px' }}>
          <h2 style={{ marginTop: 0, fontSize: '15px' }}>2. Patient &amp; Examination Information</h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(120px, 1fr))', gap: '10px', padding: '10px', background: '#F5F8F9', borderRadius: '6px' }}>
            <div><small>Patient name</small><div><strong>{activePatientName}</strong></div></div>
            <div><small>Patient ID</small><div><strong>{activePatientId}</strong></div></div>
            <div><small>Age</small><div><strong>{activeAge}</strong></div></div>
            <div><small>Gender</small><div><strong>{activeSex}</strong></div></div>
          </div>
        </section>

        <section className="doctor-assessment" style={{ padding: '20px' }}>
          <h2 style={{ marginTop: 0, fontSize: '15px' }}>3. Clinical Image &amp; Lesion History</h2>
          <div style={{ display: 'flex', gap: '18px', flexWrap: 'wrap', alignItems: 'flex-start' }}>
            {activeImage && (
              <img
                src={activeImage}
                alt="Captured lesion"
                style={{ width: '160px', height: '160px', objectFit: 'cover', borderRadius: '8px', border: '1px solid var(--border, #d8e2e6)' }}
              />
            )}
            <div style={{ flex: 1, minWidth: '240px', display: 'grid', gap: '10px' }}>
              <div style={{ padding: '8px 10px', background: '#F5F8F9', borderRadius: '6px', fontSize: '13.5px' }}>
                <strong style={{ color: '#526476' }}>Location:</strong> {activeSite}
              </div>
              <div className="assessment-fields assessment-fields--two">
                <label>
                  Duration
                  <input value={duration} maxLength={90} onChange={event => setDuration(event.target.value)} placeholder="When first noticed (e.g., 6 months)" />
                </label>
                <label>
                  Reported changes
                  <input value={reportedChanges} maxLength={110} onChange={event => setReportedChanges(event.target.value)} placeholder="Size / colour / shape / none" />
                </label>
              </div>
              <div className="assessment-fields assessment-fields--two">
                <label>
                  Symptoms
                  <input value={symptoms} maxLength={110} onChange={event => setSymptoms(event.target.value)} placeholder="Itching / bleeding / pain / asymptomatic" />
                </label>
                <label>
                  Relevant personal / family history
                  <input value={relevantHistory} maxLength={140} onChange={event => setRelevantHistory(event.target.value)} placeholder="Prior skin cancer, family melanoma, sunburn" />
                </label>
              </div>
            </div>
          </div>
        </section>

        <section className="doctor-assessment" style={{ padding: '20px' }}>
          <h2 style={{ marginTop: 0, fontSize: '15px' }}>4. Findings, Impression &amp; Management</h2>
          <div style={{ marginBottom: '12px' }}>
            <div style={{ fontSize: '13px', fontWeight: 600, marginBottom: '8px' }}>
              ABCDE &amp; Dermoscopic Abnormalities (click to flag key / unusual features)
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
              {ABCDE_AND_DERMOSCOPY_FLAGS.map(flag => {
                const selected = abcdeFlags.includes(flag)
                return (
                  <button
                    key={flag}
                    type="button"
                    aria-pressed={selected}
                    onClick={() => toggleFlag(flag)}
                    style={{
                      padding: '6px 11px',
                      borderRadius: '6px',
                      fontSize: '12.5px',
                      fontWeight: selected ? 600 : 500,
                      border: selected ? '1px solid #146C70' : '1px solid #D8E1E5',
                      background: selected ? '#E6F4F3' : '#F5F8F9',
                      color: selected ? '#146C70' : '#526476',
                    }}
                  >
                    {flag}
                  </button>
                )
              })}
            </div>
          </div>
          <label>
            Additional key / unusual findings summary
            <input
              value={keyFindings}
              maxLength={200}
              onChange={event => setKeyFindings(event.target.value)}
              placeholder="e.g., Enlarged lesion (8 × 6 mm), eccentric hyperpigmentation, peripheral globules"
            />
          </label>
          <label>
            Clinical / dermoscopic observations
            <textarea value={observations} maxLength={350} rows={3} onChange={event => setObservations(event.target.value)} placeholder="Lesion morphology, pigment distribution, border regularity, vascular structures, and surrounding skin." />
          </label>
          <div className="assessment-fields assessment-fields--two">
            <label>
              Measurements (if calibrated)
              <input value={measurements} maxLength={80} onChange={event => setMeasurements(event.target.value)} placeholder='e.g., 8 × 6 mm or "Not measured"' />
            </label>
            <label>
              Associated observations / lymph nodes
              <input value={associatedObservations} maxLength={120} onChange={event => setAssociatedObservations(event.target.value)} placeholder='e.g., No palpable lymphadenopathy or "Not assessed"' />
            </label>
          </div>
          <div className="assessment-fields assessment-fields--two">
            <label>
              Clinical impression / provisional diagnosis
              <input value={diagnosis} maxLength={180} onChange={event => setDiagnosis(event.target.value)} placeholder="Primary clinical impression" />
            </label>
            <label>
              Differential diagnoses
              <input value={differentials} maxLength={160} onChange={event => setDifferentials(event.target.value)} placeholder="Up to five, separated by commas" />
            </label>
          </div>
          <div className="assessment-fields assessment-fields--two">
            <label>
              Risk / Triage category
              <select value={triage} onChange={event => setTriage(event.target.value as 'Routine' | 'Priority' | 'Urgent')}>
                <option value="Routine">Routine</option>
                <option value="Priority">Priority</option>
                <option value="Urgent">Urgent (High suspicion)</option>
              </select>
            </label>
            <label>
              Recommended management plan
              <select value={nextAction} onChange={event => setNextAction(event.target.value as NextAction)}>
                <option value="routine_follow_up">Routine follow-up</option>
                <option value="dermatology_referral">Dermatology referral</option>
                <option value="biopsy_consideration">Consider biopsy</option>
                <option value="additional_assessment">Additional assessment</option>
                <option value="other">Other</option>
              </select>
            </label>
          </div>
          <div className="assessment-fields assessment-fields--two">
            <label>
              Follow-up timeline
              <input value={followUpPlan} maxLength={120} onChange={event => setFollowUpPlan(event.target.value)} placeholder="e.g., Digital dermoscopy follow-up in 3 months / Excision within 14 days" />
            </label>
            <label>
              Patient advice / safety-netting
              <input value={safetyNetAdvice} maxLength={180} onChange={event => setSafetyNetAdvice(event.target.value)} placeholder="Safety instructions for patient" />
            </label>
          </div>
        </section>

        <section className="doctor-assessment" style={{ padding: '20px' }}>
          <h2 style={{ marginTop: 0, fontSize: '15px' }}>5. Supporting AI Evidence &amp; Clinician Review</h2>
          <div style={{ padding: '10px 12px', background: '#F2F7F8', borderRadius: '6px', marginBottom: '12px', color: '#203047' }}>
            <strong style={{ color: '#146C70' }}>Highest AI Prediction:</strong> {activeLeadingClass} ({leadingScore}%) · Analysis ID: <code>{activeAnalysisId.slice(0, 8)}</code> · Model: {activeModelVersion}
          </div>
          <fieldset>
            <legend>Clinician concordance with leading AI prediction</legend>
            <div className="assessment-decisions">
              {decisions.map(item => (
                <button
                  key={item.value}
                  type="button"
                  aria-pressed={decision === item.value}
                  className={decision === item.value ? 'selected' : ''}
                  onClick={() => setDecision(item.value)}
                >
                  {item.label}
                </button>
              ))}
            </div>
          </fieldset>
          <div className="assessment-fields assessment-fields--two">
            <label>
              Clinical confidence
              <select value={confidence} onChange={event => setConfidence(Number(event.target.value))}>
                <option value={1}>1 — Very uncertain</option>
                <option value={2}>2 — Uncertain</option>
                <option value={3}>3 — Moderate</option>
                <option value={4}>4 — Confident</option>
                <option value={5}>5 — Very confident</option>
              </select>
            </label>
            <label>
              AI evidence review note
              <input value={aiEvidenceReview} maxLength={180} onChange={event => setAiEvidenceReview(event.target.value)} placeholder="Brief clinician review of AI output quality" />
            </label>
          </div>
          <div className="assessment-fields assessment-fields--two">
            <label>
              Reviewed by (Clinician name / designation)
              <input value={reviewedBy} maxLength={100} onChange={event => setReviewedBy(event.target.value)} placeholder="Dr. Name, Designation / Reg. No." />
            </label>
            <label>
              Clinical review status
              <select value={reviewStatus} onChange={event => setReviewStatus(event.target.value as 'Pending' | 'Signed')}>
                <option value="Pending">Pending (Draft)</option>
                <option value="Signed">Signed</option>
              </select>
            </label>
          </div>

          {error && <p className="assessment-error" role="alert"><AlertCircle size={16} />{error}</p>}

          <div className="assessment-actions">
            <p>Only the latest 5 saved reports are retained in the database.</p>
            <button type="submit" className="button button--primary" disabled={!decision || saving}>
              <Save size={16} />{saving ? 'Saving…' : isEditMode ? 'Update Report' : 'Save Report'}
            </button>
          </div>
        </section>
      </form>
    </div>
  )
}
