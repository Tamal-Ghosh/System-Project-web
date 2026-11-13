import { createContext, useContext, useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { useLocalImage } from './image/useLocalImage'
import type { Region } from './image/geometry'

function useSessionState() {
  const source = useLocalImage()
  const [tool, setTool] = useState<'rectangle' | 'freehand'>('rectangle')
  const [region, setRegion] = useState<Region | null>(null)
  const [history, setHistory] = useState<(Region | null)[]>([])
  const [zoom, setZoom] = useState(1)
  const [view, setView] = useState<'original' | 'input'>('original')
  useEffect(() => { setRegion(null); setHistory([]); setZoom(1); setView('original') }, [source.image])
  return { ...source, tool, setTool, region, setRegion, history, setHistory, zoom, setZoom, view, setView }
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
