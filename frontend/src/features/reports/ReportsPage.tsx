import { AlertCircle, Download, FileText, LoaderCircle, Pencil, Search, Trash2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { deleteAssessment, getAssessments } from '../../services/assessments'
import type { DoctorAssessment } from '../../services/assessments'
import { doctorReportHtml, downloadReportPdf, openPrintableReport } from '../../services/reports'

export function ReportsPage() {
  const navigate = useNavigate()
  const [reports, setReports] = useState<DoctorAssessment[]>([])
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [confirmDelete, setConfirmDelete] = useState<DoctorAssessment | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [downloadingId, setDownloadingId] = useState<string | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    getAssessments(controller.signal)
      .then(rows => setReports(rows.slice(0, 5)))
      .catch(failure => {
        if (failure?.name !== 'AbortError') setError(failure instanceof Error ? failure.message : 'Reports could not be loaded.')
      })
      .finally(() => setLoading(false))
    return () => controller.abort()
  }, [])

  async function handleDownload(report: DoctorAssessment) {
    if (downloadingId) return
    setDownloadingId(report.id)
    setError('')
    try {
      await downloadReportPdf(report)
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'Could not download report PDF.')
    } finally {
      setDownloadingId(null)
    }
  }

  async function handleConfirmDelete() {
    if (!confirmDelete || deletingId) return
    const target = confirmDelete
    setDeletingId(target.id)
    setError('')
    try {
      await deleteAssessment(target.id)
      setReports(previous => previous.filter(item => item.id !== target.id))
      setConfirmDelete(null)
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'Report could not be deleted.')
    } finally {
      setDeletingId(null)
    }
  }

  const normalizedQuery = query.trim().toLowerCase()
  const filteredReports = reports.filter(item => {
    if (!normalizedQuery) return true
    const patientName = (item.patient_name || '').toLowerCase()
    const patientId = (item.patient_id || '').toLowerCase()
    const analysisId = item.analysis_id.toLowerCase()
    const diagnosis = (item.suspected_diagnosis || item.leading_class || '').toLowerCase()
    const leadingClass = item.leading_class.toLowerCase()
    return (
      patientName.includes(normalizedQuery) ||
      patientId.includes(normalizedQuery) ||
      analysisId.includes(normalizedQuery) ||
      diagnosis.includes(normalizedQuery) ||
      leadingClass.includes(normalizedQuery)
    )
  })

  return (
    <div className="reports-page">
      <div className="clinical-page-heading">
        <div>
          <div className="eyebrow">Clinical documents</div>
          <h1>Reports</h1>
          <p>Latest 5 saved reports with patient details and analysis summary.</p>
        </div>
      </div>

      <div style={{ position: 'relative', marginBottom: '18px' }}>
        <Search size={16} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', opacity: 0.6 }} />
        <input
          type="search"
          value={query}
          onChange={event => setQuery(event.target.value)}
          placeholder="Search by patient name, patient ID, or analysis..."
          aria-label="Search reports"
          style={{ width: '100%', padding: '10px 14px 10px 38px', borderRadius: '8px', border: '1px solid var(--border, #d8e2e6)', fontSize: '14px' }}
        />
      </div>

      {confirmDelete && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="delete-confirm-title"
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(16, 42, 67, 0.45)',
            display: 'grid',
            placeItems: 'center',
            zIndex: 1000,
            padding: '16px',
          }}
        >
          <div style={{ background: '#fff', borderRadius: '10px', padding: '22px', maxWidth: '420px', width: '100%', boxShadow: '0 12px 32px rgba(0,0,0,0.18)' }}>
            <h2 id="delete-confirm-title" style={{ marginTop: 0, fontSize: '17px' }}>Delete report?</h2>
            <p style={{ margin: '8px 0 18px', color: '#486581' }}>
              Are you sure you want to permanently delete the report for{' '}
              <strong>{confirmDelete.patient_name || 'Patient'}</strong> ({confirmDelete.patient_id || 'No ID'})?
            </p>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button
                type="button"
                className="button button--secondary"
                disabled={Boolean(deletingId)}
                onClick={() => setConfirmDelete(null)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="button button--primary"
                style={{ background: '#c92a2a', borderColor: '#c92a2a' }}
                disabled={Boolean(deletingId)}
                onClick={handleConfirmDelete}
              >
                <Trash2 size={15} />{deletingId ? 'Deleting…' : 'Confirm Delete'}
              </button>
            </div>
          </div>
        </div>
      )}

      {loading && <div className="reviews-state"><LoaderCircle className="spin" size={24} />Loading saved reports…</div>}
      {error && <div className="reviews-state reviews-state--error"><AlertCircle size={24} /><strong>Reports error</strong><p>{error}</p></div>}
      {!loading && reports.length === 0 && !error && (
        <div className="reviews-state">
          <FileText size={30} />
          <strong>No reports saved yet</strong>
          <p>Run an analysis on the dashboard and click Make Report to create one.</p>
        </div>
      )}
      {!loading && reports.length > 0 && filteredReports.length === 0 && (
        <div className="reviews-state">
          <Search size={28} />
          <strong>No matching reports</strong>
          <p>Try another patient name, patient ID, or analysis name.</p>
        </div>
      )}
      {!loading && filteredReports.length > 0 && (
        <div className="report-list">
          {filteredReports.map(report => {
            const patientName = report.patient_name || 'Patient name not recorded'
            const patientId = report.patient_id || 'No ID'
            const analysisName = report.suspected_diagnosis || report.leading_class
            const isDownloading = downloadingId === report.id
            return (
              <article className="report-card" key={report.id}>
                <div className="report-card__case">
                  <span className="report-card__date">
                    {new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(report.created_at))}
                  </span>
                  <h2>{patientName} <small style={{ fontWeight: 500, opacity: 0.75 }}>({patientId})</small></h2>
                  <p>
                    <strong>Analysis:</strong> {analysisName} ({report.analysis_id.slice(0, 8)}) · {report.patient_metadata.site} · {report.patient_metadata.age} years
                  </p>
                </div>
                <div className="report-card__actions" style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                  <button
                    type="button"
                    className="button button--secondary"
                    onClick={() => openPrintableReport(doctorReportHtml(report))}
                  >
                    <FileText size={16} />Open Report
                  </button>
                  <button
                    type="button"
                    className="button button--primary"
                    disabled={Boolean(downloadingId)}
                    onClick={() => handleDownload(report)}
                  >
                    <Download size={15} />{isDownloading ? 'Downloading…' : 'Download PDF'}
                  </button>
                  <button
                    type="button"
                    className="button button--secondary"
                    onClick={() => navigate(`/reports/edit/${report.id}`, { state: { report } })}
                  >
                    <Pencil size={15} />Edit
                  </button>
                  <button
                    type="button"
                    className="button button--secondary"
                    style={{ color: '#c92a2a', borderColor: '#f3c6c6' }}
                    onClick={() => setConfirmDelete(report)}
                  >
                    <Trash2 size={15} />Delete
                  </button>
                </div>
              </article>
            )
          })}
        </div>
      )}
    </div>
  )
}
