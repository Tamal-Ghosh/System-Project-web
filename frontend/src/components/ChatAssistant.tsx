import React, { useState, useRef, useEffect } from 'react'
import { Send, User, Bot, BookOpen, X } from 'lucide-react'
import { sendChatMessage } from '../api'
import type { AnalysisResult, ChatMessage } from '../types'

interface Props {
  analysis: AnalysisResult | null
  onClearAnalysis: () => void
}

export function ChatAssistant({ analysis, onClearAnalysis }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content:
        'Hello Doctor. I am your clinical research assistant. Upload a lesion image on the left to analyze, or ask questions regarding dermatoscopy criteria, uncertainty, or ResNet50 classification.',
      created_at: new Date().toISOString(),
    },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // When a new analysis arrives, add a contextual notification
  useEffect(() => {
    if (analysis) {
      const topPct = (analysis.probabilities[0]?.probability * 100).toFixed(1) + '%'
      const hasRoi = analysis.annotated
      const segText = analysis.segmentation_requested
        ? ' Segmentation was performed.'
        : ' Segmentation was not requested.'

      setMessages((prev) => [
        ...prev,
        {
          id: 'analysis-' + analysis.analysis_id,
          role: 'assistant',
          content: `I've received the analysis for ${hasRoi ? 'the **annotated lesion ROI**' : 'this lesion'}. ResNet50 predicted **${analysis.predicted_class_display}** with **${topPct}** confidence.${segText}\n\nYou can ask me why the model made this prediction, what the uncertainty score indicates, or explore the Grad-CAM features.`,
          created_at: new Date().toISOString(),
        },
      ])
    }
  }, [analysis])

  const handleSend = async (textToSend?: string) => {
    const text = (textToSend || input).trim()
    if (!text || loading) return

    const userMsg: ChatMessage = {
      id: 'usr-' + Date.now(),
      role: 'user',
      content: text,
      created_at: new Date().toISOString(),
    }

    const loadingMsg: ChatMessage = {
      id: 'load-' + Date.now(),
      role: 'assistant',
      content: '',
      created_at: new Date().toISOString(),
      is_loading: true,
    }

    setMessages((prev) => [...prev, userMsg, loadingMsg])
    setInput('')
    setLoading(true)

    try {
      const res = await sendChatMessage(text, undefined, analysis?.analysis_id)
      setMessages((prev) =>
        prev.map((m) =>
          m.id === loadingMsg.id
            ? {
                ...m,
                content: res.content,
                sources: res.sources,
                tool_used: res.tool_used,
                is_loading: false,
              }
            : m
        )
      )
    } catch (e: any) {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === loadingMsg.id
            ? {
                ...m,
                content: 'Failed to retrieve response from backend API. Please check server.',
                is_loading: false,
                is_error: true,
              }
            : m
        )
      )
    } finally {
      setLoading(false)
    }
  }

  const handleKey = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const prompts = analysis
    ? [
        'Why did the model predict this class?',
        'What does the uncertainty score mean?',
        'Explain the Grad-CAM regions for this lesion',
        'Explain the SHAP attributions for this lesion',
        'What clinical limitations should I consider?',
      ]
    : [
        'How does ResNet50 classify skin lesions?',
        'What does model calibration (ECE) mean?',
        'What is the difference between Grad-CAM and SHAP?',
        'Explain the ABCDE criteria in dermatoscopy',
      ]

  return (
    <div className="rounded-2xl border border-slate-200 bg-white shadow-xs overflow-hidden flex flex-col h-[700px]">
      {/* Header */}
      <div className="px-5 py-4 border-b border-slate-100 bg-slate-50/60 flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="font-semibold text-slate-900 text-sm">AI Decision-Support Chatbot</h3>
            <span className="w-2 h-2 rounded-full bg-teal-500 animate-pulse" title="Connected to FastAPI" />
          </div>
          <p className="text-xs text-slate-400 mt-0.5">Clinical Q&amp;A grounded in model outputs &amp; ISIC research</p>
        </div>
        <span className="text-[11px] px-2 py-0.5 bg-teal-50 text-teal-700 font-medium rounded-full border border-teal-200">
          FastAPI Agent
        </span>
      </div>

      {/* Active Analysis Context Banner */}
      {analysis && (
        <div className="px-4 py-2.5 bg-teal-50/80 border-b border-teal-100 flex items-center justify-between gap-2 text-xs">
          <div className="flex items-center gap-2 text-teal-900 truncate">
            <span className="font-semibold text-teal-800">Linked to:</span>
            <span className="truncate">
              <strong>{analysis.predicted_class_display}</strong> (
              {(analysis.probabilities[0]?.probability * 100).toFixed(0)}%)
            </span>
          </div>
          <button
            type="button"
            onClick={onClearAnalysis}
            className="text-teal-600 hover:text-teal-800 font-medium transition flex items-center gap-1 flex-shrink-0 cursor-pointer"
            title="Unlink active analysis context"
          >
            <X className="w-3.5 h-3.5" /> Unlink
          </button>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg) => {
          const isUser = msg.role === 'user'
          return (
            <div key={msg.id} className={`flex gap-3 ${isUser ? 'flex-row-reverse' : ''}`}>
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                  isUser ? 'bg-teal-100 text-teal-700' : 'bg-slate-100 text-slate-600'
                }`}
              >
                {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
              </div>

              <div className={`flex flex-col gap-1 max-w-[82%] ${isUser ? 'items-end' : 'items-start'}`}>
                <div
                  className={`px-4 py-3 rounded-2xl text-xs sm:text-sm leading-relaxed whitespace-pre-wrap ${
                    isUser
                      ? 'bg-teal-600 text-white rounded-tr-xs shadow-xs'
                      : msg.is_error
                      ? 'bg-red-50 text-red-700 border border-red-200 rounded-tl-xs'
                      : 'bg-slate-50 text-slate-800 border border-slate-200/80 rounded-tl-xs shadow-xs'
                  }`}
                >
                  {msg.is_loading ? (
                    <span className="flex gap-1.5 items-center py-1">
                      {[0, 1, 2].map((i) => (
                        <span
                          key={i}
                          className="w-2 h-2 bg-slate-400 rounded-full animate-bounce"
                          style={{ animationDelay: `${i * 0.15}s` }}
                        />
                      ))}
                    </span>
                  ) : (
                    msg.content
                  )}
                </div>

                {/* Sources / Citations */}
                {msg.sources && msg.sources.length > 0 && (
                  <div className="space-y-1 w-full mt-1">
                    {msg.sources.map((src) => (
                      <div
                        key={src.id}
                        className="px-3 py-2 bg-blue-50 border border-blue-100 rounded-xl text-xs text-blue-900"
                      >
                        <div className="flex items-start gap-1.5">
                          <BookOpen className="w-3.5 h-3.5 text-blue-600 flex-shrink-0 mt-0.5" />
                          <div className="flex-1">
                            <p className="font-semibold text-blue-800">{src.title}</p>
                            {src.page_or_section && (
                              <p className="text-[11px] text-blue-600">{src.page_or_section}</p>
                            )}
                            {src.excerpt && (
                              <p className="text-[11px] text-blue-700 mt-0.5 italic">"{src.excerpt}"</p>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )
        })}
        <div ref={bottomRef} />
      </div>

      {/* Suggested Prompt Chips */}
      <div className="px-4 py-2 border-t border-slate-100 bg-slate-50/40 flex flex-wrap gap-1.5">
        {prompts.map((p) => (
          <button
            key={p}
            type="button"
            onClick={() => handleSend(p)}
            className="px-2.5 py-1 text-xs bg-white border border-slate-200 text-slate-600 rounded-full hover:border-teal-400 hover:text-teal-700 hover:bg-teal-50 transition cursor-pointer"
          >
            {p}
          </button>
        ))}
      </div>

      {/* Input */}
      <div className="p-3 border-t border-slate-200 bg-white">
        <div className="flex gap-2 bg-slate-50 rounded-xl border border-slate-200 p-2 focus-within:border-teal-400 focus-within:ring-2 focus-within:ring-teal-100 transition">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKey}
            placeholder={
              analysis
                ? 'Ask about this prediction, uncertainty, Grad-CAM...'
                : 'Ask a research question or upload an image to analyze...'
            }
            rows={2}
            disabled={loading}
            className="flex-1 text-xs sm:text-sm text-slate-800 placeholder-slate-400 outline-none resize-none bg-transparent leading-relaxed"
          />
          <button
            type="button"
            onClick={() => handleSend()}
            disabled={!input.trim() || loading}
            className="self-end flex items-center justify-center w-8 h-8 sm:w-9 sm:h-9 bg-teal-600 hover:bg-teal-700 text-white rounded-lg transition disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
        <p className="text-[10px] text-slate-400 text-center mt-2">
          Clinical decision-support assistant. Requires clinician review. Not for autonomous diagnosis.
        </p>
      </div>
    </div>
  )
}
