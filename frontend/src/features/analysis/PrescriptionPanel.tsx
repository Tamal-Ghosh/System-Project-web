import { AlertCircle, CheckCircle2, ChevronDown, CirclePlus, LoaderCircle, Pencil, Pill, Printer, Save, Search, Trash2, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import type { DoctorAssessment } from '../../services/assessments'
import type { ClassificationResult } from '../../services/classification'
import { savePrescription, suggestMedicines } from '../../services/prescriptions'
import type { AllergyStatus, MedicationEntry, MedicineSuggestion, Prescription } from '../../services/prescriptions'
import { openPrintableReport, prescriptionHtml } from '../../services/reports'

const scheduleOptions = ['0', '¼', '½', '1', '1½', '2']
const emptyMedication = (): MedicationEntry => ({ name: '', rxcui: null, strength: '', formulation: '', route: '', morning: '0', noon: '0', night: '0', duration: '', instructions: '' })

export function PrescriptionPanel({ result, patientId, assessment }: { result: ClassificationResult; patientName: string; patientId: string; assessment: DoctorAssessment | null }) {
  const [symptoms, setSymptoms] = useState('')
  const [allergyStatus, setAllergyStatus] = useState<AllergyStatus>('unknown')
  const [allergyDetails, setAllergyDetails] = useState('')
  const [medications, setMedications] = useState<MedicationEntry[]>([])
  const [medicineDraft, setMedicineDraft] = useState<MedicationEntry>(emptyMedication())
  const [editingIndex, setEditingIndex] = useState<number | null>(null)
  const [suggestions, setSuggestions] = useState<MedicineSuggestion[]>([])
  const [suggestionState, setSuggestionState] = useState<'idle' | 'loading' | 'error'>('idle')
  const [followUp, setFollowUp] = useState('')
  const [saved, setSaved] = useState<Prescription | null>(null)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const controller = useRef<AbortController | null>(null)

  useEffect(() => {
    const term = medicineDraft.name.trim()
    if (term.length < 3 || medicineDraft.rxcui) { setSuggestions([]); setSuggestionState('idle'); return }
    const active = new AbortController()
    const timer = window.setTimeout(() => {
      setSuggestionState('loading')
      suggestMedicines(term, active.signal).then(rows => { setSuggestions(rows); setSuggestionState('idle') }).catch(failure => {
        if (failure?.name !== 'AbortError') { setSuggestions([]); setSuggestionState('error') }
      })
    }, 350)
    return () => { window.clearTimeout(timer); active.abort() }
  }, [medicineDraft.name, medicineDraft.rxcui])

  function updateDraft(field: keyof MedicationEntry, value: string | null) {
    setMedicineDraft(current => ({ ...current, [field]: value }))
  }

  function commitMedicine() {
    const hasDose = [medicineDraft.morning, medicineDraft.noon, medicineDraft.night].some(value => value !== '0')
    if (!medicineDraft.name.trim() || !hasDose || !medicineDraft.duration.trim()) {
      setError('Complete medicine name, at least one dose time, and duration before adding it.'); return
    }
    if (editingIndex === null) setMedications(current => [...current, medicineDraft])
    else setMedications(current => current.map((item, index) => index === editingIndex ? medicineDraft : item))
    setMedicineDraft(emptyMedication()); setEditingIndex(null); setSuggestions([]); setError('')
  }

  function editMedicine(index: number) {
    setMedicineDraft({ ...medications[index] }); setEditingIndex(index); setSuggestions([]); setError('')
  }

  function removeMedicine(index: number) {
    setMedications(current => current.filter((_, itemIndex) => itemIndex !== index))
    if (editingIndex === index) { setMedicineDraft(emptyMedication()); setEditingIndex(null) }
    else if (editingIndex !== null && editingIndex > index) setEditingIndex(editingIndex - 1)
  }

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (saving) return
    if (medications.length === 0) { setError('Add at least one medicine before saving the prescription.'); return }
    if (allergyStatus === 'present' && !allergyDetails.trim()) { setError('Enter the known allergy details.'); return }
    const active = new AbortController(); controller.current?.abort(); controller.current = active
    setSaving(true); setError('')
    try {
      const prescription = await savePrescription({ patientId, result, assessmentId: assessment?.id }, {
        symptoms: symptoms.split(',').map(value => value.trim()).filter(Boolean).slice(0, 12),
        allergyStatus, allergyDetails: allergyDetails.trim(), medications, followUp: followUp.trim(),
      }, active.signal)
      setSaved(prescription)
    } catch (failure) {
      if (!active.signal.aborted) setError(failure instanceof Error ? failure.message : 'Prescription could not be saved.')
    } finally { if (controller.current === active) setSaving(false) }
  }

  return <details className="clinical-disclosure prescription-section">
    <summary><span className="disclosure-icon"><Pill size={21} /></span><span><strong>Prescription</strong><small>Doctor-authored medicines and instructions</small></span><ChevronDown className="disclosure-chevron" size={19} /></summary>
    {saved ? <div className="prescription-saved"><CheckCircle2 size={24} /><div><strong>Prescription saved</strong><p>It is linked to patient {saved.patient_id} and analysis {saved.analysis_id.slice(0, 8)}.</p><button type="button" className="button button--secondary" onClick={() => openPrintableReport(prescriptionHtml(saved, assessment || undefined))}><Printer size={16} />Print prescription</button></div></div> : <form className="prescription-form" onSubmit={submit}>
      <div className="prescription-safety-note">RxNorm supplies name suggestions only. The treating doctor independently selects the medicine and dosing schedule.</div>
      <label>Symptoms / presenting concerns<input value={symptoms} maxLength={1000} onChange={event => setSymptoms(event.target.value)} placeholder="Itching, bleeding, recent change — separated by commas" /></label>
      <div className="assessment-fields assessment-fields--two"><label>Allergy status<select value={allergyStatus} onChange={event => setAllergyStatus(event.target.value as AllergyStatus)}><option value="unknown">Not confirmed</option><option value="none_known">No known allergies</option><option value="present">Known allergy</option></select></label><label>Allergy details<input disabled={allergyStatus !== 'present'} value={allergyDetails} maxLength={500} onChange={event => setAllergyDetails(event.target.value)} placeholder={allergyStatus === 'present' ? 'Medicine or substance and reaction' : 'Enable by selecting known allergy'} /></label></div>
      <div className="medication-list"><div className="medication-list__heading"><div><strong>Medicines</strong><p>Search, set morning–noon–night dose, then add to the list.</p></div><span>{medications.length}/10 added</span></div>
        <fieldset className="medicine-editor"><legend>{editingIndex === null ? 'Add medicine' : `Edit medicine ${editingIndex + 1}`}</legend>
          <div className="medicine-primary-grid"><label className="medicine-search-label">Medicine name<div className="medicine-search"><Search size={16} /><input value={medicineDraft.name} maxLength={160} autoComplete="off" onChange={event => { updateDraft('name', event.target.value); updateDraft('rxcui', null) }} placeholder="Type at least 3 letters" />{suggestionState === 'loading' && <LoaderCircle className="spin" size={16} />}</div>{suggestions.length > 0 && <div className="medicine-suggestions" role="listbox">{suggestions.map(item => <button key={`${item.rxcui}-${item.name}`} type="button" role="option" onClick={() => { setMedicineDraft(current => ({ ...current, name: item.name, rxcui: item.rxcui })); setSuggestions([]) }}><strong>{item.name}</strong><small>RxNorm · {item.rxcui}</small></button>)}</div>}{suggestionState === 'error' && <small className="suggestion-note">Suggestions unavailable — manual entry is still allowed.</small>}{medicineDraft.rxcui && <small className="suggestion-note suggestion-note--selected">RxNorm verified name · {medicineDraft.rxcui}</small>}</label><label>Strength<input value={medicineDraft.strength} maxLength={80} placeholder="e.g. 10 mg" onChange={event => updateDraft('strength', event.target.value)} /></label><label>Form<select value={medicineDraft.formulation} onChange={event => updateDraft('formulation', event.target.value)}><option value="">Select</option><option>Tablet</option><option>Capsule</option><option>Cream</option><option>Ointment</option><option>Lotion</option><option>Gel</option><option>Solution</option><option>Other</option></select></label><label>Route<select value={medicineDraft.route} onChange={event => updateDraft('route', event.target.value)}><option value="">Select</option><option>Oral</option><option>Topical</option><option>Intramuscular</option><option>Intravenous</option><option>Subcutaneous</option><option>Other</option></select></label></div>
          <div className="dose-schedule"><div><strong>When to take</strong><small>Morning + Noon + Night</small></div>{(['morning', 'noon', 'night'] as const).map((period, index) => <label key={period}><span>{['Morning', 'Noon', 'Night'][index]}</span><select aria-label={`${period} dose`} value={medicineDraft[period]} onChange={event => updateDraft(period, event.target.value)}>{scheduleOptions.map(value => <option key={value} value={value}>{value}</option>)}</select></label>)}<div className="dose-pattern"><span>Pattern</span><strong>{medicineDraft.morning} + {medicineDraft.noon} + {medicineDraft.night}</strong></div></div>
          <div className="medicine-secondary-grid"><label>Duration<input value={medicineDraft.duration} maxLength={120} placeholder="e.g. 7 days / 2 weeks" onChange={event => updateDraft('duration', event.target.value)} /></label><label>Additional instructions<input value={medicineDraft.instructions} maxLength={500} placeholder="After food, apply to affected area, precautions…" onChange={event => updateDraft('instructions', event.target.value)} /></label></div>
          <div className="medicine-editor__actions">{editingIndex !== null && <button type="button" className="button button--secondary" onClick={() => { setMedicineDraft(emptyMedication()); setEditingIndex(null); setError('') }}><X size={15} />Cancel edit</button>}<button type="button" className="button button--secondary" disabled={editingIndex === null && medications.length >= 10} onClick={commitMedicine}><CirclePlus size={16} />{editingIndex === null ? 'Add medicine' : 'Update medicine'}</button></div>
        </fieldset>
        {medications.length > 0 && <div className="added-medicines" aria-label="Added medicines">{medications.map((medicine, index) => <div className={`medicine-summary ${editingIndex === index ? 'is-editing' : ''}`} key={`${medicine.name}-${index}`}><span className="medicine-summary__number">{index + 1}</span><div><strong>{medicine.name}{medicine.strength ? ` · ${medicine.strength}` : ''}{medicine.formulation ? ` · ${medicine.formulation}` : ''}</strong><span>{medicine.morning} + {medicine.noon} + {medicine.night} · {medicine.duration}{medicine.route ? ` · ${medicine.route}` : ''}</span>{medicine.instructions && <small>{medicine.instructions}</small>}</div><div className="medicine-summary__actions"><button type="button" aria-label={`Edit ${medicine.name}`} onClick={() => editMedicine(index)}><Pencil size={15} />Edit</button><button type="button" aria-label={`Delete ${medicine.name}`} onClick={() => removeMedicine(index)}><Trash2 size={15} />Delete</button></div></div>)}</div>}
      </div>
      <label>General follow-up / precautions<textarea value={followUp} maxLength={500} rows={3} onChange={event => setFollowUp(event.target.value)} placeholder="Follow-up timing, general precautions or monitoring instructions" /></label>
      {error && <p className="assessment-error" role="alert"><AlertCircle size={16} />{error}</p>}
      <div className="assessment-actions"><p>Prescriber identity and registration will come from the authenticated doctor profile.</p><button type="submit" className="button button--primary" disabled={saving}><Save size={16} />{saving ? 'Saving…' : 'Save prescription'}</button></div>
    </form>}
  </details>
}
