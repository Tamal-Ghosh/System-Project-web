import type { DoctorAssessment, NextAction } from './assessments'
import type { Prescription } from './prescriptions'

const actionLabels: Record<NextAction, string> = {
  routine_follow_up: 'Routine follow-up',
  dermatology_referral: 'Dermatology referral',
  biopsy_consideration: 'Consider biopsy',
  additional_assessment: 'Additional clinical assessment',
  other: 'Other clinician-directed action',
}

const decisionLabels = { agree: 'Agrees with model output', disagree: 'Disagrees with model output', unsure: 'Uncertain' }

function escapeHtml(value: unknown) {
  return String(value ?? '').replace(/[&<>'"]/g, character => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' })[character]!)
}

function documentShell(title: string, subtitle: string, body: string) {
  return `<!doctype html><html><head><meta charset="utf-8"><title>${escapeHtml(title)}</title><style>
  @page{size:A4;margin:16mm}*{box-sizing:border-box}body{font-family:Arial,sans-serif;color:#12263c;margin:0;font-size:12px;line-height:1.55}header{border-bottom:3px solid #008579;padding-bottom:14px;margin-bottom:20px}h1{font-size:24px;margin:0 0 4px}h2{font-size:16px;margin:22px 0 9px;border-bottom:1px solid #dbe5ed;padding-bottom:6px}p{margin:5px 0}.muted{color:#60758c}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:9px}.fact{background:#f5f8fa;border:1px solid #dce5ed;border-radius:6px;padding:9px}.fact span{display:block;color:#60758c;font-size:10px;text-transform:uppercase;letter-spacing:.05em}.fact strong{display:block;margin-top:3px}.scores{width:100%;border-collapse:collapse}.scores th,.scores td{text-align:left;padding:6px 8px;border-bottom:1px solid #e2e8ee}.scores th:last-child,.scores td:last-child{text-align:right}.notice{margin-top:22px;padding:12px;border-left:4px solid #d59a20;background:#fff8e7}.signature{margin-top:35px;display:grid;grid-template-columns:1fr 1fr;gap:45px}.signature div{border-top:1px solid #60758c;padding-top:6px}.footer{margin-top:26px;padding-top:10px;border-top:1px solid #dbe5ed;color:#71849a;font-size:10px}@media print{button{display:none}}
  </style></head><body><header><strong>DermScope Clinical Workspace</strong><h1>${escapeHtml(title)}</h1><p class="muted">${escapeHtml(subtitle)}</p></header>${body}</body></html>`
}

function commonFacts(assessment: DoctorAssessment) {
  const date = new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(assessment.created_at))
  return `<div class="grid"><div class="fact"><span>Patient ID</span><strong>${escapeHtml(assessment.patient_id || 'Legacy record')}</strong></div><div class="fact"><span>Analysis ID</span><strong>${escapeHtml(assessment.analysis_id)}</strong></div><div class="fact"><span>Assessment date</span><strong>${escapeHtml(date)}</strong></div><div class="fact"><span>Model version</span><strong>${escapeHtml(assessment.model_version)}</strong></div><div class="fact"><span>Age</span><strong>${escapeHtml(assessment.patient_metadata.age)} years</strong></div><div class="fact"><span>Gender / location</span><strong>${escapeHtml(assessment.patient_metadata.sex)} · ${escapeHtml(assessment.patient_metadata.site)}</strong></div></div>`
}

export function doctorReportHtml(assessment: DoctorAssessment) {
  const scores = [...assessment.model_scores].sort((a, b) => b.score - a.score).map(row => `<tr><td>${escapeHtml(row.label)}</td><td>${(row.score * 100).toFixed(1)}%</td></tr>`).join('')
  const differentials = assessment.differential_diagnoses.length ? assessment.differential_diagnoses.map(escapeHtml).join(', ') : 'None recorded'
  return documentShell('Doctor Clinical Report', 'Technical decision-support record for the treating clinician', `${commonFacts(assessment)}<h2>Model output</h2><div class="grid"><div class="fact"><span>Leading classification</span><strong>${escapeHtml(assessment.leading_class)}</strong></div><div class="fact"><span>Doctor decision</span><strong>${escapeHtml(decisionLabels[assessment.decision])}</strong></div><div class="fact"><span>Clinical confidence</span><strong>${assessment.confidence}/5</strong></div></div><table class="scores"><thead><tr><th>Classification</th><th>Model score</th></tr></thead><tbody>${scores}</tbody></table><h2>Independent clinical assessment</h2><p><strong>Clinical impression:</strong> ${escapeHtml(assessment.suspected_diagnosis || 'Not recorded')}</p><p><strong>Differential diagnoses:</strong> ${differentials}</p><p><strong>Next action:</strong> ${escapeHtml(actionLabels[assessment.next_action])}</p><p><strong>Clinical note:</strong> ${escapeHtml(assessment.clinical_note || 'No additional note')}</p><div class="notice"><strong>Clinical limitation</strong><br>AI-generated decision support is not a confirmed diagnosis and does not replace clinical examination or histopathology. Model scores must be interpreted with the image quality, patient history, and clinician findings.</div><div class="signature"><div>Clinician signature</div><div>Date</div></div><div class="footer">Generated from an immutable assessment snapshot. Reviewer identity will be populated from the authenticated doctor account when authentication is enabled.</div>`)
}

export function patientSummaryHtml(assessment: DoctorAssessment) {
  return documentShell('Patient Summary', 'Doctor-approved explanation of the skin-lesion assessment', `${commonFacts(assessment)}<h2>What was assessed</h2><p>A dermoscopic image of a lesion at <strong>${escapeHtml(assessment.patient_metadata.site)}</strong> was reviewed using a clinical decision-support model and an independent doctor assessment.</p><h2>Doctor's clinical impression</h2><p><strong>${escapeHtml(assessment.suspected_diagnosis || 'No final clinical impression was recorded')}</strong></p>${assessment.differential_diagnoses.length ? `<p class="muted">Other possibilities considered: ${assessment.differential_diagnoses.map(escapeHtml).join(', ')}</p>` : ''}<h2>Recommended next step</h2><p>${escapeHtml(actionLabels[assessment.next_action])}</p>${assessment.clinical_note ? `<h2>Advice from the clinical review</h2><p>${escapeHtml(assessment.clinical_note)}</p>` : ''}<div class="notice"><strong>Important</strong><br>This summary is not a pathology result or a prescription. Seek medical attention sooner if the lesion changes rapidly, bleeds, ulcerates, becomes painful, or you have another concern.</div><div class="signature"><div>Approving clinician</div><div>Date</div></div><div class="footer">This patient-friendly summary intentionally omits technical model probabilities and uncertainty terminology.</div>`)
}

function prescriptionFacts(prescription: Prescription) {
  const date = new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(prescription.created_at))
  return `<div class="grid"><div class="fact"><span>Patient ID</span><strong>${escapeHtml(prescription.patient_id)}</strong></div><div class="fact"><span>Analysis ID</span><strong>${escapeHtml(prescription.analysis_id)}</strong></div><div class="fact"><span>Prescription date</span><strong>${escapeHtml(date)}</strong></div><div class="fact"><span>Model version</span><strong>${escapeHtml(prescription.model_version)}</strong></div><div class="fact"><span>Age</span><strong>${escapeHtml(prescription.patient_metadata.age)} years</strong></div><div class="fact"><span>Gender / location</span><strong>${escapeHtml(prescription.patient_metadata.sex)} · ${escapeHtml(prescription.patient_metadata.site)}</strong></div></div>`
}
