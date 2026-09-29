import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import {
  Activity,
  Upload,
  RefreshCw,
  X,
  Pencil,
  Scissors,
  Loader2,
  AlertCircle,
  ImageIcon,
  MessageSquare,
  Sparkles,
} from 'lucide-react'

import { ImageAnnotationCanvas } from './components/ImageAnnotationCanvas'
import { PredictionCard } from './components/PredictionCard'
import { ReliabilityCard } from './components/ReliabilityCard'
import { GradCAMSection } from './components/GradCAMSection'
import { SegmentationSection } from './components/SegmentationSection'
import { ChatAssistant } from './components/ChatAssistant'

import { runClassification } from './api'
import type { AnalysisResult, LesionAnnotation } from './types'

export default function App() {
  const [file, setFile] = useState<File | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [annotation, setAnnotation] = useState<LesionAnnotation | null>(null)
  const [enableSegmentation, setEnableSegmentation] = useState<boolean>(false)

  const [loading, setLoading] = useState<boolean>(false)
  const [progress, setProgress] = useState<number>(0)
  const [error, setError] = useState<string | null>(null)

  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [mobileTab, setMobileTab] = useState<'analysis' | 'chat'>('analysis')

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const f = acceptedFiles[0]
    if (!f) return
    setFile(f)
    setPreviewUrl(URL.createObjectURL(f))
    setAnnotation(null)
    setResult(null)
    setError(null)
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'image/jpeg': ['.jpg', '.jpeg'], 'image/png': ['.png'] },
    maxFiles: 1,
    maxSize: 20 * 1024 * 1024,
    disabled: loading,
  })

  const handleReset = () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl)
    setFile(null)
    setPreviewUrl(null)
    setAnnotation(null)
    setResult(null)
    setError(null)
    setProgress(0)
    setEnableSegmentation(false)
  }

  const handleRunAnalysis = async () => {
    if (!file) return
    setLoading(true)
    setError(null)
    setProgress(0)

    try {
      const data = await runClassification(file, annotation, enableSegmentation, undefined, setProgress)
      setResult(data)
    } catch (e: any) {
      setError(e.response?.data?.detail || e.message || 'Classification request failed. Please check FastAPI backend.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col text-slate-900 font-sans">
      {/* Top Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-20 shadow-xs">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="flex items-center justify-between py-3.5">
            {/* Logo */}
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 bg-teal-600 rounded-xl flex items-center justify-center shadow-xs text-white">
                <Activity className="w-5 h-5" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-bold text-slate-900 text-base leading-tight">DermaInsight AI</span>
                  <span className="hidden sm:inline-flex items-center px-2 py-0.5 bg-slate-100 text-slate-600 text-[11px] font-medium rounded-full">
                    FastAPI + PyTorch ResNet50
                  </span>
                </div>
                <div className="text-xs text-slate-500">Skin Lesion Analysis &amp; Clinical Decision Support</div>
              </div>
            </div>

            {/* Right Status */}
            <div className="flex items-center gap-3">
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-emerald-50 border border-emerald-200 text-emerald-700 text-xs font-medium rounded-full">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                Backend Live
              </span>
              {result && (
                <button
                  type="button"
                  onClick={handleReset}
                  className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-600 hover:text-slate-900 bg-slate-100 hover:bg-slate-200 rounded-lg transition cursor-pointer"
                >
                  + New Analysis
                </button>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Guide Banner */}
      <div className="bg-white border-b border-slate-200 py-2.5 px-4 sm:px-6">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs text-slate-500">
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1 font-semibold text-teal-800 bg-teal-50 px-2 py-0.5 rounded-full border border-teal-200">
              <Sparkles className="w-3 h-3 text-teal-600" /> Clinical Workflow
            </span>
            <span>Upload/Annotate lesion &rarr; Run PyTorch ResNet50 &rarr; Ask AI chatbot grounded in results.</span>
          </div>
          {result && (
            <div className="text-teal-700 font-medium flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-teal-500 animate-pulse" />
              Active result: <strong>{result.predicted_class_display}</strong>
            </div>
          )}
        </div>
      </div>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6 flex-1 w-full">
        {/* Mobile Tab Switcher */}
        <div className="flex lg:hidden gap-1 mb-5 p-1 bg-white rounded-xl border border-slate-200 shadow-xs">
          <button
            type="button"
            onClick={() => setMobileTab('analysis')}
            className={`flex-1 flex items-center justify-center gap-2 py-2 text-xs sm:text-sm font-medium rounded-lg transition cursor-pointer ${
              mobileTab === 'analysis' ? 'bg-teal-600 text-white shadow-xs' : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <ImageIcon className="w-4 h-4" />
            Upload &amp; Results
          </button>

          <button
            type="button"
            onClick={() => setMobileTab('chat')}
            className={`flex-1 flex items-center justify-center gap-2 py-2 text-xs sm:text-sm font-medium rounded-lg transition relative cursor-pointer ${
              mobileTab === 'chat' ? 'bg-teal-600 text-white shadow-xs' : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <MessageSquare className="w-4 h-4" />
            AI Chatbot
            {result && <span className="w-2 h-2 rounded-full bg-teal-400" />}
          </button>
        </div>

        {/* 2-Column Responsive Workspace */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          {/* Left Column: Upload, Annotation & Results */}
          <div className={`lg:col-span-7 space-y-6 ${mobileTab === 'chat' ? 'hidden lg:block' : 'block'}`}>
            {/* Upload & Annotation Box */}
            <div className="rounded-2xl border border-slate-200 bg-white shadow-xs p-5 space-y-4">
              <div>
                <h2 className="text-base font-bold text-slate-900">Upload &amp; Annotate Lesion Image</h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  Upload a dermoscopy image. You can draw/box the lesion region to isolate the ROI.
                </p>
              </div>

              {!file ? (
                <div
                  {...getRootProps()}
                  className={`border-2 border-dashed rounded-2xl p-10 text-center cursor-pointer transition-all select-none ${
                    isDragActive
                      ? 'border-teal-400 bg-teal-50'
                      : 'border-slate-200 hover:border-teal-300 hover:bg-slate-50'
                  }`}
                >
                  <input {...getInputProps()} />
                  <div className="flex flex-col items-center gap-3">
                    <div className="w-14 h-14 rounded-2xl bg-teal-50 flex items-center justify-center text-teal-600">
                      <Upload className="w-7 h-7" />
                    </div>
                    <div>
                      <p className="font-semibold text-slate-700 text-sm">
                        {isDragActive ? 'Drop image here...' : 'Drag & drop skin lesion image, or click to browse'}
                      </p>
                      <p className="text-xs text-slate-400 mt-1">Supports JPG, PNG (Max 20 MB)</p>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="space-y-4">
                  {/* Annotation Canvas */}
                  {previewUrl && (
                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-semibold text-slate-700 flex items-center gap-1.5">
                          <Pencil className="w-3.5 h-3.5 text-teal-600" />
                          Interactive Lesion Annotation Canvas
                        </span>
                        <span className="text-slate-400">
                          {annotation?.hasAnnotation ? '✓ ROI Focused for Model' : 'Optional — Draw to outline lesion'}
                        </span>
                      </div>
                      <ImageAnnotationCanvas
                        imageUrl={previewUrl}
                        annotation={annotation}
                        onAnnotationChange={setAnnotation}
                      />
                    </div>
                  )}

                  {/* File Info */}
                  <div className="flex items-center justify-between gap-2 p-2.5 bg-slate-50 rounded-xl border border-slate-200 text-xs">
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="font-medium text-slate-700 truncate">{file.name}</span>
                      <span className="text-slate-400">({(file.size / 1024).toFixed(0)} KB)</span>
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      <button
                        type="button"
                        onClick={handleReset}
                        disabled={loading}
                        className="flex items-center gap-1 text-slate-500 hover:text-teal-600 font-medium transition cursor-pointer"
                      >
                        <RefreshCw className="w-3 h-3" /> Replace
                      </button>
                      <button
                        type="button"
                        onClick={handleReset}
                        disabled={loading}
                        className="flex items-center gap-1 text-red-500 hover:text-red-700 font-medium transition cursor-pointer ml-1"
                      >
                        <X className="w-3 h-3" /> Remove
                      </button>
                    </div>
                  </div>

                  {/* Optional Segmentation Checkbox */}
                  <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl">
                    <label className="flex items-start gap-2.5 cursor-pointer select-none">
                      <input
                        type="checkbox"
                        checked={enableSegmentation}
                        onChange={(e) => setEnableSegmentation(e.target.checked)}
                        className="mt-0.5 rounded border-slate-300 text-teal-600 focus:ring-teal-500 w-4 h-4 accent-teal-600 cursor-pointer"
                      />
                      <div className="text-xs">
                        <span className="font-semibold text-slate-800 flex items-center gap-1.5">
                          <Scissors className="w-3.5 h-3.5 text-teal-600" />
                          Perform Lesion Segmentation (Optional)
                        </span>
                        <p className="text-slate-500 mt-0.5 leading-relaxed">
                          Only runs segmentation if you check this box. If unchecked, segmentation is skipped and only
                          ResNet50 classification is computed.
                        </p>
                      </div>
                    </label>
                  </div>

                  {/* Run Button */}
                  <button
                    type="button"
                    onClick={handleRunAnalysis}
                    disabled={loading}
                    className="w-full flex items-center justify-center gap-2 py-3 bg-teal-600 hover:bg-teal-700 text-white font-semibold rounded-xl transition shadow-xs disabled:opacity-50 cursor-pointer"
                  >
                    {loading ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Running ResNet50 Classifier... {progress > 0 && `${progress}%`}
                      </>
                    ) : (
                      <>
                        {enableSegmentation
                          ? 'Run Classification & Segmentation'
                          : 'Run Classification (ResNet50)'}
                      </>
                    )}
                  </button>
                </div>
              )}

              {error && (
                <div className="flex items-start gap-2 p-3 bg-red-50 border border-red-200 rounded-xl text-xs text-red-700">
                  <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="font-semibold">Inference Error</p>
                    <p>{error}</p>
                  </div>
                </div>
              )}
            </div>

            {/* Result Box (Only visible when analysis result exists) */}
            {result && (
              <div className="space-y-6">
                <PredictionCard result={result} />
                <ReliabilityCard info={result.reliability} />
                <GradCAMSection result={result} />
                <SegmentationSection result={result} />
              </div>
            )}
          </div>

          {/* Right Column: AI Decision-Support Chatbot (Sticky on Desktop) */}
          <div className={`lg:col-span-5 lg:sticky lg:top-20 ${mobileTab === 'analysis' ? 'hidden lg:block' : 'block'}`}>
            <ChatAssistant analysis={result} onClearAnalysis={() => setResult(null)} />
          </div>
        </div>
      </main>

      <footer className="border-t border-slate-200 bg-white py-3 px-4 text-center text-xs text-slate-400">
        DermaInsight AI — Clinical decision-support research platform. Built with React, Tailwind CSS &amp; FastAPI.
      </footer>
    </div>
  )
}
