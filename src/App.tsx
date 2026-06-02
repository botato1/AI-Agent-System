import { useState, useEffect, createContext, useContext } from 'react'
import Sidebar from './components/layout/Sidebar'
import Home from './pages/Home'
import Analysis from './pages/Analysis'
import Tasks from './pages/Tasks'
import Settings from './pages/Settings'
import Pipeline from './pages/Pipeline'
import Graph from './pages/Graph'
import Documents from './pages/Documents'
import VoiceAnalysis from './pages/VoiceAnalysis'

type ToastType = 'success' | 'error' | 'info'

interface ToastContextType {
  showToast: (message: string, type?: ToastType) => void
}

export const ToastContext = createContext<ToastContextType>({ showToast: () => {} })
export const useToast = () => useContext(ToastContext)

export default function App() {
  const [activePage, setActivePage] = useState('home')
  const [isDark, setIsDark] = useState(false)
  const [toast, setToast] = useState<{ message: string; type: ToastType } | null>(null)
  const [selectedChatId, setSelectedChatId] = useState<number | null>(null)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [selectedDocId, setSelectedDocId] = useState<number | null>(null)
  const [docViewMode, setDocViewMode] = useState<'list' | 'original' | 'analysis'>('list')
  const [reviewFileName, setReviewFileName] = useState<string | null>(null)
  const [selectedVoiceId, setSelectedVoiceId] = useState<number | null>(null)
  const [voiceViewMode, setVoiceViewMode] = useState<'list' | 'original' | 'analysis'>('list')
  


  useEffect(() => {
    if (isDark) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }, [isDark])

  const showToast = (message: string, type: ToastType = 'info') => {
    setToast({ message, type })
    setTimeout(() => setToast(null), 2500)
  }

  const renderPage = () => {
    switch (activePage) {
      case 'home': return <Home selectedChatId={selectedChatId} />
      case 'pipeline': return (
  <Pipeline
    onGoToAnalysis={() => setActivePage('analysis')}
    reviewFileName={reviewFileName}
    onClearReview={() => setReviewFileName(null)}
  />
)
case 'analysis': return (
  <Analysis onReview={() => {
    setReviewFileName('마케팅 전략 회의.pdf')
    setActivePage('home') // 일단 home으로 갔다가
    setTimeout(() => setActivePage('pipeline'), 0) // 바로 pipeline으로
  }} />
)
      case 'tasks': return <Tasks />
      case 'settings': return <Settings />
      case 'graph': return <Graph />
      case 'documents': return (
  <Documents
    selectedDocId={selectedDocId}
    docViewMode={docViewMode}
    onNameClick={(id) => { setSelectedDocId(id); setDocViewMode('original') }}
    onAnalysisClick={(id) => { setSelectedDocId(id); setDocViewMode('analysis') }}
    onBack={() => { setSelectedDocId(null); setDocViewMode('list') }}
  />
)
case 'voice': return (
  <VoiceAnalysis onReview={() => setActivePage('voice')} />
)

      default: return (
        <div className="flex items-center justify-center h-full">
          <p className="text-gray-400 text-sm">준비 중인 페이지예요 😊</p>
        </div>
     
    )
    }
  }

  return (
    <ToastContext.Provider value={{ showToast }}>
      <div className="bg-gray-50 dark:bg-[#1c1a1a] min-h-screen flex transition-colors duration-300">
        <Sidebar
          activePage={activePage}
          onPageChange={setActivePage}
          isDark={isDark}
          onToggleDark={() => setIsDark(!isDark)}
          onChatSelect={(id) => {
            setSelectedChatId(id)
            setActivePage('home')
          }}
          onCollapse={(v) => setSidebarCollapsed(v)}
        />
        <main className={`${sidebarCollapsed ? 'ml-14' : 'ml-52'} flex-1 p-6 transition-all duration-300`}>
          {renderPage()}
        </main>

        {toast && (
          <div className={`fixed top-6 left-1/2 -translate-x-1/2 flex items-center gap-2 px-5 py-3 rounded-xl shadow-lg text-sm font-medium z-50 transition-all ${
            toast.type === 'success' ? 'bg-gray-800 text-white' :
            toast.type === 'error' ? 'bg-red-500 text-white' :
            'bg-blue-500 text-white'
          }`}>
            {toast.type === 'success' && <span>✓</span>}
            {toast.type === 'error' && <span>✕</span>}
            {toast.type === 'info' && <span>ℹ</span>}
            {toast.message}
          </div>
        )}
      </div>
    </ToastContext.Provider>
  )
}