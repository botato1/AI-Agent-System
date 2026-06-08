import { useState } from 'react'
import { Search, Upload, Grid, List } from 'lucide-react'
import { files, FILTERS } from '../../data/documentsData'
import type { FileItem } from '../../data/documentsData'
import DocumentCard from './DocumentCard'

type Props = {
  onNameClick: (id: number) => void
  onAnalysisClick: (id: number) => void
}

export default function DocumentTab({ onNameClick, onAnalysisClick }: Props) {
  const [search, setSearch] = useState('')
  const [viewMode, setViewMode] = useState<'list' | 'grid'>('list')
  const [filter, setFilter] = useState('전체')

  const filtered = files.filter((f) => {
    const matchSearch = f.name.toLowerCase().includes(search.toLowerCase())
    const matchFilter = filter === '전체' || f.type === filter
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
            className="flex-1 text-sm text-gray-700 dark:text-gray-200 outline-none placeholder-gray-300 bg-transparent"
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

        <div className="flex bg-gray-100 rounded-lg p-0.5">
          <button
            onClick={() => setViewMode('list')}
            className={`p-1.5 rounded-md transition ${viewMode === 'list' ? 'bg-white shadow-sm' : ''}`}
          >
            <List size={14} className={viewMode === 'list' ? 'text-gray-700' : 'text-gray-400'} />
          </button>
          <button
            onClick={() => setViewMode('grid')}
            className={`p-1.5 rounded-md transition ${viewMode === 'grid' ? 'bg-white shadow-sm' : ''}`}
          >
            <Grid size={14} className={viewMode === 'grid' ? 'text-gray-700' : 'text-gray-400'} />
          </button>
        </div>
      </div>

      {viewMode === 'list' && (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 overflow-hidden">
          <div className="grid grid-cols-12 px-4 py-2 border-b border-gray-100 dark:border-gray-700 bg-gray-50 dark:bg-gray-700">
            <span className="col-span-5 text-xs text-gray-400 font-medium">이름</span>
            <span className="col-span-2 text-xs text-gray-400 font-medium">유형</span>
            <span className="col-span-2 text-xs text-gray-400 font-medium">업로드 날짜</span>
            <span className="col-span-2 text-xs text-gray-400 font-medium">크기</span>
            <span className="col-span-1 text-xs text-gray-400 font-medium">분석</span>
          </div>
          {filtered.map((file) => (
            <DocumentCard
              key={file.id}
              file={file}
              viewMode="list"
              onNameClick={(f) => onNameClick(f.id)}
              onAnalysisClick={(f) => onAnalysisClick(f.id)}
            />
          ))}
        </div>
      )}

      {viewMode === 'grid' && (
        <div className="grid grid-cols-3 gap-4">
          {filtered.map((file) => (
            <DocumentCard
              key={file.id}
              file={file}
              viewMode="grid"
              onNameClick={(f) => onNameClick(f.id)}
              onAnalysisClick={(f) => onAnalysisClick(f.id)}
            />
          ))}
        </div>
      )}
    </div>
  )
}