import type { AssessmentDecision, DoctorAssessment, NextAction } from './assessments'
import type { Prescription } from './prescriptions'

const actionLabels: Record<NextAction, string> = {
  routine_follow_up: 'Routine follow-up',
  dermatology_referral: 'Dermatology referral',
  biopsy_consideration: 'Consider biopsy',
  additional_assessment: 'Additional clinical assessment',
  other: 'Other clinician-directed action',
}

const concordanceLabels: Record<AssessmentDecision, string> = {
  agree: 'Agreed with AI output',
  disagree: 'Disagreed with AI output',
  unsure: 'Uncertain / equivocal',
}

export interface ReportDetails {
  __report_v2: true
  clinicName?: string
  clinicAddress?: string
  clinicContact?: string
  referringClinician?: string
  imageType?: string
  indication?: string
  fitzpatrick?: string
  duration?: string
  reportedChanges?: string
  symptoms?: string
  relevantHistory?: string
  abcdeFlags?: string[]
  keyFindings?: string
  observations?: string
  measurements?: string
  associatedObservations?: string
  triage?: 'Routine' | 'Priority' | 'Urgent'
  followUpPlan?: string
  safetyNetAdvice?: string
  aiEvidenceReview?: string
  reviewedBy?: string
  reviewStatus?: 'Pending' | 'Signed'
  xaiMethod?: string
  xaiTargetClass?: string
  segStatus?: string
  segCorrected?: string
}

export function serializeReportDetails(details: Omit<ReportDetails, '__report_v2'>): string {
  const clean: Record<string, unknown> = { __report_v2: true }
  for (const [key, value] of Object.entries(details)) {
    if (Array.isArray(value)) {
      if (value.length > 0) clean[key] = value
    } else if (typeof value === 'string') {
      const trimmed = value.trim()
      if (trimmed) clean[key] = trimmed
    } else if (value !== undefined && value !== null) {
      clean[key] = value
    }
  }
  const encoded = JSON.stringify(clean)
  if (encoded.length <= 1980) return encoded
  // Trim longest free-text fields only if needed to respect the 2000-char database constraint
  if (typeof clean.observations === 'string') clean.observations = clean.observations.slice(0, 300)
  if (typeof clean.keyFindings === 'string') clean.keyFindings = clean.keyFindings.slice(0, 200)
  if (typeof clean.relevantHistory === 'string') clean.relevantHistory = clean.relevantHistory.slice(0, 140)
  return JSON.stringify(clean).slice(0, 1995)
}

export function parseReportDetails(clinicalNote: string | null | undefined): ReportDetails | null {
  if (!clinicalNote) return null
  try {
    const parsed = JSON.parse(clinicalNote)
    if (parsed && parsed.__report_v2 === true) return parsed as ReportDetails
  } catch {
    return null
  }
  return null
}

function readStoredEvidence(key: string): Record<string, string> | null {
  try {
    const raw = localStorage.getItem(key)
    if (!raw) return null
    return JSON.parse(raw) as Record<string, string>
  } catch {
    return null
  }
}

function escapeHtml(value: unknown) {
  return String(value ?? '').replace(/[&<>'"]/g, character => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' })[character]!)
}

export function doctorReportHtml(assessment: DoctorAssessment) {
  const details = parseReportDetails(assessment.clinical_note)
  const reportId = assessment.id.slice(0, 8).toUpperCase()
  const examDate = new Intl.DateTimeFormat('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }).format(new Date(assessment.created_at))
  const reviewStatus = details?.reviewStatus || 'Pending'
  const isSigned = reviewStatus === 'Signed'

  const clinicName = details?.clinicName?.trim() || 'DermaScope Clinical Unit'
  const clinicSubtitle = 'Dermatology & Diagnostic Assessment Unit'
  const clinicAddress = details?.clinicAddress?.trim() || 'Clinical Dermatology Department'
  const clinicContact = details?.clinicContact?.trim() || 'Tel / Email on file'

  const duration = details?.duration?.trim() || 'Unknown'
  const reportedChanges = details?.reportedChanges?.trim() || 'Unknown'
  const symptoms = details?.symptoms?.trim() || 'None reported'
  const relevantHistory = details?.relevantHistory?.trim() || 'None recorded'

  const abcdeFlags = details?.abcdeFlags ?? []
  const customKeyFindings = details?.keyFindings?.trim() || ''
  const observations = details?.observations?.trim() || (!details && assessment.clinical_note ? assessment.clinical_note : 'Not recorded')
  const measurements = details?.measurements?.trim() || 'Not measured'
  const associatedObservations = details?.associatedObservations?.trim() || 'Not assessed'

  const impression = assessment.suspected_diagnosis?.trim() || assessment.leading_class
  const differentials = assessment.differential_diagnoses.length ? assessment.differential_diagnoses.join(', ') : 'None listed'
  const triage = details?.triage || 'Routine'

  const recommendedPlan = actionLabels[assessment.next_action] || assessment.next_action
  const followUp = details?.followUpPlan?.trim() || 'As clinically indicated'
  const safetyNetAdvice = details?.safetyNetAdvice?.trim() || 'Advised to monitor for ABCDE changes (asymmetry, border, color, diameter, evolution), bleeding, or ulceration and seek prompt review.'
  const concordance = concordanceLabels[assessment.decision] || assessment.decision
  const aiEvidenceReview = details?.aiEvidenceReview?.trim() || 'Supporting model evidence reviewed alongside clinical examination.'
  const reviewedBy = details?.reviewedBy?.trim() || assessment.reviewer_name || 'Pending clinician assignment'

  const leadingScore = assessment.model_scores.find(row => row.label === assessment.leading_class)?.score ?? Math.max(...assessment.model_scores.map(row => row.score))

  const storedXai = readStoredEvidence(`xai_evidence_${assessment.analysis_id}`)
  const hasXai = Boolean(storedXai?.maskData || details?.xaiMethod)
  const xaiMethod = details?.xaiMethod || storedXai?.method || 'Integrated Gradients'
  const xaiTarget = details?.xaiTargetClass || storedXai?.targetClass || assessment.leading_class

  const storedSeg = readStoredEvidence(`seg_evidence_${assessment.analysis_id}`)
  const hasSeg = Boolean(storedSeg?.maskData || details?.segStatus)
  const segStatus = details?.segStatus || storedSeg?.status || 'Valid'
  const segCorrected = details?.segCorrected || storedSeg?.corrected || 'No'

  const imageBlock = assessment.image_snapshot
    ? `<img class="lesion-img" src="${escapeHtml(assessment.image_snapshot)}" alt="Lesion clinical image" />`
    : `<div class="img-empty">No lesion image attached</div>`

  const xaiVisualBlock = storedXai?.maskData && assessment.image_snapshot
    ? `<div class="xai-overlay-wrap"><img src="${escapeHtml(assessment.image_snapshot)}" alt="Lesion base" /><div class="xai-mask" style="mask-image:url(data:image/png;base64,${escapeHtml(storedXai.maskData)});-webkit-mask-image:url(data:image/png;base64,${escapeHtml(storedXai.maskData)})"></div></div>`
    : `<div class="img-empty">XAI attribution computed (${escapeHtml(xaiMethod)})</div>`

  const segVisualBlock = storedSeg?.maskData
    ? `<img src="data:image/png;base64,${escapeHtml(storedSeg.maskData)}" alt="Lesion segmentation overlay" />`
    : `<div class="img-empty">Segmentation mask (${escapeHtml(segStatus)})</div>`

  const keyFlagsHtml = abcdeFlags.length > 0
    ? `<div class="flag-list">${abcdeFlags.map(flag => `<span class="flag-chip">${escapeHtml(flag)}</span>`).join('')}</div>`
    : ''

  const keyFindingsSummary = customKeyFindings || (abcdeFlags.length > 0 ? 'See flagged ABCDE / dermoscopic features above.' : 'No unusual morphological features flagged.')

  const visualEvidenceSection = (hasXai || hasSeg) ? `
  <div class="sec-head"><span class="sec-title">Visual AI Evidence</span><span class="sec-sub">&nbsp;&nbsp;|&nbsp;&nbsp;include only when available</span></div>
  <table class="visual-tbl">
    ${hasXai ? `
    <tr>
      <td class="visual-img-cell">${xaiVisualBlock}<div class="cap">XAI attribution</div></td>
      <td class="visual-text-cell">
        <div class="sub-head">XAI EXPLANATION</div>
        <div class="kv-line"><strong>Method:</strong> <span>${escapeHtml(xaiMethod)}</span></div>
        <div class="kv-line"><strong>Target class:</strong> <span>${escapeHtml(xaiTarget)}</span></div>
        <div class="kv-line"><strong>Interpretation:</strong> <span>Attribution is model evidence, not a confirmed clinical finding.</span></div>
      </td>
    </tr>` : ''}
    ${hasSeg ? `
    <tr>
      <td class="visual-img-cell">${segVisualBlock}<div class="cap">Lesion segmentation</div></td>
      <td class="visual-text-cell">
        <div class="sub-head">LESION SEGMENTATION</div>
        <div class="kv-line"><strong>Mask status:</strong> <span>${escapeHtml(segStatus)}</span></div>
        <div class="kv-line"><strong>Clinician correction:</strong> <span>${escapeHtml(segCorrected)}</span></div>
        <div class="kv-line"><strong>Note:</strong> <span>Pixel mask is not a physical measurement.</span></div>
      </td>
    </tr>` : ''}
  </table>` : ''

  const footerText = isSigned
    ? 'CLINICALLY REVIEWED &nbsp;&bull;&nbsp; AI OUTPUT IS NOT A DIAGNOSIS'
    : 'DRAFT TEMPLATE &nbsp;&bull;&nbsp; NOT CLINICALLY REVIEWED &nbsp;&bull;&nbsp; AI OUTPUT IS NOT A DIAGNOSIS'

  return `<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Skin Lesion / Dermoscopy Examination Report — ${escapeHtml(reportId)}</title>
<style>
  @page { size: A4; margin: 14mm 16mm; }
  * { box-sizing: border-box; }
  body {
    font-family: 'Aptos', 'Segoe UI', Calibri, Arial, sans-serif;
    color: #203047;
    margin: 0;
    background: #fff;
    font-size: 10.5pt;
    line-height: 1.44;
  }
  .page-wrap { max-width: 790px; margin: 0 auto; padding: 6px 0; }

  .clinic-header { margin-bottom: 10px; }
  .clinic-name { font-size: 14.5pt; font-weight: 700; color: #203047; line-height: 1.25; }
  .clinic-unit { font-size: 9.5pt; color: #526476; margin-top: 2px; }
  .clinic-contact { font-size: 9pt; color: #718090; margin-top: 2px; }

  .doc-title {
    font-size: 15pt;
    font-weight: 700;
    color: #203047;
    letter-spacing: .01em;
    border-bottom: 1.6px solid #146C70;
    padding-bottom: 5px;
    margin: 0 0 7px;
  }
  .doc-meta { font-size: 9.5pt; color: #203047; margin-bottom: 12px; }
  .doc-meta strong { color: #526476; font-weight: 700; }
  .doc-meta span.sep { display: inline-block; width: 20px; }

  .sec-head {
    border-bottom: 0.75pt solid #D8E1E5;
    padding-bottom: 3px;
    margin: 13px 0 7px;
  }
  .sec-title {
    font-size: 10pt;
    font-weight: 700;
    color: #146C70;
    text-transform: uppercase;
    letter-spacing: .02em;
  }
  .sec-sub { font-size: 8.5pt; color: #718090; font-weight: 400; }

  table.shaded-grid {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0 2px;
    margin-bottom: 4px;
  }
  table.shaded-grid td {
    width: 50%;
    background: #F5F8F9;
    padding: 5px 10px;
    vertical-align: top;
    font-size: 9.5pt;
    color: #203047;
  }
  table.shaded-grid td + td { border-left: 2px solid #fff; }
  table.shaded-grid--four td { width: auto; }
  table.shaded-grid--four td:nth-child(1) { width: 34%; }
  table.shaded-grid--four td:nth-child(2) { width: 26%; }
  table.shaded-grid--four td:nth-child(3) { width: 18%; }
  table.shaded-grid--four td:nth-child(4) { width: 22%; }
  table.shaded-grid .lbl { font-size: 9pt; font-weight: 700; color: #526476; margin-right: 6px; }

  table.split-tbl { width: 100%; border-collapse: collapse; margin-bottom: 4px; break-inside: avoid; }
  table.split-tbl td { width: 50%; vertical-align: top; padding: 5px 10px 5px 0; }
  table.split-tbl td + td { padding: 5px 0 5px 14px; }
  .lesion-img { max-width: 100%; max-height: 165px; border-radius: 6px; display: block; object-fit: contain; }
  .img-empty { color: #718090; font-size: 9pt; padding: 18px 0; }
  .cap { font-size: 8.5pt; color: #718090; margin-top: 4px; }

  .kv-line { font-size: 9.5pt; margin-bottom: 5px; color: #203047; }
  .kv-line strong { color: #526476; font-weight: 700; margin-right: 4px; }

  .key-findings-box {
    background: #F2F7F8;
    padding: 7px 10px;
    margin-bottom: 7px;
    break-inside: avoid;
  }
  .flag-list { display: flex; flex-wrap: wrap; gap: 5px; margin: 4px 0; }
  .flag-chip {
    display: inline-block;
    background: #fff;
    border: 0.75pt solid #D8E1E5;
    color: #146C70;
    font-size: 8.5pt;
    font-weight: 700;
    padding: 2px 7px;
    border-radius: 3px;
  }

  .finding-line { font-size: 9.8pt; margin: 0 0 5px; color: #526476; }
  .finding-line strong { color: #203047; font-weight: 700; }

  .page-two { page-break-before: always; padding-top: 4px; }
  @media screen { .page-two { margin-top: 26px; padding-top: 18px; border-top: 1px dashed #D8E1E5; } }

  .ai-callout {
    background: #F2F7F8;
    padding: 9px 13px;
    margin: 8px 0 11px;
    break-inside: avoid;
  }
  .ai-callout-title { font-size: 10pt; font-weight: 700; color: #146C70; margin-bottom: 3px; }
  .ai-callout-body { font-size: 9.5pt; color: #203047; }

  .note-line { font-size: 9pt; color: #526476; margin: 5px 0 9px; }
  .note-line strong { color: #146C70; font-weight: 700; }

  table.visual-tbl { width: 100%; border-collapse: collapse; margin-bottom: 8px; }
  table.visual-tbl td { width: 50%; vertical-align: top; padding: 6px 10px 6px 0; }
  table.visual-tbl td.visual-text-cell { padding: 6px 0 6px 14px; }
  .visual-img-cell img { max-width: 100%; max-height: 150px; border-radius: 6px; display: block; object-fit: contain; }
  .xai-overlay-wrap { position: relative; display: inline-block; max-width: 100%; }
  .xai-mask {
    position: absolute; inset: 0;
    background: linear-gradient(90deg, #182a88, #28bdd0, #ffb72b, #e72c19);
    opacity: 0.6;
    mask-size: 100% 100%; -webkit-mask-size: 100% 100%;
    mask-repeat: no-repeat; -webkit-mask-repeat: no-repeat;
    border-radius: 6px;
  }
  .sub-head { font-size: 10pt; font-weight: 700; color: #146C70; margin-bottom: 5px; }
  .visual-text-cell .kv-line strong { color: #203047; }
  .visual-text-cell .kv-line span { color: #526476; }

  .review-summary { font-size: 9.5pt; color: #526476; margin: 8px 0 11px; }
  .review-summary strong { font-size: 10pt; color: #203047; font-weight: 700; }

  table.sig-tbl { width: 100%; border-collapse: collapse; margin-top: 6px; break-inside: avoid; }
  table.sig-tbl td { width: 50%; padding: 5px 10px 5px 0; font-size: 9.5pt; color: #526476; vertical-align: top; }
  table.sig-tbl td strong { color: #203047; font-weight: 700; }

  .footer-note { margin-top: 14px; font-size: 8.5pt; color: #526476; letter-spacing: .02em; }
</style>
</head>
<body>
<div class="page-wrap">
  <div class="clinic-header">
    <div class="clinic-name">${escapeHtml(clinicName)}</div>
    <div class="clinic-unit">${escapeHtml(clinicSubtitle)}</div>
    <div class="clinic-contact">${escapeHtml(clinicAddress)} &nbsp;&nbsp;|&nbsp;&nbsp; ${escapeHtml(clinicContact)}</div>
  </div>

  <h1 class="doc-title">SKIN LESION / DERMOSCOPY EXAMINATION REPORT</h1>
  <div class="doc-meta">
    <strong>Report ID:</strong> ${escapeHtml(reportId)}
    <span class="sep"></span>
    <strong>Examination date:</strong> ${escapeHtml(examDate)}
    <span class="sep"></span>
    <strong>Priority:</strong> ${escapeHtml(triage)}
  </div>

  <div class="sec-head"><span class="sec-title">Patient &amp; Examination Information</span></div>
  <table class="shaded-grid shaded-grid--four">
    <tr>
      <td><span class="lbl">Patient name:</span> ${escapeHtml(assessment.patient_name || 'Not recorded')}</td>
      <td><span class="lbl">Patient ID:</span> ${escapeHtml(assessment.patient_id || 'N/A')}</td>
      <td><span class="lbl">Age:</span> ${escapeHtml(assessment.patient_metadata.age)}</td>
      <td><span class="lbl">Gender:</span> ${escapeHtml(assessment.patient_metadata.sex)}</td>
    </tr>
  </table>

  <div class="sec-head"><span class="sec-title">Clinical Image &amp; Lesion History</span></div>
  <table class="split-tbl">
    <tr>
      <td>
        ${imageBlock}
        <div class="cap">Captured examination image</div>
      </td>
      <td>
        <div class="kv-line"><strong>Location:</strong> ${escapeHtml(assessment.patient_metadata.site)}</div>
        <div class="kv-line"><strong>Duration:</strong> ${escapeHtml(duration)}</div>
        <div class="kv-line"><strong>Reported changes:</strong> ${escapeHtml(reportedChanges)}</div>
        <div class="kv-line"><strong>Symptoms:</strong> ${escapeHtml(symptoms)}</div>
        <div class="kv-line"><strong>Relevant history:</strong> ${escapeHtml(relevantHistory)}</div>
      </td>
    </tr>
  </table>

  <div class="sec-head"><span class="sec-title">Findings</span><span class="sec-sub">&nbsp;&nbsp;|&nbsp;&nbsp;clinician documented</span></div>
  <div class="key-findings-box">
    <p class="finding-line" style="margin-bottom:4px;"><strong>Key / Unusual findings:</strong> ${escapeHtml(keyFindingsSummary)}</p>
    ${keyFlagsHtml}
  </div>
  <p class="finding-line"><strong>Clinical / dermoscopic observations:</strong> ${escapeHtml(observations)}</p>
  <p class="finding-line"><strong>Measurements (if calibrated):</strong> ${escapeHtml(measurements)}</p>
  <p class="finding-line"><strong>Associated observations:</strong> ${escapeHtml(associatedObservations)}</p>

  <div class="sec-head"><span class="sec-title">Clinical Impression &amp; Assessment</span></div>
  <table class="shaded-grid">
    <tr>
      <td><span class="lbl">Clinical impression:</span> ${escapeHtml(impression)}</td>
      <td><span class="lbl">Differential diagnoses:</span> ${escapeHtml(differentials)}</td>
    </tr>
  </table>

  <div class="sec-head"><span class="sec-title">Recommendation / Follow-up</span></div>
  <p class="finding-line"><strong>Recommended plan:</strong> ${escapeHtml(recommendedPlan)}</p>
  <p class="finding-line"><strong>Follow-up:</strong> ${escapeHtml(followUp)}</p>
  <p class="finding-line"><strong>Patient advice / safety-netting:</strong> ${escapeHtml(safetyNetAdvice)}</p>

  <div class="page-two">
    <h1 class="doc-title">SUPPORTING AI EVIDENCE</h1>
    <div class="doc-meta">
      <strong>Linked report:</strong> ${escapeHtml(reportId)}
      <span class="sep"></span>
      <strong>Analysis ID:</strong> ${escapeHtml(assessment.analysis_id.slice(0, 8))}
      <span class="sep"></span>
      <strong>Status:</strong> Completed
    </div>

    <div class="ai-callout">
      <div class="ai-callout-title">AI Model evidence for clinician review</div>
      <div class="ai-callout-body">This page shows Model-generated supporting evidence, not a confirmed medical diagnosis. Use only actual results from the same examination.</div>
    </div>

    <div class="sec-head"><span class="sec-title">Highest AI Prediction</span></div>
    <table class="shaded-grid">
      <tr>
        <td><span class="lbl">Predicted lesion class:</span> ${escapeHtml(assessment.leading_class)}</td>
        <td><span class="lbl">Model score:</span> ${(leadingScore * 100).toFixed(1)}%</td>
      </tr>
    </table>
    <p class="note-line"><strong>Note:</strong> AI model scores are not calibrated disease probabilities. If a safety check withholds the prediction, do not show a class or score.</p>

    ${visualEvidenceSection}

    <p class="review-summary"><strong>Clinician concordance:</strong> ${escapeHtml(concordance)} &nbsp;&bull;&nbsp; <strong>AI evidence review:</strong> ${escapeHtml(aiEvidenceReview)}</p>

    <div class="sec-head"><span class="sec-title">Clinician Review &amp; Signature</span></div>
    <table class="sig-tbl">
      <tr>
        <td><strong>Reviewed by:</strong> ${escapeHtml(reviewedBy)}</td>
        <td><strong>Review date:</strong> ${escapeHtml(examDate)}</td>
      </tr>
      <tr>
        <td>Signature: _______________________</td>
        <td>Clinical review status: ${escapeHtml(reviewStatus)}</td>
      </tr>
    </table>

    <div class="footer-note">${footerText}</div>
  </div>
</div>
</body>
</html>`
}

export function prescriptionHtml(_prescription: Prescription, _assessment?: DoctorAssessment) {
  return ''
}

export function openPrintableReport(html: string) {
  const toolbarHtml = `<div class="preview-toolbar" style="position:sticky;top:0;z-index:999;background:#203047;color:#fff;padding:10px 18px;display:flex;justify-content:space-between;align-items:center;font-family:'Aptos','Segoe UI',Arial,sans-serif;font-size:13px;"><span style="font-weight:600;">Report Preview</span><div style="display:flex;gap:8px;"><button type="button" onclick="window.print()" style="background:#146C70;color:#fff;border:0;border-radius:6px;padding:7px 14px;cursor:pointer;font-weight:600;">Print / Save as PDF</button></div></div><style>@media print{.preview-toolbar{display:none!important}}</style>`
  const withToolbar = html.replace('<body>', `<body>${toolbarHtml}`)
  const reportWindow = window.open('', '_blank')
  if (!reportWindow) throw new Error('Allow pop-ups to open the report preview.')
  reportWindow.opener = null
  reportWindow.document.open()
  reportWindow.document.write(withToolbar)
  reportWindow.document.close()
}

export async function downloadReportPdf(assessment: DoctorAssessment): Promise<void> {
  const html = doctorReportHtml(assessment)
  const reportId = assessment.id.slice(0, 8).toUpperCase()
  const patientPart = (assessment.patient_id || assessment.patient_name || 'Patient').replace(/[^A-Za-z0-9_-]+/g, '_')
  const filename = `Skin_Lesion_Report_${patientPart}_${reportId}.pdf`

  const response = await fetch('/api/v1/reports/pdf', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ html, filename }),
  })
  if (!response.ok) {
    throw new Error('Could not generate PDF download.')
  }
  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  window.setTimeout(() => URL.revokeObjectURL(url), 1000)
}
