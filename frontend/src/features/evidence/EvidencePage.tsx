import { useSearchParams } from 'react-router-dom'
import {
  Activity,
  FileSpreadsheet,
  ShieldCheck,
  Users,
} from 'lucide-react'
import { SubgroupPerformancePanel } from './SubgroupPerformancePanel'
import { CalibrationPanel } from '../analysis/CalibrationEvidence'

const EVIDENCE_TABS = [
  { id: 'calibration', label: 'Calibration', icon: Activity },
  { id: 'validation', label: 'Validation', icon: ShieldCheck },
  { id: 'subgroups', label: 'Subgroup & external', icon: Users },
] as const

const BENCHMARK_CLASSES = [
  { code: 'MEL', name: 'Melanoma', sensitivity: 84.4, n: 160, risk: 'Critical' },
  { code: 'BCC', name: 'Basal Cell Carcinoma', sensitivity: 86.5, n: 156, risk: 'Critical' },
  { code: 'SCCKA', name: 'Squamous Cell Carcinoma / KA', sensitivity: 81.3, n: 96, risk: 'Critical' },
  { code: 'NV', name: 'Melanocytic Nevus', sensitivity: 89.2, n: 260, risk: 'Benign' },
  { code: 'BKL', name: 'Benign Keratosis (Solar Lentigo/SK)', sensitivity: 83.5, n: 194, risk: 'Benign' },
  { code: 'AKIEC', name: 'Actinic Keratosis / Bowen', sensitivity: 79.2, n: 96, risk: 'Pre-malignant' },
  { code: 'DF', name: 'Dermatofibroma', sensitivity: 85.7, n: 56, risk: 'Benign' },
  { code: 'VASC', name: 'Vascular Lesion (Hemangioma/Pyogenic)', sensitivity: 84.6, n: 52, risk: 'Benign' },
  { code: 'INF', name: 'Inflammatory / Dermatitis', sensitivity: 82.6, n: 46, risk: 'Benign' },
  { code: 'BEN_OTH', name: 'Other Benign Cutaneous Lesion', sensitivity: 80.4, n: 46, risk: 'Benign' },
  { code: 'MAL_OTH', name: 'Other Rare Malignancy (Merkel/Adnexal)', sensitivity: 77.8, n: 38, risk: 'Critical' },
]

export function EvidencePage() {
  const [params, setParams] = useSearchParams()
  const activeTab = (params.get('tab') || params.get('module') || 'calibration').toLowerCase()

  const setTab = (tab: string) => {
    setParams({ tab })
  }

  return (
    <div className="model-validation-page" style={{ padding: '24px 28px', maxWidth: '1280px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* Header Row */}
      <div className="clinical-page-heading" style={{ margin: 0, paddingBottom: '4px' }}>
        <div>
          <h1 style={{ fontSize: '26px', fontWeight: 800, color: '#0f172a', margin: 0 }}>
            Model Evidence
          </h1>
        </div>
      </div>

      {/* Main Tabbed Container Styled like Inspector Tabs */}
      <div className="evidence-tabs-shell" style={{
        background: '#ffffff',
        border: '1px solid #e2e8f0',
        borderRadius: '10px',
        overflow: 'hidden',
        boxShadow: '0 1px 3px rgba(0,0,0,0.03)'
      }}>
        {/* Navigation Tabs Header */}
        <nav
          className="no-print"
          aria-label="Model evidence sections"
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'flex-start',
            gap: '32px',
            background: '#ffffff',
            borderBottom: '1px solid #e2e8f0',
            padding: '0 24px',
          }}
        >
          {EVIDENCE_TABS.map(({ id, label, icon: Icon }) => {
            const isSelected = activeTab === id
            return (
              <button
                type="button"
                key={id}
                aria-pressed={isSelected}
                aria-controls="evidence-content"
                onClick={() => setTab(id)}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '14px 4px',
                  minHeight: '48px',
                  border: 'none',
                  borderBottom: isSelected ? '2.5px solid #008d80' : '2.5px solid transparent',
                  background: 'none',
                  fontSize: '14.5px',
                  fontWeight: isSelected ? 650 : 500,
                  color: isSelected ? '#007d72' : '#59708b',
                  cursor: 'pointer',
                  flex: 'none',
                  transition: 'color 0.15s ease, border-color 0.15s ease',
                }}
              >
                <Icon size={16} strokeWidth={isSelected ? 2 : 1.7} />
                <span>{label}</span>
              </button>
            )
          })}
        </nav>

        {/* Tab Content Area */}
        <div id="evidence-content" className="evidence-tab-content" style={{ padding: '22px' }}>
          {activeTab === 'calibration' && (
            <div>
              <CalibrationPanel hideLimitations={true} />
            </div>
          )}

          {activeTab === 'validation' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              {/* KPI Performance Highlights */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '14px' }}>
                <div style={{ background: '#f8fafc', padding: '16px', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
                  <span style={{ fontSize: '12px', color: '#64748b', fontWeight: 600 }}>Balanced Accuracy</span>
                  <strong style={{ display: 'block', fontSize: '20px', color: '#0f172a', margin: '4px 0 2px' }}>84.15%</strong>
                  <span style={{ fontSize: '11.5px', color: '#64748b' }}>95% CI: [80.62%, 87.97%]</span>
                </div>
                <div style={{ background: '#f8fafc', padding: '16px', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
                  <span style={{ fontSize: '12px', color: '#64748b', fontWeight: 600 }}>Macro ROC-AUC</span>
                  <strong style={{ display: 'block', fontSize: '20px', color: '#0f172a', margin: '4px 0 2px' }}>90.89%</strong>
                  <span style={{ fontSize: '11.5px', color: '#64748b' }}>95% CI: [89.08%, 92.55%]</span>
                </div>
                <div style={{ background: '#f8fafc', padding: '16px', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
                  <span style={{ fontSize: '12px', color: '#64748b', fontWeight: 600 }}>Melanoma (MEL) Sensitivity</span>
                  <strong style={{ display: 'block', fontSize: '20px', color: '#047857', margin: '4px 0 2px' }}>84.38%</strong>
                  <span style={{ fontSize: '11.5px', color: '#64748b' }}>Critical Malignancy Target</span>
                </div>
                <div style={{ background: '#f8fafc', padding: '16px', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
                  <span style={{ fontSize: '12px', color: '#64748b', fontWeight: 600 }}>Basal Cell (BCC) Sensitivity</span>
                  <strong style={{ display: 'block', fontSize: '20px', color: '#047857', margin: '4px 0 2px' }}>86.54%</strong>
                  <span style={{ fontSize: '11.5px', color: '#64748b' }}>High Clinical Concordance</span>
                </div>
              </div>

              {/* Class-wise Performance Table */}
              <div style={{
                background: '#ffffff',
                border: '1px solid #e2e8f0',
                borderRadius: '8px',
                overflow: 'hidden',
              }}>
                <div style={{ padding: '14px 18px', borderBottom: '1px solid #e2e8f0', background: '#fafcfd', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <FileSpreadsheet size={17} style={{ color: '#008579' }} />
                    <h4 style={{ margin: 0, fontSize: '15px', fontWeight: 700, color: '#0f172a' }}>
                      Diagnostic Class Sensitivity &amp; Test Volume (N=1,200)
                    </h4>
                  </div>
                </div>

                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13.5px' }}>
                    <thead>
                      <tr style={{ background: '#f8fafc', borderBottom: '1px solid #e2e8f0' }}>
                        <th style={{ padding: '11px 16px', color: '#475569', fontWeight: 650 }}>Class Acronym</th>
                        <th style={{ padding: '11px 16px', color: '#475569', fontWeight: 650 }}>Full Clinical Description</th>
                        <th style={{ padding: '11px 16px', color: '#475569', fontWeight: 650 }}>Risk Category</th>
                        <th style={{ padding: '11px 16px', color: '#475569', fontWeight: 650, textAlign: 'center' }}>Samples (N)</th>
                        <th style={{ padding: '11px 16px', color: '#475569', fontWeight: 650, textAlign: 'right' }}>Sensitivity</th>
                      </tr>
                    </thead>
                    <tbody>
                      {BENCHMARK_CLASSES.map((cls, idx) => (
                        <tr key={cls.code} style={{ borderBottom: '1px solid #f1f5f9', background: idx % 2 === 0 ? '#ffffff' : '#fafcfd' }}>
                          <td style={{ padding: '11px 16px', fontWeight: 700, color: '#0f172a' }}>{cls.code}</td>
                          <td style={{ padding: '11px 16px', color: '#334155' }}>{cls.name}</td>
                          <td style={{ padding: '11px 16px' }}>
                            <span style={{
                              display: 'inline-block',
                              padding: '2px 8px',
                              borderRadius: '4px',
                              fontSize: '11.5px',
                              fontWeight: 700,
                              background: cls.risk === 'Critical' ? '#fef2f2' : cls.risk === 'Pre-malignant' ? '#fffbeb' : '#f0fdf4',
                              color: cls.risk === 'Critical' ? '#991b1b' : cls.risk === 'Pre-malignant' ? '#92400e' : '#166534',
                            }}>
                              {cls.risk}
                            </span>
                          </td>
                          <td style={{ padding: '11px 16px', textAlign: 'center', color: '#64748b' }}>{cls.n}</td>
                          <td style={{ padding: '11px 16px', textAlign: 'right', fontWeight: 700, color: cls.sensitivity >= 84 ? '#047857' : '#b45309' }}>
                            {cls.sensitivity.toFixed(1)}%
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'subgroups' && (
            <div>
              <SubgroupPerformancePanel />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
