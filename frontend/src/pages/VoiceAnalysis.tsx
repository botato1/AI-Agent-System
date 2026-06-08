import { useState } from 'react'
import { Download, Share2 } from 'lucide-react'
import { useToast } from '../App'
import TabSummary from '../components/Voice/TabSummary'
import TabScript from '../components/Voice/TabScript'
import TabTasks from '../components/Voice/TabTasks'
import TabSpeakers from '../components/Voice/TabSpeakers'
import ConfidenceBar from '../components/Analysis/ConfidenceBar'

const tabs = ['요약', '스크립트', 'Task', '발언자']

interface VoiceAnalysisProps {
  onReview: () => void
}

export default function VoiceAnalysis({ onReview }: VoiceAnalysisProps) {
  const { showToast } = useToast()
  const [activeTab, setActiveTab] = useState(0)

  const handleShare = () => {
    navigator.clipboard.writeText(window.location.href)
    showToast('링크가 복사됐어요')
  }

  const renderTab = () => {
    switch (activeTab) {
      case 0: return <TabSummary />
      case 1: return <TabScript />
      case 2: return <TabTasks />
      case 3: return <TabSpeakers />
      default: return <TabSummary />
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-lg font-bold text-gray-800 dark:text-white">마케팅 전략 회의</h1>
            <span className="text-xs bg-blue-100 dark:bg-blue-900 text-blue-600 dark:text-blue-300 px-2 py-0.5 rounded-full font-medium">분석 완료</span>
          </div>
          <p className="text-xs text-gray-400 mt-0.5">2024.05.20 (월) 14:00 · 42분 30초</p>
        </div>
        <div className="flex gap-2">
          <button className="flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400 border border-gray-200 dark:border-gray-600 px-3 py-1.5 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700">
            <Download size={13} /> TXT
          </button>
          <button onClick={handleShare} className="flex items-center gap-1.5 text-xs text-white bg-blue-600 px-3 py-1.5 rounded-lg hover:bg-blue-700">
            <Share2 size={13} /> 공유하기
          </button>
        </div>
      </div>

      <ConfidenceBar confidence={85} onReview={onReview} />

      <div className="flex gap-1 mb-6 border-b border-gray-100 dark:border-gray-700">
        {tabs.map((tab, i) => (
          <button
            key={i}
            onClick={() => setActiveTab(i)}
            className={`text-sm px-4 py-2 border-b-2 transition ${activeTab === i ? 'border-blue-600 text-blue-600 font-medium' : 'border-transparent text-gray-400 hover:text-gray-600 dark:hover:text-gray-300'}`}
          >
            {tab}
          </button>
        ))}
      </div>
      {renderTab()}
    </div>
  )
}