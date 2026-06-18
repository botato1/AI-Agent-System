import { useState } from 'react'
import { files } from '../data/documentsData'
import DocumentTab from '../components/Documents/DocumentTab'
import VoiceTab from '../components/Documents/VoiceTab'
import DocumentOriginal from '../components/Documents/DocumentOriginal'
import DocumentAnalysis from '../components/Documents/DocumentAnalysis'

type Props = {
  selectedDocId: number | null
  docViewMode: 'list' | 'original' | 'analysis'
  onNameClick: (id: number) => void
  onAnalysisClick: (id: number) => void
  onBack: () => void
}

const tabs = ['문서', '음성']

export default function Documents({ selectedDocId, docViewMode, onBack }: Props) {
  const [activeTab, setActiveTab] = useState(0)

  const selectedDoc = files.find(f => f.id === selectedDocId) ?? null

  if (docViewMode === 'original' && selectedDoc) {
    return <DocumentOriginal file={selectedDoc} onBack={onBack} />
  }
  if (docViewMode === 'analysis' && selectedDoc) {
    return <DocumentAnalysis file={selectedDoc} onBack={onBack} />
  }

  return (
    <div>
      <div className="flex gap-1 mb-5 border-b border-gray-100 dark:border-gray-700">
        {tabs.map((tab, i) => (
          <button
            key={i}
            onClick={() => setActiveTab(i)}
            className={`text-sm px-4 py-2 border-b-2 transition ${
              activeTab === i
                ? 'border-blue-600 text-blue-600 font-medium'
                : 'border-transparent text-gray-400 hover:text-gray-600 dark:hover:text-gray-300'
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {activeTab === 0 && (
        <DocumentTab
        />
      )}
      {activeTab === 1 && (
        <VoiceTab
          onNameClick={(id) => console.log('음성 원본:', id)}
          onAnalysisClick={(id) => console.log('음성 분석:', id)}
        />
      )}
    </div>
  )
}