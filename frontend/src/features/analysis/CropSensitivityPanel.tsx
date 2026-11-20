import { useEffect, useMemo, useRef, useState } from 'react'
import { ArrowLeftRight, Info, LoaderCircle } from 'lucide-react'
import { classify, type ClassificationResult } from '../../services/classification'
import { useAnalysisSession } from './AnalysisSession'

type ClassScore = ClassificationResult['scores'][number]

function leadingScore(scores: ClassScore[]): ClassScore {
  return scores.reduce((best, score) => score.score > best.score ? score : best, scores[0])
}

function percent(score: number) {
  return (score * 100).toFixed(1) + '%'
}

export function CropSensitivityPanel() {
  const { image, region, result, age, sex, site, loading } = useAnalysisSession()
  const [fullImageResult, setFullImageResult] = useState<ClassificationResult | null>(null)
  const [working, setWorking] = useState(false)
  const [error, setError] = useState('')
  const controller = useRef<AbortController | null>(null)

  useEffect(() => {
    controller.current?.abort()
    controller.current = null
    setFullImageResult(null)
    setError('')
    setWorking(false)
    return () => controller.current?.abort()
  }, [image, region, result, age, sex, site])

  const rows = useMemo(() => {
    if (!result || !fullImageResult || result.model_version !== fullImageResult.model_version) return []
    const fullScores = new Map(fullImageResult.scores.map(item => [item.label, item.score]))
    return result.scores
      .map(item => ({ label: item.label, crop: item.score, full: fullScores.get(item.label) ?? 0 }))
      .map(item => ({ ...item, delta: item.crop - item.full }))
      .sort((left, right) => Math.abs(right.delta) - Math.abs(left.delta))
  }, [result, fullImageResult])

  async function compareWithFullImage() {
    if (!image || !region || !result || working) return
    const active = new AbortController()
    controller.current?.abort()
    controller.current = active
    setWorking(true)
    setError('')
    setFullImageResult(null)
    try {
      const response = await classify(image.file, Number(age), sex, site, active.signal)
      if (!active.signal.aborted) setFullImageResult(response)
    } catch (failure) {
      if (!active.signal.aborted) setError(failure instanceof Error ? failure.message : 'The comparison could not be completed. Please retry.')
    } finally {
      if (controller.current === active) {
        controller.current = null
        setWorking(false)
      }
    }
  }

  const cropTop = result ? leadingScore(result.scores) : null
  const fullTop = fullImageResult ? leadingScore(fullImageResult.scores) : null
  const sameModelVersion = result && fullImageResult && result.model_version === fullImageResult.model_version
  const largestChange = rows[0]

  return <section className="crop-sensitivity-panel" aria-label="Crop sensitivity comparison">
    <div className="crop-sensitivity-intro">
      <div>
        <h3>Compare selected crop with full image</h3>
        <p>The selected-crop result is reused. One additional inference runs on the original image with the same metadata.</p>
      </div>
      <button type="button" className="button button--primary" onClick={compareWithFullImage}
        disabled={!image || !region || !result || loading || working}>
        {working ? <LoaderCircle size={16} className="crop-sensitivity-spinner" /> : <ArrowLeftRight size={16} />}
        {working ? 'Comparing…' : 'Compare predictions'}
      </button>
    </div>

    {!image && <p className="crop-sensitivity-hint">Upload an image on Dashboard to begin.</p>}
    {image && !region && <p className="crop-sensitivity-hint">Select a rectangle or freehand region on Dashboard, then run classification on that selection.</p>}
    {image && region && !result && <p className="crop-sensitivity-hint">Run classification on the selected region first. Its result will be compared with the full image.</p>}
    {working && <p className="crop-sensitivity-status" role="status">Running one additional full-image inference. This may take a while.</p>}
    {error && <p className="image-error" role="alert">{error}</p>}
    {result && fullImageResult && !sameModelVersion && <p className="image-error" role="alert">The model version changed between runs, so the predictions cannot be compared as a crop-only experiment.</p>}

    {sameModelVersion && cropTop && fullTop && largestChange && <div className="crop-sensitivity-results" aria-live="polite">
      <div className="crop-sensitivity-summary">
        <article className="crop-sensitivity-result-card">
          <span>Selected crop</span>
          <strong>{cropTop.label}</strong>
          <b>{percent(cropTop.score)}</b>
        </article>
        <article className="crop-sensitivity-result-card">
          <span>Full image</span>
          <strong>{fullTop.label}</strong>
          <b>{percent(fullTop.score)}</b>
        </article>
      </div>
      <p className="crop-sensitivity-model">Compared with the same model version: {fullImageResult.model_version}</p>
      <p className="crop-sensitivity-shift">
        {cropTop.label === fullTop.label
          ? 'The leading class stayed the same. The largest class-score change was ' + largestChange.label + ': ' + (largestChange.delta > 0 ? '+' : '') + (largestChange.delta * 100).toFixed(1) + ' percentage points.'
          : 'The leading class changed from ' + fullTop.label + ' on the full image to ' + cropTop.label + ' on the selected crop.'}
      </p>
      <details className="crop-sensitivity-details">
        <summary>Compare all {rows.length} class scores</summary>
        <div className="crop-sensitivity-table-wrap">
          <table className="crop-sensitivity-table">
            <thead><tr><th>Class</th><th>Full image</th><th>Selected crop</th><th>Change</th></tr></thead>
            <tbody>{rows.map(row => <tr key={row.label}>
              <th scope="row">{row.label}</th>
              <td>{percent(row.full)}</td>
              <td>{percent(row.crop)}</td>
              <td className={row.delta > 0.0005 ? 'positive' : row.delta < -0.0005 ? 'negative' : ''}>
                {row.delta > 0 ? '+' : ''}{(row.delta * 100).toFixed(1)} pp
              </td>
            </tr>)}</tbody>
          </table>
        </div>
      </details>
      <p className="crop-sensitivity-disclosure"><Info size={15} />Score changes describe this model's response to two different image inputs. They are not a diagnostic sensitivity measure or proof of clinical correctness. A freehand selection is evaluated using its rectangular bounding crop. This comparison is not saved.</p>
    </div>}
  </section>
}
