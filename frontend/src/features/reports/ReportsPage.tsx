import { AlertCircle, ChevronDown, FileText, Folder, LoaderCircle, ShieldCheck, UserRound } from 'lucide-react'
import { useEffect, useState } from 'react'
import { getAssessments } from '../../services/assessments'
import type { DoctorAssessment } from '../../services/assessments'
import { doctorReportHtml, openPrintableReport, patientSummaryHtml } from '../../services/reports'

interface ReportCase {
  analysisId: string
  patientId: string
  createdAt: string
  assessment?: DoctorAssessment
}

export function ReportsPage() {
  const [assessments, setAssessments] = useState<DoctorAssessment[]>([])
  const [approved, setApproved] = useState<Record<string, boolean>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const caseMap = new Map<string, ReportCase>()
  assessments.forEach(assessment => caseMap.set(assessment.analysis_id, {
    analysisId: assessment.analysis_id,
    patientId: assessment.patient_id || 'Unassigned legacy records',
    createdAt: assessment.created_at,
    assessment,
  }))

  const patientFolders = [...caseMap.values()]
    .sort((a, b) => Date.parse(b.createdAt) - Date.parse(a.createdAt))
    .reduce<Record<string, ReportCase[]>>((folders, reportCase) => {
      ;(folders[reportCase.patientId] ||= []).push(reportCase)
      return folders
    }, {})

  useEffect(() => {
    const controller = new AbortController()
    getAssessments(controller.signal).then(setAssessments)
      .catch(failure => {
        if (failure?.name !== 'AbortError') setError(failure instanceof Error ? failure.message : 'Reports could not be loaded.')
      }).finally(() => setLoading(false))
    return () => controller.abort()
  }, [])

  return <div className="reports-page">
    <div className="clinical-page-heading"><div><div className="eyebrow">Clinical documents</div><h1>Reports</h1><p>Doctor assessments and prescriptions are organized by patient and analysis.</p></div></div>
    <div className="report-type-guide"><div><FileText size={22} /><div><strong>Doctor clinical report</strong><p>Technical model output, clinical assessment and audit information.</p></div></div><div><UserRound size={22} /><div><strong>Patient summary</strong><p>Plain-language next steps. Requires explicit doctor approval.</p></div></div></div>
    {loading && <div className="reviews-state"><LoaderCircle className="spin" size={24} />Loading assessed cases…</div>}
    {error && <div className="reviews-state reviews-state--error"><AlertCircle size={24} /><strong>Reports unavailable</strong><p>{error}</p></div>}
    {!loading && !error && caseMap.size === 0 && <div className="reviews-state"><FileText size={30} /><strong>No clinical documents yet</strong><p>Save a doctor assessment or prescription to create a patient record.</p></div>}
    {!loading && !error && caseMap.size > 0 && <div className="patient-report-folders">{Object.entries(patientFolders).map(([patientId, cases], folderIndex) => <details className="patient-report-folder" key={patientId} open={folderIndex === 0}>
      <summary><span className="folder-icon"><Folder size={21} /></span><span><strong>{patientId}</strong><small>{cases.length} {cases.length === 1 ? 'clinical case' : 'clinical cases'}</small></span><ChevronDown className="folder-chevron" size={18} /></summary>
      <div className="report-list">{cases.map((reportCase, caseIndex) => {
        const { assessment, prescription } = reportCase
        const metadata = assessment!.patient_metadata
        const leadingClass = assessment!.suspected_diagnosis || assessment!.leading_class
        const approvalKey = assessment?.id || reportCase.analysisId
        return <article className="report-card" key={reportCase.analysisId}><div className="report-card__case"><span className="case-number">Case {String(cases.length - caseIndex).padStart(2, '0')}</span><span className="report-card__date">{new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(reportCase.createdAt))}</span><h2>{leadingClass}</h2><p>Analysis {reportCase.analysisId.slice(0, 8)} · {metadata.site} · {metadata.age} years</p></div><div className="report-card__actions">{assessment && <><button className="button button--secondary" onClick={() => openPrintableReport(doctorReportHtml(assessment))}><FileText size={16} />Doctor report</button><label className="patient-approval"><input type="checkbox" checked={!!approved[approvalKey]} onChange={event => setApproved(current => ({ ...current, [approvalKey]: event.target.checked }))} /><ShieldCheck size={15} />Approve patient summary</label><button className="button button--secondary" disabled={!approved[approvalKey]} onClick={() => openPrintableReport(patientSummaryHtml(assessment))}><UserRound size={16} />Patient summary</button></>}</div></article>
      })}</div>
    </details>)}</div>}
  </div>
}
