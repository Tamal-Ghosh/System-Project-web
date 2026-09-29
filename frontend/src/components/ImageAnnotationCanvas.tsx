import React, { useRef, useState, useEffect, useCallback } from 'react'
import { Pencil, Square, RotateCcw, Check, Sparkles, Eye, Info } from 'lucide-react'
import type { LesionAnnotation } from '../types'

interface Props {
  imageUrl: string
  annotation: LesionAnnotation | null
  onAnnotationChange: (annotation: LesionAnnotation | null) => void
}

export function ImageAnnotationCanvas({ imageUrl, annotation, onAnnotationChange }: Props) {
  const imageRef = useRef<HTMLImageElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)

  const [tool, setTool] = useState<'freehand' | 'bbox'>('freehand')
  const [isDrawing, setIsDrawing] = useState(false)
  const [startPos, setStartPos] = useState<{ x: number; y: number } | null>(null)
  const [points, setPoints] = useState<Array<{ x: number; y: number }>>([])
  const [hasDrawn, setHasDrawn] = useState(annotation?.hasAnnotation ?? false)
  const [showOriginal, setShowOriginal] = useState(false)

  const syncCanvasSize = useCallback(() => {
    const img = imageRef.current
    const canvas = canvasRef.current
    if (!img || !canvas) return

    canvas.width = img.clientWidth
    canvas.height = img.clientHeight
    redraw()
  }, [])

  useEffect(() => {
    window.addEventListener('resize', syncCanvasSize)
    return () => window.removeEventListener('resize', syncCanvasSize)
  }, [syncCanvasSize])

  const redraw = useCallback(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    ctx.clearRect(0, 0, canvas.width, canvas.height)
    if (showOriginal || !hasDrawn) return

    if (tool === 'freehand' && points.length > 1) {
      ctx.beginPath()
      ctx.moveTo(points[0].x, points[0].y)
      for (let i = 1; i < points.length; i++) {
        ctx.lineTo(points[i].x, points[i].y)
      }
      ctx.strokeStyle = '#06b6d4' // Neon cyan
      ctx.lineWidth = 3
      ctx.lineCap = 'round'
      ctx.lineJoin = 'round'
      ctx.stroke()

      ctx.fillStyle = 'rgba(6, 182, 212, 0.18)'
      ctx.closePath()
      ctx.fill()
    } else if (tool === 'bbox' && startPos && points.length > 0) {
      const current = points[points.length - 1]
      const x = Math.min(startPos.x, current.x)
      const y = Math.min(startPos.y, current.y)
      const w = Math.abs(startPos.x - current.x)
      const h = Math.abs(startPos.y - current.y)

      ctx.strokeStyle = '#06b6d4'
      ctx.lineWidth = 2.5
      ctx.setLineDash([4, 4])
      ctx.strokeRect(x, y, w, h)
      ctx.setLineDash([])

      ctx.fillStyle = 'rgba(6, 182, 212, 0.18)'
      ctx.fillRect(x, y, w, h)
    }
  }, [hasDrawn, points, showOriginal, startPos, tool])

  useEffect(() => {
    redraw()
  }, [redraw])

  const getCanvasCoords = (e: React.MouseEvent | React.TouchEvent) => {
    const canvas = canvasRef.current
    if (!canvas) return { x: 0, y: 0 }
    const rect = canvas.getBoundingClientRect()
    const clientX = 'touches' in e ? e.touches[0].clientX : e.clientX
    const clientY = 'touches' in e ? e.touches[0].clientY : e.clientY
    return {
      x: clientX - rect.left,
      y: clientY - rect.top,
    }
  }

  const handleStart = (e: React.MouseEvent | React.TouchEvent) => {
    e.preventDefault()
    const coords = getCanvasCoords(e)
    setIsDrawing(true)
    setStartPos(coords)
    setPoints([coords])
  }

  const handleMove = (e: React.MouseEvent | React.TouchEvent) => {
    if (!isDrawing) return
    e.preventDefault()
    const coords = getCanvasCoords(e)
    if (tool === 'freehand') {
      setPoints((prev) => [...prev, coords])
    } else {
      setPoints([coords])
    }
  }

  const handleEnd = () => {
    if (!isDrawing) return
    setIsDrawing(false)
    setHasDrawn(true)

    const img = imageRef.current
    const canvas = canvasRef.current
    if (!img || !canvas) return

    // Calculate natural image scaling factor
    const scaleX = img.naturalWidth / canvas.width
    const scaleY = img.naturalHeight / canvas.height

    let roiBbox: { x: number; y: number; width: number; height: number } | undefined

    if (tool === 'bbox' && startPos && points.length > 0) {
      const last = points[points.length - 1]
      const x = Math.min(startPos.x, last.x) * scaleX
      const y = Math.min(startPos.y, last.y) * scaleY
      const w = Math.abs(startPos.x - last.x) * scaleX
      const h = Math.abs(startPos.y - last.y) * scaleY

      roiBbox = {
        x: Math.round(x),
        y: Math.round(y),
        width: Math.round(w),
        height: Math.round(h),
      }
    } else if (tool === 'freehand' && points.length > 2) {
      const xs = points.map((p) => p.x * scaleX)
      const ys = points.map((p) => p.y * scaleY)
      const minX = Math.min(...xs)
      const maxX = Math.max(...xs)
      const minY = Math.min(...ys)
      const maxY = Math.max(...ys)

      roiBbox = {
        x: Math.round(minX),
        y: Math.round(minY),
        width: Math.round(maxX - minX),
        height: Math.round(maxY - minY),
      }
    }

    onAnnotationChange({
      hasAnnotation: true,
      mode: tool,
      strokePoints: points,
      roiBbox,
    })
  }

  const handleClear = () => {
    setPoints([])
    setStartPos(null)
    setHasDrawn(false)
    onAnnotationChange(null)
    const canvas = canvasRef.current
    if (canvas) {
      const ctx = canvas.getContext('2d')
      ctx?.clearRect(0, 0, canvas.width, canvas.height)
    }
  }

  return (
    <div className="space-y-3">
      {/* Canvas Toolset Bar */}
      <div className="flex flex-wrap items-center justify-between gap-2 p-2 bg-slate-50 border border-slate-200 rounded-xl text-xs">
        <div className="flex items-center gap-1.5">
          <span className="font-semibold text-slate-700 px-1">Tool:</span>
          <button
            type="button"
            onClick={() => setTool('freehand')}
            className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg font-medium transition cursor-pointer ${
              tool === 'freehand'
                ? 'bg-teal-600 text-white shadow-xs'
                : 'text-slate-600 hover:bg-slate-200/60'
            }`}
            title="Freehand pen to circle the lesion"
          >
            <Pencil className="w-3.5 h-3.5" />
            Draw Lesion
          </button>
          <button
            type="button"
            onClick={() => setTool('bbox')}
            className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg font-medium transition cursor-pointer ${
              tool === 'bbox'
                ? 'bg-teal-600 text-white shadow-xs'
                : 'text-slate-600 hover:bg-slate-200/60'
            }`}
            title="Bounding box selection"
          >
            <Square className="w-3.5 h-3.5" />
            Box ROI
          </button>
        </div>

        <div className="flex items-center gap-2">
          {hasDrawn && (
            <button
              type="button"
              onMouseDown={() => setShowOriginal(true)}
              onMouseUp={() => setShowOriginal(false)}
              onTouchStart={() => setShowOriginal(true)}
              onTouchEnd={() => setShowOriginal(false)}
              className="flex items-center gap-1 text-slate-500 hover:text-slate-800 px-2 py-1 rounded select-none font-medium cursor-pointer"
              title="Hold to see image without annotations"
            >
              <Eye className="w-3.5 h-3.5" />
              Peek Original
            </button>
          )}

          {hasDrawn && (
            <button
              type="button"
              onClick={handleClear}
              className="flex items-center gap-1 text-red-600 hover:text-red-700 px-2 py-1 rounded font-medium transition hover:bg-red-50 cursor-pointer"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              Clear
            </button>
          )}
        </div>
      </div>

      {/* Interactive Image & Drawing Canvas */}
      <div className="relative rounded-2xl overflow-hidden bg-slate-900 border border-slate-200 flex items-center justify-center cursor-crosshair select-none touch-none">
        <img
          ref={imageRef}
          src={imageUrl}
          alt="Lesion to annotate"
          onLoad={syncCanvasSize}
          className="object-contain max-h-80 w-full pointer-events-none"
        />

        <canvas
          ref={canvasRef}
          onMouseDown={handleStart}
          onMouseMove={handleMove}
          onMouseUp={handleEnd}
          onMouseLeave={handleEnd}
          onTouchStart={handleStart}
          onTouchMove={handleMove}
          onTouchEnd={handleEnd}
          className="absolute inset-0 w-full h-full"
        />

        {/* Floating guidance chip */}
        <div className="absolute bottom-2 left-2 pointer-events-none">
          {hasDrawn ? (
            <span className="inline-flex items-center gap-1 px-2.5 py-1 bg-teal-900/80 backdrop-blur-md text-teal-200 text-[11px] font-medium rounded-full shadow">
              <Check className="w-3 h-3 text-teal-400" /> Lesion Annotated (ROI focused for model)
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 px-2.5 py-1 bg-black/60 backdrop-blur-md text-slate-200 text-[11px] rounded-full">
              <Sparkles className="w-3 h-3 text-teal-400" /> Draw or box the lesion to isolate ROI
            </span>
          )}
        </div>
      </div>

      <div className="flex items-start gap-1.5 text-xs text-slate-500">
        <Info className="w-3.5 h-3.5 text-slate-400 flex-shrink-0 mt-0.5" />
        <span>
          Annotating isolates the specific lesion ROI for classification. If left unannotated, the full image is analyzed.
        </span>
      </div>
    </div>
  )
}
