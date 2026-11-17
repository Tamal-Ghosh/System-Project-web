import { createContext, useContext, useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { useLocalImage } from './image/useLocalImage'
import type { ClassificationResult } from '../../services/classification'
import type { Region } from './image/geometry'

function useSessionState() {
  const source = useLocalImage()
  const [patientId, setPatientId] = useState('')
  const [age, setAge] = useState('')
  const [sex, setSex] = useState('')
  const [site, setSite] = useState('unknown')
  const [result, setResult] = useState<ClassificationResult | null>(null)
  const [tool, setTool] = useState<'rectangle' | 'freehand'>('rectangle')
  const [region, setRegion] = useState<Region | null>(null)
  const [history, setHistory] = useState<(Region | null)[]>([])
  const [zoom, setZoom] = useState(1)
  const [view, setView] = useState<'original' | 'input'>('original')
  useEffect(() => { setRegion(null); setHistory([]); setZoom(1); setView('original') }, [source.image])
  return { ...source, patientId, setPatientId, age, setAge, sex, setSex, site, setSite, result, setResult, tool, setTool, region, setRegion, history, setHistory, zoom, setZoom, view, setView }
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
