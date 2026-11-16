import { useEffect, useRef, useState } from 'react'
import { ImageWorkspace } from './image/ImageWorkspace'
import { useAnalysisSession } from './AnalysisSession'
import { AnalysisInspector } from './AnalysisInspector'
import { classify } from '../../services/classification'
import { regionBounds } from './image/geometry'

export function ImageAnalysisWorkspace() {
  const { image, loading, error, load, clear, region, age, setAge, sex, setSex, site, setSite, result, setResult } = useAnalysisSession()
  const [isClassifying, setIsClassifying] = useState(false)
  const [requestError, setRequestError] = useState('')
  const controller = useRef<AbortController | null>(null)
  const resultsRef = useRef<HTMLDivElement>(null)
  useEffect(() => {
    controller.current?.abort()
    setResult(null); setRequestError(''); setIsClassifying(false)
    return () => controller.current?.abort()
  }, [image, region, age, sex, site, setResult])

  async function handleStartClassification() {
    if (!image || isClassifying) return
    if (age.trim() === '' || !Number.isFinite(Number(age)) || Number(age) < 0 || Number(age) > 120 || !sex) {
      setRequestError('Enter an age between 0 and 120 and select gender.'); return
    }
    const active = new AbortController()
    controller.current?.abort(); controller.current = active
    setIsClassifying(true); setRequestError(''); setResult(null)
    try {
      const bounds = region ? regionBounds(region, image.width, image.height) : { x: 0, y: 0, width: image.width, height: image.height }
      const canvas = document.createElement('canvas')
      canvas.width = bounds.width; canvas.height = bounds.height
      const context = canvas.getContext('2d')
      if (!context) throw new Error('Could not prepare the selected image.')
      context.drawImage(image.element, bounds.x, bounds.y, bounds.width, bounds.height, 0, 0, canvas.width, canvas.height)
      const blob = await new Promise<Blob>((resolve, reject) => canvas.toBlob(value => value ? resolve(value) : reject(new Error('Could not prepare image.')), 'image/png'))
      if (active.signal.aborted) return
      const response = await classify(blob, Number(age), sex, site, active.signal)
      if (active.signal.aborted) return
      setResult(response)
      requestAnimationFrame(() => resultsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' }))
    } catch (failure) {
      if (!active.signal.aborted) setRequestError(failure instanceof Error ? failure.message : 'Classification failed. Please retry.')
    } finally {
      if (controller.current === active) setIsClassifying(false)
    }
  }

  return <div className="clinical-analysis-page clinical-analysis-page--stacked">
    <ImageWorkspace image={image} loading={loading} error={error} onFile={load}
      onClear={() => { clear(); setAge(''); setSex(''); setSite('unknown') }} onStartClassification={handleStartClassification}
      isClassifying={isClassifying} hasStartedClassification={!!result} />
    {isClassifying && <p role="status">Running model analysis…</p>}
    {requestError && <p className="image-error" role="alert">{requestError}</p>}
    {result && <div ref={resultsRef} className="classification-reveal-container"><AnalysisInspector hasImage={!!image} result={result} /></div>}
  </div>
}
