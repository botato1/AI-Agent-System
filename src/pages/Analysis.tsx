import { Document, Packer, Paragraph, TextRun, HeadingLevel } from 'docx'
import { saveAs } from 'file-saver'
import { NanumGothicBase64 } from '../fonts/NanumGothic'
import { useToast } from '../App'
import { useState } from 'react'
import { ArrowLeft, Download, Share2 } from 'lucide-react'
import jsPDF from 'jspdf'
import TabSummary from '../components/Analysis/TabSummary'
import TabOriginal from '../components/Analysis/TabOriginal'
import ConfidenceBar from '../components/Analysis/ConfidenceBar'
import TabTasks from '../components/Analysis/TabTasks'
import TabRelated from '../components/Analysis/TabRelated'

const tabs = ['요약', '전체 문서', 'Task', '연관 문서']

interface AnalysisProps {
  onReview: () => void
}

export default function Analysis({ onReview }: AnalysisProps) {
  const { showToast } = useToast()
  const [activeTab, setActiveTab] = useState(0)

  const handleDownload = () => {
    const doc = new jsPDF()
    doc.addFileToVFS('NanumGothic.ttf', NanumGothicBase64)
    doc.addFont('NanumGothic.ttf', 'NanumGothic', 'normal')
    doc.setFont('NanumGothic')
    doc.setFontSize(18)
    doc.text('마케팅 전략 회의 분석 보고서', 20, 20)
    doc.setFontSize(11)
    doc.text('회의 일시: 2024.05.20 (월) 14:00', 20, 35)
    doc.text('회의 시간: 1시간 32분', 20, 43)
    doc.save('마케팅전략회의_분석보고서.pdf')
  }

  const handleDownloadDocx = async () => {
    const doc = new Document({
      sections: [{
        children: [
          new Paragraph({ text: '마케팅 전략 회의 분석 보고서', heading: HeadingLevel.HEADING_1 }),
          new Paragraph({ children: [new TextRun({ text: '회의 일시: 2024.05.20 (월) 14:00', size: 22 })] }),
        ]
      }]
    })
    const blob = await Packer.toBlob(doc)
    saveAs(blob, '마케팅전략회의_분석보고서.docx')
  }

  const handleDownloadTxt = () => {
    const content = `마케팅 전략 회의 분석 보고서\n회의 일시: 2024.05.20 (월) 14:00`
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
    saveAs(blob, '마케팅전략회의_분석보고서.txt')
  }

  const handleShare = () => {
    navigator.clipboard.writeText(window.location.href)
    showToast('링크가 복사됐어요')
  }

const renderTab = () => {
  switch (activeTab) {
    case 0: return <TabSummary />
    case 1: return <TabOriginal />
    case 2: return <TabTasks />
    case 3: return <TabRelated />
    default: return <TabSummary />
  }
}

  return (
    <div id="analysis-content">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <button className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700">
            <ArrowLeft size={16} className="text-gray-500 dark:text-gray-400" />
          </button>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-bold text-gray-800 dark:text-white">마케팅 전략 회의</h1>
              <span className="text-xs bg-blue-100 dark:bg-blue-900 text-blue-600 dark:text-blue-300 px-2 py-0.5 rounded-full font-medium">분석 완료</span>
            </div>
            <p className="text-xs text-gray-400 mt-0.5">2024.05.20 (월) 14:00 · 회의 시간 1hr 32m</p>
          </div>
        </div>
        <div className="flex gap-2">
          <button onClick={handleDownload} className="flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400 border border-gray-200 dark:border-gray-600 px-3 py-1.5 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700">
            <Download size={13} /> PDF
          </button>
          <button onClick={handleDownloadDocx} className="flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400 border border-gray-200 dark:border-gray-600 px-3 py-1.5 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700">
            <Download size={13} /> DOCX
          </button>
          <button onClick={handleDownloadTxt} className="flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400 border border-gray-200 dark:border-gray-600 px-3 py-1.5 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700">
            <Download size={13} /> TXT
          </button>
          <button onClick={handleShare} className="flex items-center gap-1.5 text-xs text-white bg-blue-600 px-3 py-1.5 rounded-lg hover:bg-blue-700">
            <Share2 size={13} /> 공유하기
          </button>
        </div>
      </div>

      <ConfidenceBar confidence={72} onReview={onReview} />

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