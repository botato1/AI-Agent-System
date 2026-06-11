import { useState } from 'react'

import { Upload } from 'lucide-react'

import type { FileItem } from '../data/documentsData'
import { files } from '../data/documentsData'
import { voices } from '../data/voiceData'

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

export default function Documents({ selectedDocId, docViewMode, onNameClick, onAnalysisClick, onBack }: Props) {
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
      <div className="flex items-center justify-between mb-5">
        <h1 className="text-lg font-bold text-gray-800">문서 보관함</h1>
        <button className="flex items-center gap-1.5 text-xs text-white bg-blue-600 px-3 py-2 rounded-lg hover:bg-blue-700">
          <Upload size={13} /> 업로드
        </button>
      </div>

      <div className="flex gap-1 mb-5 border-b border-gray-100">
        {tabs.map((tab, i) => (
          <button
            key={i}
            onClick={() => setActiveTab(i)}
            className={`text-sm px-4 py-2 border-b-2 transition ${
              activeTab === i
                ? 'border-blue-600 text-blue-600 font-medium'
                : 'border-transparent text-gray-400 hover:text-gray-600'
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {activeTab === 0 && (
        <DocumentTab
          onNameClick={onNameClick}
          onAnalysisClick={onAnalysisClick}
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