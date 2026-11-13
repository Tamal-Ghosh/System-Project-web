import { useEffect, useRef, useState } from 'react'
import type { PointerEvent } from 'react'
import { ImagePlus, Upload, Square, Pencil, Undo2, RotateCcw, ZoomIn, ZoomOut, Maximize, Trash2, ScanLine } from 'lucide-react'
import type { LocalImage } from './useLocalImage'
import { createRegionPreview } from './useLocalImage'
import { clampPoint, regionBounds } from './geometry'
import type { Point, Region } from './geometry'
import { useAnalysisSession } from '../AnalysisSession'

interface Props {
  image: LocalImage | null
  loading: boolean
  error: string
  onFile: (file: File) => void
  onClear: () => void
  onStartClassification?: () => void
  isClassifying?: boolean
  hasStartedClassification?: boolean
}

export function ImageWorkspace({
  image,
  loading,
  error,
  onFile,
  onClear,
  onStartClassification,
  isClassifying = false,
  hasStartedClassification = false,
}: Props) {
  const input = useRef<HTMLInputElement>(null)
  const svg = useRef<SVGSVGElement>(null)
  const { tool, setTool, region, setRegion, history, setHistory, zoom, setZoom, view, setView } = useAnalysisSession()
  const [draft, setDraft] = useState<Region | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [previewError, setPreviewError] = useState('')
  const [dragOver, setDragOver] = useState(false)

  useEffect(() => { setDraft(null); setPreview(null); setPreviewError('') }, [image])
  useEffect(() => {
    setPreviewError('')
    if (!image || !region) { setPreview(null); return }
    try { setPreview(createRegionPreview(image, region)) }
    catch { setPreview(null); setPreviewError('The selected input preview could not be created. Reset the region and try again.') }
  }, [image, region])

  function point(event: PointerEvent<SVGSVGElement>): Point | null {
    const matrix = svg.current?.getScreenCTM()
    if (!matrix || !image) return null
    const location = new DOMPoint(event.clientX, event.clientY).matrixTransform(matrix.inverse())
    return clampPoint(location, image.width, image.height)
  }
  function start(event: PointerEvent<SVGSVGElement>) {
    if (event.button !== 0 || !image || view !== 'original') return
    const p = point(event); if (!p) return
    event.currentTarget.setPointerCapture(event.pointerId)
    setDraft({ kind: tool, points: [p, p] })
  }
  function move(event: PointerEvent<SVGSVGElement>) {
    if (!draft) return
    const p = point(event); if (!p) return
    setDraft(previous => previous ? { ...previous, points: previous.kind === 'rectangle' ? [previous.points[0], p] : [...previous.points, p] } : null)
  }
  function end(event: PointerEvent<SVGSVGElement>) {
    if (!draft || !image) return
    if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId)
    const p = point(event)
    const next = p ? { ...draft, points: draft.kind === 'rectangle' ? [draft.points[0], p] : [...draft.points, p] } : draft
    const bounds = regionBounds(next, image.width, image.height)
    if (bounds.width >= 2 && bounds.height >= 2) { setHistory(previous => [...previous, region]); setRegion(next) }
    setDraft(null)
  }
  function reset() { setHistory(previous => [...previous, region]); setRegion(null); setView('original'); setZoom(1) }
  const active = draft ?? region
  const bounds = image && active ? regionBounds(active, image.width, image.height) : null
  const path = active?.points.map((p, i) => `${i ? 'L' : 'M'}${p.x},${p.y}`).join(' ') + (draft ? '' : ' Z')

  return <section className="clinical-image-panel" aria-label="Image workspace">
    <header className="clinical-panel-heading"><div><h2>Lesion image</h2></div></header>
    <input ref={input} type="file" accept="image/jpeg,image/png,image/webp" className="sr-only" aria-label="Choose dermoscopic image" onChange={event => { const file = event.target.files?.[0]; if (file) onFile(file); event.target.value = '' }} />
    <div className="clinical-toolbar" aria-label="Image tools">
      <div className="tool-group"><button disabled={!image || view === 'input'} aria-pressed={tool === 'rectangle'} className={tool === 'rectangle' ? 'selected' : ''} onClick={() => setTool('rectangle')}><Square size={16} />Rectangle</button><button disabled={!image || view === 'input'} aria-pressed={tool === 'freehand'} className={tool === 'freehand' ? 'selected' : ''} onClick={() => setTool('freehand')}><Pencil size={16} />Freehand</button></div>
      <div className="tool-group compact"><button disabled={!history.length} aria-label="Undo region selection" title="Undo" onClick={() => { setRegion(history.at(-1) ?? null); setHistory(previous => previous.slice(0, -1)); setView('original') }}><Undo2 size={16} /></button><button disabled={!image} onClick={reset} aria-label="Reset selection and zoom" title="Reset"><RotateCcw size={16} /></button><span className="tool-divider" /><button disabled={!image || zoom <= 1 || view === 'input'} aria-label="Zoom out" onClick={() => setZoom(value => Math.max(1, value - .5))}><ZoomOut size={16} /></button><button disabled={!image || zoom >= 4 || view === 'input'} aria-label="Zoom in" onClick={() => setZoom(value => Math.min(4, value + .5))}><ZoomIn size={16} /></button><button disabled={!image || view === 'input'} aria-label="Fit image" title="Fit image" onClick={() => setZoom(1)}><Maximize size={16} /></button></div>
    </div>
    <div className={`clinical-viewport ${dragOver ? 'is-dragging' : ''}`} onDragOver={event => { event.preventDefault(); setDragOver(true) }} onDragLeave={() => setDragOver(false)} onDrop={event => { event.preventDefault(); setDragOver(false); const file = event.dataTransfer.files[0]; if (file) onFile(file) }}>
      {image ? (
        <div className="clinical-viewport-inner">
          <div className="viewport-stage">
            {view === 'input' ? (
              <img className="region-preview" src={preview ?? image.src} alt="Selected region preview before model preprocessing" />
            ) : (
              <svg className="image-selection-canvas" ref={svg} viewBox={`${image.width * (1 - 1 / zoom) / 2} ${image.height * (1 - 1 / zoom) / 2} ${image.width / zoom} ${image.height / zoom}`} preserveAspectRatio="xMidYMid meet" aria-label="Image region selection canvas" onPointerDown={start} onPointerMove={move} onPointerUp={end} onPointerCancel={() => setDraft(null)}>
                <image href={image.src} width={image.width} height={image.height} />
                {active && bounds && (active.kind === 'rectangle' ? <rect x={bounds.x} y={bounds.y} width={bounds.width} height={bounds.height} fill="#00968818" stroke="#009688" strokeWidth={2} vectorEffect="non-scaling-stroke" /> : <path d={path} fill="#00968818" stroke="#009688" strokeWidth={2} vectorEffect="non-scaling-stroke" />)}
              </svg>
            )}
          </div>

          {/* Image size indicator below the lesion image */}
          <div className="viewport-dimensions-badge">
            <span>{image.width} × {image.height} px</span>
          </div>
        </div>
      ) : (
        <div className="clinical-upload-empty">
          <div className="upload-icon"><ImagePlus size={29} strokeWidth={1.4} /></div>
          <h3>Your image, in focus.</h3>
          <p>Drop an image here, or choose a file.</p>
          <button className="button button--primary" onClick={() => input.current?.click()} disabled={loading}>
            <Upload size={16} />{loading ? 'Opening image…' : 'Choose image'}
          </button>
          <span>JPG, PNG or WebP · up to 20 MB</span>
        </div>
      )}
      {loading && image && <div className="image-loading" role="status">Opening image…</div>}
    </div>
    {(error || previewError) && <p role="alert" className="image-error">{error || previewError}</p>}
    <div className="clinical-viewer-footer">
      <div className="viewer-mode-actions">
        <div className="image-view-switch">
        <button className={view === 'original' ? 'selected' : ''} aria-pressed={view === 'original'} onClick={() => setView('original')}>Original</button>
        <button disabled={!image || (!!region && !preview)} className={view === 'input' ? 'selected' : ''} aria-pressed={view === 'input'} onClick={() => setView('input')}>Input preview</button>
      </div>
        <button type="button" className="button button--secondary" onClick={onClear} disabled={!image && !loading}>
          <RotateCcw size={15} /> New analysis
        </button>
      </div>

      {image && (
        <div className="viewport-overlay-controls" role="region" aria-label="Image analysis actions">
          <button
            type="button"
            className="viewport-action-btn viewport-action-btn--secondary"
            onClick={() => input.current?.click()}
            disabled={loading}
            title="Upload another dermoscopic image"
          >
            <Upload size={15} />
            <span>Upload image</span>
          </button>

          <button
            type="button"
            className="viewport-action-btn viewport-action-btn--danger"
            onClick={onClear}
            title="Remove current image"
          >
            <Trash2 size={15} />
            <span>Remove</span>
          </button>

          <button
            type="button"
            className={`viewport-action-btn viewport-action-btn--primary ${isClassifying ? 'is-loading' : ''}`}
            onClick={onStartClassification}
            disabled={isClassifying}
            title={hasStartedClassification ? 'Re-run classification analysis' : 'Start classification analysis'}
          >
            {isClassifying ? (
              <>
                <span className="button-spinner" aria-hidden="true" />
                <span>Classifying…</span>
              </>
            ) : (
              <>
                <ScanLine size={15} />
                <span>{hasStartedClassification ? 'Re-run classification' : 'Start classification'}</span>
              </>
            )}
          </button>
        </div>
      )}
    </div>
  </section>
}
