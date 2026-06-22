import { useState } from 'react'
import TabSummary from '../components/VoiceAnalysis/TabSummary'
import TabScript from '../components/VoiceAnalysis/TabScript'
import TabKeyword from '../components/VoiceAnalysis/TabKeyword'
import TabTasks from '../components/VoiceAnalysis/TabTasks'
import TabSpeakers from '../components/VoiceAnalysis/TabSpeakers'

const TABS = ['요약', '전체 스크립트', '키워드', '액션 아이템'] as const
type Tab = typeof TABS[number]

interface SttSegment {
  speaker: string
  start: number
  end: number
  text: string
  user_edited: boolean
}

interface SttResult {
  file_id: string
  duration: number
  segments: SttSegment[]
  fileName: string
}

interface Props {
  fileId: string
  sttResult: SttResult | null
  onBack: () => void
}

const formatDuration = (seconds: number) => {
  const m = Math.floor(seconds / 60).toString().padStart(2, '0')
  const s = Math.floor(seconds % 60).toString().padStart(2, '0')
  return `${m}:${s}`
}

export default function VoiceAnalysis({ fileId, sttResult, onBack }: Props) {
  const [activeTab, setActiveTab] = useState<Tab>('요약')

  const fileName = sttResult?.fileName ?? fileId
  const duration = sttResult ? formatDuration(sttResult.duration) : '--:--'

return (
    <div className="flex-1 p-8 overflow-y-auto bg-white dark:bg-[#161616]">
      {/* 브레드크럼 */}
      <div className="flex items-center gap-2 text-xs text-gray-400 mb-4">
        <button onClick={onBack} className="hover:text-blue-500 transition-colors">음성 분석</button>
        <span>›</span>
        <span className="text-gray-600 dark:text-gray-300">분석 결과</span>
      </div>

      {/* 파일 헤더 */}
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="text-lg font-medium text-gray-900 dark:text-white">{fileName}</h1>
          <p className="text-xs text-gray-400 mt-1">
            {duration} · {sttResult?.segments.length ?? 0}개 발화 구간
          </p>
        </div>
        <div className="flex gap-2">
          <button className="flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400 border border-gray-200 dark:border-gray-700 px-3 py-1.5 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            원본 파일 다운로드
          </button>
          <button className="flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400 border border-gray-200 dark:border-gray-700 px-3 py-1.5 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
            </svg>
            공유
          </button>
        </div>
      </div>

      {/* 오디오 플레이어 */}
      <div className="bg-gray-50 dark:bg-[#1c1a1a] border border-gray-200 dark:border-gray-700 rounded-xl px-5 py-3 flex items-center gap-4 mb-5">
        <button className="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center flex-shrink-0">
          <svg className="w-4 h-4 text-white ml-0.5" fill="currentColor" viewBox="0 0 24 24">
            <path d="M8 5v14l11-7z" />
          </svg>
        </button>
        <span className="text-xs text-gray-500 dark:text-gray-400 w-24 flex-shrink-0">00:00 / {duration}</span>
        <div className="flex-1 bg-gray-200 dark:bg-gray-700 rounded-full h-1">
          <div className="bg-blue-500 h-1 rounded-full w-0" />
        </div>
        <span className="text-xs text-gray-400 flex-shrink-0">1.0x</span>
      </div>

      {/* 탭 바 */}
      <div className="flex gap-1 mb-4 border-b border-gray-100 dark:border-gray-700">
        {TABS.map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 text-sm transition-colors border-b-2 -mb-px ${
              activeTab === tab
                ? 'text-blue-500 border-blue-500 font-medium'
                : 'text-gray-500 dark:text-gray-400 border-transparent hover:text-gray-700 dark:hover:text-gray-300'
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* 탭 콘텐츠 */}
      {activeTab === '요약' && (
        <div className="flex gap-6">
          <div className="flex-1 min-w-0">
            <TabSummary duration={duration} segmentCount={sttResult?.segments.length ?? 0} />
          </div>
          <div className="w-52 flex-shrink-0">
            <TabSpeakers segments={sttResult?.segments ?? []} />
          </div>
        </div>
      )}
      {activeTab === '전체 스크립트' && <TabScript segments={sttResult?.segments ?? []} />}
      {activeTab === '키워드' && <TabKeyword />}
      {activeTab === '액션 아이템' && <TabTasks />}
    </div>
  )
}