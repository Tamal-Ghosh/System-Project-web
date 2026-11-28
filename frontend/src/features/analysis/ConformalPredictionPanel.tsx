import { ShieldCheck, Sparkles } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useAnalysisSession } from './AnalysisSession'
import { ConformalPredictionView } from './ConformalPredictionView'

export function ConformalPredictionPanel() {
  const { result } = useAnalysisSession()

  return (
    <div className="conformal-panel" style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {result ? (
        <ConformalPredictionView result={result} />
      ) : (
        <div
          style={{
            background: '#ffffff',
            border: '1px dashed #cbd5e1',
            borderRadius: '12px',
            padding: '2.25rem 1.75rem',
            textAlign: 'center',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '0.85rem',
          }}
        >
          <div
            style={{
              width: '48px',
              height: '48px',
              borderRadius: '50%',
              background: '#f1f5f9',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#64748b',
            }}
          >
            <ShieldCheck size={26} />
          </div>
          <h3 style={{ margin: 0, fontSize: '1.15rem', color: '#0f172a' }}>
            No Image Analyzed Yet
          </h3>
          <p style={{ margin: 0, fontSize: '0.96rem', color: '#64748b', maxWidth: '460px', lineHeight: 1.5 }}>
            Upload a skin lesion photo on the Dashboard and run an analysis to see the likely condition set here.
          </p>
          <Link
            to="/dashboard"
            className="button button--primary"
            style={{ marginTop: '0.3rem', display: 'inline-flex', alignItems: 'center', gap: '6px', fontSize: '0.95rem' }}
          >
            <Sparkles size={16} /> Go to Dashboard
          </Link>
        </div>
      )}
    </div>
  )
}
