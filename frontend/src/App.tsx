import { useState, useEffect, createContext, useContext } from 'react'
import Sidebar from './components/layout/Sidebar'

import Home from './pages/Home'
import Documents from './pages/Documents'
import DocumentAnalysis from './pages/DocumentAnalysis'
import Tasks from './pages/Tasks'
import Settings from './pages/Settings'
import Pipeline from './pages/Pipeline'
import Graph from './pages/Graph'
import Voice from './pages/Voice'
import VoiceAnalysis from './pages/VoiceAnalysis'

type ToastType = 'success' | 'error' | 'info'
interface ToastContextType {
  showToast: (message: string, type?: ToastType) => void
}

interface SttResult {
  file_id: string
  duration: number
  segments: { speaker: string; start: number; end: number; text: string; user_edited: boolean }[]
  fileName: string
}

export const ToastContext = createContext<ToastContextType>({ showToast: () => {} })
export const useToast = () => useContext(ToastContext)

export default function App() {
  const [activePage, setActivePage] = useState('home')
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)

  const [isDark, setIsDark] = useState(false)

  const [toast, setToast] = useState<{ message: string; type: ToastType } | null>(null)

  const [selectedChatId, setSelectedChatId] = useState<number | null>(null)
  const [activeRoomId, setActiveRoomId] = useState<string | null>(null)
  const [targetRoomId, setTargetRoomId] = useState<string | null>(null)
  const [targetFilename, setTargetFilename] = useState<string | null>(null)

  const [reviewFileName, setReviewFileName] = useState<string | null>(null)
  const [sidebarRefreshKey, setSidebarRefreshKey] = useState(0)
  
  const [voicePage, setVoicePage] = useState<'list' | 'result'>('list')
  const [selectedVoiceId, setSelectedVoiceId] = useState<string | null>(null)
  const [sttResult, setSttResult] = useState<SttResult | null>(null)

  const [docViewMode, setDocViewMode] = useState<'list' | 'original' | 'analysis'>('list')
  const [selectedDocId, setSelectedDocId] = useState<number | null>(null)

  const [documentAnalysisData, setDocumentAnalysisData] = useState<any>(null)

  useEffect(() => {
    if (isDark) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }, [isDark])

  const showToast = (message: string, type: ToastType = 'info') => {
    setToast({ message, type })
    setTimeout(() => setToast(null), 1500)
  }

  const renderPage = () => {
  switch (activePage) {
    case 'home': return (
      <Home
        selectedChatId={selectedChatId}
        onRoomCreated={() => setSidebarRefreshKey(prev => prev + 1)}
        onSelectRoom={(room_id) => setActiveRoomId(room_id)}
        activeRoomId={activeRoomId}
        setActiveRoomId={setActiveRoomId}
        targetFilename={targetFilename}
        onGoToAnalysis={() => setActivePage('documentanalysis')}
      />
    )
    case 'pipeline': return (
      <Pipeline
        onGoToAnalysis={() => setActivePage('documentanalysis')}
        reviewFileName={reviewFileName}
        onClearReview={() => setReviewFileName(null)}
        onRoomCreated={() => setSidebarRefreshKey(prev => prev + 1)}
        onFileUploaded={(filename, analysisData) => {
          console.log('파일명 세팅:', filename)
          setTargetFilename(filename)
          setDocumentAnalysisData(analysisData)
      }}
        onRoomIdCreated={(roomId) => setTargetRoomId(roomId)}
      />
    )
    case 'documents': return (
      <Documents
        selectedDocId={selectedDocId}
        docViewMode={docViewMode}
        onNameClick={(id) => {
          setSelectedDocId(id)
          setDocViewMode('original')
        }}
        onAnalysisClick={(id) => {
          setSelectedDocId(id)
          setDocViewMode('analysis')
        }}
        onBack={() => setDocViewMode('list')}
      />
    )
    case 'documentanalysis': return (
      <DocumentAnalysis
        analysisData={documentAnalysisData}
        onReview={() => {
          setReviewFileName('마케팅 전략 회의.pdf')
          setActivePage('home')
          setTimeout(() => setActivePage('pipeline'), 0)
        }}
        onGoToChat={() => {
          setActiveRoomId(targetRoomId)
          setTargetFilename(targetFilename)
          setActivePage('home')
        }}
        onBack={() => setActivePage('pipeline')}
      />
    )
    case 'tasks': return <Tasks />
    case 'settings': return <Settings />
    case 'graph': return <Graph onGoToAnalysis={() => setActivePage('documentanalysis')} />
    case 'voice': return voicePage === 'result'
      ? <VoiceAnalysis
          fileId={selectedVoiceId!}
          sttResult={sttResult}
          onBack={() => setVoicePage('list')}
        />
      : <Voice
          onAnalyze={(id, result) => {
            setSelectedVoiceId(id)
            setSttResult(result)
            setVoicePage('result')
          }}
        />
  }
}

  return (
    <ToastContext.Provider value={{ showToast }}>
      <div className="bg-gray-50 dark:bg-[#1c1a1a] min-h-screen flex transition-colors duration-300">
        <Sidebar
        refreshKey={sidebarRefreshKey}
        activePage={activePage}
        onPageChange={setActivePage}
        isDark={isDark}
        onToggleDark={() => setIsDark(!isDark)}
        onChatSelect={(id) => {
          setSelectedChatId(id)
          setActivePage('home')
        }}
        onCollapse={(v) => setSidebarCollapsed(v)}
        onRoomSelect={(room_id, filename) => {
          setActiveRoomId(room_id)
          setTargetFilename(filename)
          setActivePage('home')
        }}
      />
        <main className={`${sidebarCollapsed ? 'ml-14' : 'ml-52'} flex-1 p-6 transition-all duration-300`}>
          {renderPage()}
        </main>

        {toast && (
        <div className={`fixed top-6 left-1/2 -translate-x-1/2 z-50 flex items-center gap-2 px-5 py-2.5 rounded-full text-sm font-medium border transition-all
          bg-[#f0faf4] dark:bg-[#2a2a2a] border-[#c8e6d0] dark:border-[#3a3a3a] text-gray-800 dark:text-white`}>
          {toast.type === 'success' && (
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#22c55e" strokeWidth="2.5">
            <polyline points="20 6 9 17 4 12"/>
            </svg>
          )}
          {toast.type === 'error' && (
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#ef4444" strokeWidth="2.5">
              <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          )}
          {toast.type === 'info' && (
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" strokeWidth="2.5">
              <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
          )}
          {toast.message}
        </div>
        )}
            </div>
          </ToastContext.Provider>
        )
      }