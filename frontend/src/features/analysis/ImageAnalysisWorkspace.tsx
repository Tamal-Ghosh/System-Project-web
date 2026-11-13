import { useEffect, useRef, useState } from 'react'
import { ImageWorkspace } from './image/ImageWorkspace'
import { useAnalysisSession } from './AnalysisSession'
import { AnalysisInspector } from './AnalysisInspector'

export function ImageAnalysisWorkspace() {
  const { image, loading, error, load, clear } = useAnalysisSession()
  const [hasStartedClassification, setHasStartedClassification] = useState(false)
  const [isClassifying, setIsClassifying] = useState(false)
  const resultsRef = useRef<HTMLDivElement>(null)

  // Reset classification visibility whenever the image changes or is cleared
  useEffect(() => {
    setHasStartedClassification(false)
    setIsClassifying(false)
  }, [image])

  const handleStartClassification = () => {
    if (!image || isClassifying) return
    setIsClassifying(true)

    // Provide visual feedback during initiation then reveal the classification container
    setTimeout(() => {
      setIsClassifying(false)
      setHasStartedClassification(true)
      setTimeout(() => {
        resultsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
      }, 100)
    }, 400)
  }

  return (
    <div className="clinical-analysis-page clinical-analysis-page--stacked">
      <ImageWorkspace
        image={image}
        loading={loading}
        error={error}
        onFile={load}
        onClear={clear}
        onStartClassification={handleStartClassification}
        isClassifying={isClassifying}
        hasStartedClassification={hasStartedClassification}
      />

      {/* Below part (classification container part): only visible when Start classification is clicked */}
      {hasStartedClassification && (
        <div ref={resultsRef} className="classification-reveal-container">
          <AnalysisInspector hasImage={!!image} />
        </div>
      )}
    </div>
  )
}
