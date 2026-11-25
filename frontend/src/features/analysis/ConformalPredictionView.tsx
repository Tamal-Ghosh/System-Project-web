import { useState, useMemo } from 'react'
import {
  ShieldCheck,
  Stethoscope,
  SlidersHorizontal,
} from 'lucide-react'
import type { ClassificationResult, ConformalPredictionResult } from '../../services/classification'
import { evaluateConformalSet } from '../../services/classification'

interface ConformalPredictionViewProps {
  result: ClassificationResult
}

export function ConformalPredictionView({ result }: ConformalPredictionViewProps) {
  const [coverage, setCoverage] = useState<number>(0.95)

  const conformal: ConformalPredictionResult = useMemo(() => {
    return evaluateConformalSet(result.scores, coverage)
  }, [result.scores, coverage])

  const coverageOptions = [
    { value: 0.90, title: '90%', subtitle: 'Standard' },
    { value: 0.95, title: '95%', subtitle: 'Recommended' },
    { value: 0.99, title: '99%', subtitle: 'Extra Safe' },
  ]

  const isSingleton = conformal.certainty_tier === 'singleton'
  const pct = Math.round(coverage * 100)

  const doctorHelpText = isSingleton
    ? `Only 1 condition fits at ${pct}% safety, so you can focus on this diagnosis with high confidence.`
    : conformal.contains_malignancy
    ? `A high-risk condition (${conformal.malignant_classes.join(', ')}) cannot be ruled out at ${pct}% safety. Examine closely or consider a biopsy before ruling out cancer.`
    : `Multiple benign conditions are possible. Compare these ${conformal.set_size} candidates during your physical exam.`

  const useSingleColumn = conformal.prediction_set.length === 1

  return (
    <div className="conformal-view" style={{ display: 'flex', flexDirection: 'column', gap: '1.3rem' }}>
      {/* 1. Safety Level Card */}
      <div
        style={{
          background: '#ffffff',
          borderRadius: '12px',
          border: '1px solid #e2e8f0',
          padding: '1.15rem 1.25rem',
          boxShadow: '0 1px 2px rgba(15, 23, 42, 0.04)',
          display: 'flex',
          flexDirection: 'column',
          gap: '0.85rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.55rem' }}>
          <SlidersHorizontal size={18} style={{ color: '#0d9488' }} />
          <strong style={{ fontSize: '1.02rem', color: '#0f172a' }}>Safety Level</strong>
        </div>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(3, 1fr)',
            gap: '0.55rem',
            background: '#f8fafc',
            padding: '0.35rem',
            borderRadius: '10px',
            border: '1px solid #e2e8f0',
          }}
        >
          {coverageOptions.map(opt => {
            const isSelected = coverage === opt.value
            return (
              <button
                key={opt.value}
                type="button"
                onClick={() => setCoverage(opt.value)}
                style={{
                  padding: '0.65rem 0.75rem',
                  borderRadius: '8px',
                  border: isSelected ? '1px solid #0d9488' : '1px solid transparent',
                  background: isSelected ? '#ffffff' : 'transparent',
                  boxShadow: isSelected ? '0 1px 3px rgba(15, 23, 42, 0.08)' : 'none',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '0.4rem',
                  transition: 'all 0.15s ease',
                }}
              >
                <strong style={{ fontSize: '0.98rem', color: isSelected ? '#0f766e' : '#475569' }}>
                  {opt.title}
                </strong>
                <span style={{ fontSize: '0.9rem', color: isSelected ? '#0d9488' : '#64748b', fontWeight: isSelected ? 600 : 400 }}>
                  · {opt.subtitle}
                </span>
              </button>
            )
          })}
        </div>
      </div>

      {/* 2. Safe Diagnosis Set */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <ShieldCheck size={20} style={{ color: '#0d9488' }} />
          <strong style={{ fontSize: '1.05rem', color: '#0f172a' }}>
            Safe Diagnosis Set ({conformal.prediction_set.length})
          </strong>
        </div>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: useSingleColumn ? '1fr' : 'repeat(2, minmax(0, 1fr))',
            gap: '0.85rem',
          }}
        >
          {conformal.prediction_set.map((item, idx) => {
            const isMalignant = item.category === 'Malignant'
            const isPremalignant = item.category === 'Premalignant'
            const isTop = idx === 0

            return (
              <div
                key={item.label}
                style={{
                  background: '#ffffff',
                  border: isTop ? '1.5px solid #0d9488' : '1px solid #e2e8f0',
                  borderRadius: '12px',
                  padding: '1.1rem 1.25rem',
                  boxShadow: '0 1px 3px rgba(15, 23, 42, 0.04)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '0.7rem',
                  width: '100%',
                  maxWidth: useSingleColumn ? '62%' : undefined,
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '0.6rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.55rem', flexWrap: 'wrap' }}>
                    <strong style={{ fontSize: '1.08rem', color: '#0f172a' }}>
                      {item.display_name}
                    </strong>
                    <span
                      style={{
                        fontSize: '0.82rem',
                        fontWeight: 700,
                        padding: '2px 8px',
                        borderRadius: '6px',
                        background: '#f1f5f9',
                        color: '#475569',
                      }}
                    >
                      {item.label}
                    </span>
                  </div>

                  <span
                    style={{
                      fontSize: '0.82rem',
                      fontWeight: 700,
                      padding: '4px 11px',
                      borderRadius: '999px',
                      background: isMalignant ? '#fee2e2' : isPremalignant ? '#fef3c7' : '#dcfce7',
                      color: isMalignant ? '#b91c1c' : isPremalignant ? '#b45309' : '#15803d',
                      flexShrink: 0,
                    }}
                  >
                    {item.category}
                  </span>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
                  <div style={{ flex: 1, height: '10px', background: '#f1f5f9', borderRadius: '999px', overflow: 'hidden' }}>
                    <div
                      style={{
                        width: `${Math.min(100, item.score * 100)}%`,
                        height: '100%',
                        background: isMalignant ? '#dc2626' : '#0d9488',
                        borderRadius: '999px',
                        transition: 'width 0.25s ease',
                      }}
                    />
                  </div>
                  <strong style={{ fontSize: '1.05rem', color: '#0f172a', minWidth: '54px', textAlign: 'right' }}>
                    {(item.score * 100).toFixed(1)}%
                  </strong>
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* 3. How this helps you */}
      <div
        style={{
          background: '#f0fdfa',
          border: '1px solid #ccfbf1',
          borderLeft: '4px solid #0d9488',
          borderRadius: '10px',
          padding: '1rem 1.15rem',
          display: 'flex',
          alignItems: 'flex-start',
          gap: '0.75rem',
        }}
      >
        <Stethoscope size={20} style={{ color: '#0f766e', flexShrink: 0, marginTop: '2px' }} />
        <div style={{ fontSize: '0.96rem', color: '#134e4a', lineHeight: 1.5 }}>
          <strong style={{ color: '#0f766e' }}>How this helps you:</strong> {doctorHelpText}
        </div>
      </div>
    </div>
  )
}
