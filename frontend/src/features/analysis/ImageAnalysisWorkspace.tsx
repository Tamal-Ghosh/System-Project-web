import { useEffect, useRef, useState } from 'react'
import { FileText } from 'lucide-react'
import { Link } from 'react-router-dom'
import { ImageWorkspace } from './image/ImageWorkspace'
import { useAnalysisSession } from './AnalysisSession'
import { AnalysisInspector } from './AnalysisInspector'
import { classify } from '../../services/classification'
import { regionBounds } from './image/geometry'

function createReportSnapshot(source: HTMLCanvasElement) {
  const maximumEdge = 720
  const scale = Math.min(1, maximumEdge / Math.max(source.width, source.height))
  const snapshot = document.createElement('canvas')
  snapshot.width = Math.max(1, Math.round(source.width * scale))
  snapshot.height = Math.max(1, Math.round(source.height * scale))
  const context = snapshot.getContext('2d')
  if (!context) return null
  context.drawImage(source, 0, 0, snapshot.width, snapshot.height)
  return snapshot.toDataURL('image/jpeg', .82)
}

export function ImageAnalysisWorkspace() {
  const { image, loading, error, load, clear, region, patientName, setPatientName, patientId, setPatientId, age, setAge, sex, setSex, site, setSite, result, setResult, setReportImageSnapshot } = useAnalysisSession()
  const [isClassifying, setIsClassifying] = useState(false)
  const [requestError, setRequestError] = useState('')
  const [analysisImage, setAnalysisImage] = useState<Blob | undefined>()
  const controller = useRef<AbortController | null>(null)
  const resultsRef = useRef<HTMLDivElement>(null)
  const prevInputsRef = useRef({ image, region, patientName, patientId, age, sex, site })
  useEffect(() => {
    const prev = prevInputsRef.current
    const changed = prev.image !== image || prev.region !== region || prev.patientName !== patientName || prev.patientId !== patientId || prev.age !== age || prev.sex !== sex || prev.site !== site
    prevInputsRef.current = { image, region, patientName, patientId, age, sex, site }
    if (!changed) return
    controller.current?.abort()
    setResult(null); setAnalysisImage(undefined); setReportImageSnapshot(null); setRequestError(''); setIsClassifying(false)
    return () => controller.current?.abort()
  }, [image, region, patientName, patientId, age, sex, site, setResult, setReportImageSnapshot])

  async function handleStartClassification() {
    if (!image || isClassifying) return
    if (patientName.trim().length < 2) {
      setRequestError('Enter the patient name using at least 2 characters.'); return
    }
    if (!/^[A-Za-z0-9][A-Za-z0-9_-]{2,39}$/.test(patientId.trim())) {
      setRequestError('Enter a patient ID using 3–40 letters, numbers, hyphens or underscores.'); return
    }
    if (age.trim() === '' || !Number.isFinite(Number(age)) || Number(age) < 0 || Number(age) > 120 || !sex) {
      setRequestError('Enter an age between 0 and 120 and select gender.'); return
    }
    const active = new AbortController()
    controller.current?.abort(); controller.current = active
    setIsClassifying(true); setRequestError(''); setResult(null); setAnalysisImage(undefined)
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
      setAnalysisImage(blob); setReportImageSnapshot(createReportSnapshot(canvas)); setResult(response)
      requestAnimationFrame(() => resultsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' }))
    } catch (failure) {
      if (!active.signal.aborted) setRequestError(failure instanceof Error ? failure.message : 'Classification failed. Please retry.')
    } finally {
      if (controller.current === active) setIsClassifying(false)
    }
  }

  return <div className="clinical-analysis-page clinical-analysis-page--stacked">
    <ImageWorkspace image={image} loading={loading} error={error} onFile={load}
      onClear={() => { clear(); setPatientName(''); setPatientId(''); setAge(''); setSex(''); setSite('unknown') }} onStartClassification={handleStartClassification}
      isClassifying={isClassifying} hasStartedClassification={!!result} />
    {isClassifying && <p role="status">Running model analysis…</p>}
    {requestError && <p className="image-error" role="alert">{requestError}</p>}
    {result && <div ref={resultsRef} className="classification-reveal-container"><AnalysisInspector hasImage={!!image} result={result} image={analysisImage} age={age} sex={sex} site={site} /><div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '12px' }}><Link to="/reports/new" className="button button--primary"><FileText size={16} />Make Report</Link></div></div>}
  </div>
}
