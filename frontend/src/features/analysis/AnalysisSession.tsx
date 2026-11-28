import { forgetAssistantCase, rememberAssistantCase, restoreAssistantCase } from '../../services/assistant'
import { createContext, useContext, useEffect, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { useLocalImage } from './image/useLocalImage'
import type { ClassificationResult } from '../../services/classification'
import type { Region } from './image/geometry'

function useSessionState() {
  const source = useLocalImage()
  const [patientName, setPatientName] = useState('')
  const [patientId, setPatientId] = useState('')
  const [age, setAge] = useState('')
  const [sex, setSex] = useState('')
  const [site, setSite] = useState('unknown')
  const [result, setResult] = useState<ClassificationResult | null>(null)
  const [analysisImage,setAnalysisImage]=useState<Blob | undefined>()
  const [reportImageSnapshot,setReportImageSnapshot]=useState<string | null>(null)
  const [assistantCase, setAssistantCase] = useState<ClassificationResult | null>(null)
  const [assistantRestoring, setAssistantRestoring] = useState(false)
  const [assistantRestoreError, setAssistantRestoreError] = useState('')
  const [restoreAttempt, setRestoreAttempt] = useState(0)
  const assistantRestore = useRef<AbortController | null>(null)
  const inputVersion = useRef(0)
  const [tool, setTool] = useState<'rectangle' | 'freehand'>('rectangle')
  const [region, setRegion] = useState<Region | null>(null)
  const [history, setHistory] = useState<(Region | null)[]>([])
  const [zoom, setZoom] = useState(1)
  const [view, setView] = useState<'original' | 'input'>('original')
  useEffect(() => { setRegion(null); setHistory([]); setZoom(1); setView('original') }, [source.image])
  const previousInput = useRef([source.image, region, patientName, patientId, age, sex, site])
  useEffect(() => {
    const next = [source.image, region, patientName, patientId, age, sex, site]
    if (next.every((value, index) => value === previousInput.current[index])) return
    previousInput.current = next
    inputVersion.current++
    assistantRestore.current?.abort()
    setAssistantCase(null); setAssistantRestoreError(''); setAssistantRestoring(false); setResult(null); setAnalysisImage(undefined); setReportImageSnapshot(null)
    forgetAssistantCase()
  }, [source.image, region, patientName, patientId, age, sex, site])
  useEffect(() => {
    if (!result) return
    inputVersion.current++
    assistantRestore.current?.abort(); setAssistantRestoring(false)
    setAssistantCase(result); setAssistantRestoreError(''); rememberAssistantCase(result)
  }, [result])
  useEffect(() => {
    const controller = new AbortController(), version = inputVersion.current
    assistantRestore.current = controller
    setAssistantRestoring(true); setAssistantRestoreError('')
    restoreAssistantCase(controller.signal).then(saved => {
      if (!controller.signal.aborted && version === inputVersion.current) setAssistantCase(saved)
    }).catch(() => {
      if (!controller.signal.aborted) setAssistantRestoreError('The saved conversation could not be restored. Please retry.')
    }).finally(() => { if (!controller.signal.aborted) setAssistantRestoring(false) })
    return () => controller.abort()
  }, [restoreAttempt])
  return { ...source, assistantCase, assistantRestoring, assistantRestoreError, retryAssistantRestore: () => setRestoreAttempt(value => value + 1), patientName, setPatientName, patientId, setPatientId, age, setAge, sex, setSex, site, setSite, result, setResult, analysisImage, setAnalysisImage, reportImageSnapshot, setReportImageSnapshot, tool, setTool, region, setRegion, history, setHistory, zoom, setZoom, view, setView }
}

const AnalysisSessionContext = createContext<ReturnType<typeof useSessionState> | null>(null)
export function AnalysisSessionProvider({ children }: { children: ReactNode }) {
  const session = useSessionState()
  return <AnalysisSessionContext.Provider value={session}>{children}</AnalysisSessionContext.Provider>
}
export function useAnalysisSession() {
  const session = useContext(AnalysisSessionContext)
  if (!session) throw new Error('AnalysisSessionProvider is required.')
  return session
}
