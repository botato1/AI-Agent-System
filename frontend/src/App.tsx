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

  const [docViewMode, setDocViewMode] = useState<'list' | 'original' | 'analysis'>('list')
  const [selectedDocId, setSelectedDocId] = useState<number | null>(null)



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
        onFileUploaded={(filename) => {
          console.log('파일명 세팅:',filename)
          setTargetFilename(filename)
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
        onReview={() => {
          setReviewFileName('마케팅 전략 회의.pdf')
          setActivePage('home')
          setTimeout(() => setActivePage('pipeline'), 0)
        }}
        onGoToChat={() => {
          setActiveRoomId(targetRoomId)
          setActivePage('home')
        }}
        onBack={()=>setActivePage('pipeline')}
      />
    )
      case 'tasks': return <Tasks />
      case 'settings': return <Settings />
      case 'graph': return <Graph onGoToAnalysis={() => setActivePage('documentanalysis')} />
      case 'voice' : return voicePage === 'result'
        ?<VoiceAnalysis
            fileId={selectedVoiceId!}
            onBack={() => setVoicePage('list')}
          />
        : <Voice
            onAnalyze={(id) => {
              setSelectedVoiceId(id)
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
          <div className={`fixed top-6 left-1/2 -translate-x-1/2 flex items-center gap-3 px-5 py-3 rounded-2xl shadow-lg text-sm font-medium z-50 transition-all ${
            toast.type === 'success' ? 'bg-[#D8F0DA]/90 text-gray-700' :
            toast.type === 'error' ? 'bg-red-500/90 text-white' :
            'bg-blue-500/70 text-white'
          }`}>
            {toast.type === 'success' && (
              <div className="w-6 h-6 rounded-full bg-green-500 flex items-center justify-center flex-shrink-0">
                <span className="text-white text-xs">✓</span>
              </div>
            )}
            {toast.type === 'error' && (
              <div className="w-6 h-6 rounded-full bg-red-600 flex items-center justify-center flex-shrink-0">
                <span className="text-white text-xs">✕</span>
              </div>
            )}
            {toast.type === 'info' && (
              <div className="w-6 h-6 rounded-full bg-blue-600 flex items-center justify-center flex-shrink-0">
                <span className="text-white text-xs">ℹ</span>
              </div>
            )}
            {toast.message}
          </div>
        )}
      </div>
    </ToastContext.Provider>
  )
}