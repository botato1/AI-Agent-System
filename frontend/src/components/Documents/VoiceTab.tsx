import { useState } from 'react'
import { Search, Grid, List, Mic } from 'lucide-react'
import { voices, FILTERS } from '../../data/voiceData'

type Props = {
  onNameClick: (id: number) => void
  onAnalysisClick: (id: number) => void
}

const typeColors: Record<string, string> = {
  WAV: 'bg-blue-100 text-blue-500',
  MP3: 'bg-purple-100 text-purple-500',
  M4A: 'bg-green-100 text-green-500',
}

export default function VoiceTab({ onNameClick, onAnalysisClick }: Props) {
  const [search, setSearch] = useState('')
  const [viewMode, setViewMode] = useState<'list' | 'grid'>('list')
  const [filter, setFilter] = useState('전체')

  const filtered = voices.filter((v) => {
    const matchSearch = v.name.toLowerCase().includes(search.toLowerCase())
    const matchFilter = filter === '전체' || v.type === filter
    return matchSearch && matchFilter
  })

  return (
    <div>
      <div className="flex items-center gap-3 mb-5">
        <div className="flex-1 flex items-center gap-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-lg px-3 py-2">
          <Search size={14} className="text-gray-300" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="파일 검색..."
            className="flex-1 text-sm text-gray-700 dark:text-gray-200 outline-none placeholder-gray-500 bg-transparent"
          />
        </div>

        <div className="flex gap-1">
          {FILTERS.map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`text-xs px-3 py-1.5 rounded-lg border transition ${
                filter === f
                  ? 'bg-blue-600 text-white border-blue-600'
                  : 'bg-white dark:bg-gray-800 text-gray-400 dark:text-gray-500 border-gray-200 dark:border-gray-600 hover:border-blue-300'
              }`}
            >
              {f}
            </button>
          ))}
        </div>

        <div className="flex bg-gray-100 dark:bg-gray-700 rounded-lg p-0.5">
          <button
            onClick={() => setViewMode('list')}
            className={`p-1.5 rounded-md transition ${viewMode === 'list' ? 'bg-white dark:bg-gray-600 shadow-sm' : ''}`}
          >
            <List size={14} className={viewMode === 'list' ? 'text-gray-700 dark:text-gray-200' : 'text-gray-400'} />
          </button>
          <button
            onClick={() => setViewMode('grid')}
            className={`p-1.5 rounded-md transition ${viewMode === 'grid' ? 'bg-white dark:bg-gray-600 shadow-sm' : ''}`}
          >
            <Grid size={14} className={viewMode === 'grid' ? 'text-gray-700 dark:text-gray-200' : 'text-gray-400'} />
          </button>
        </div>
      </div>

      {viewMode === 'list' && (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 overflow-hidden">
          <div className="grid grid-cols-12 px-4 py-2 border-b border-gray-100 dark:border-gray-700 bg-gray-50 dark:bg-gray-700">
            <span className="col-span-4 text-xs text-gray-400 dark:text-gray-500 font-medium">이름</span>
            <span className="col-span-2 text-xs text-gray-400 dark:text-gray-500 font-medium">유형</span>
            <span className="col-span-2 text-xs text-gray-400 dark:text-gray-500 font-medium">업로드 날짜</span>
            <span className="col-span-2 text-xs text-gray-400 dark:text-gray-500 font-medium">크기</span>
            <span className="col-span-1 text-xs text-gray-400 dark:text-gray-500 font-medium">길이</span>
            <span className="col-span-1 text-xs text-gray-400 dark:text-gray-500 font-medium">분석</span>
          </div>
          {filtered.map((voice) => (
            <div key={voice.id} className="grid grid-cols-12 px-4 py-3 border-b border-gray-50 dark:border-gray-700 last:border-0 hover:bg-gray-50 dark:hover:bg-gray-700 transition items-center">
              <div className="col-span-4 flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg flex items-center justify-center border border-blue-300 dark:border-blue-800 text-blue-400 dark:text-blue-700">
                  <Mic size={16} />
                </div>
                <button
                  onClick={() => onNameClick(voice.id)}
                  className="text-sm text-gray-700 dark:text-gray-200 truncate hover:text-blue-600 hover:underline text-left"
                >
                  {voice.name}
                </button>
              </div>
              <div className="col-span-2">
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${typeColors[voice.type]}`}>
                  {voice.type}
                </span>
              </div>
              <span className="col-span-2 text-xs text-gray-400 dark:text-gray-500">{voice.date}</span>
              <span className="col-span-2 text-xs text-gray-400 dark:text-gray-500">{voice.size}</span>
              <span className="col-span-1 text-xs text-gray-400 dark:text-gray-500">{voice.duration}</span>
              <div className="col-span-1">
                <button
                  onClick={() => onAnalysisClick(voice.id)}
                  className="text-xs text-blue-500 hover:underline"
                >
                  분석
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {viewMode === 'grid' && (
        <div className="grid grid-cols-3 gap-4">
          {filtered.map((voice) => (
            <div key={voice.id} className="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 p-4 hover:border-blue-200 dark:hover:border-blue-700 transition">
              <div className="w-10 h-10 rounded-xl flex items-center justify-center mb-3 border border-blue-300 dark:border-blue-800 text-blue-400 dark:text-blue-700">
                <Mic size={18} />
              </div>
              <button
                onClick={() => onNameClick(voice.id)}
                className="text-sm font-medium text-gray-700 dark:text-gray-200 truncate mb-1 w-full text-left hover:text-blue-600 hover:underline"
              >
                {voice.name}
              </button>
              <div className="flex items-center justify-between mt-1">
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${typeColors[voice.type]}`}>
                  {voice.type}
                </span>
                <span className="text-xs text-gray-400 dark:text-gray-500">{voice.duration}</span>
              </div>
              <div className="flex items-center justify-between mt-2">
                <p className="text-xs text-gray-300 dark:text-gray-600">{voice.date}</p>
                <button
                  onClick={() => onAnalysisClick(voice.id)}
                  className="text-xs text-blue-500 hover:underline"
                >
                  분석
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}