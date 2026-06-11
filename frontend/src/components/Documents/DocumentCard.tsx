//문서 보관함 - 문서 카드 (리스트/그리드)
import { FileText, File } from 'lucide-react'
import type { FileItem } from '../../data/documentsData'

type Props = {
  file: FileItem
  viewMode: 'list' | 'grid'
  onNameClick: (file: FileItem) => void
  onAnalysisClick: (file: FileItem) => void
}

const getIcon = (type: string) => {
  if (type === 'pdf') return <FileText size={16} />
  if (type === 'docx') return <File size={16} />
  return <File size={16} />
}

const typeColors: Record<string, { color: string }> = {
  PDF:  { color: '#818cf8' },
  DOCX: { color: '#34d399' },
  TXT:  { color: '#fb923c' },
}

export default function DocumentCard({ file, viewMode, onNameClick, onAnalysisClick }: Props) {
  if (viewMode === 'list') {
    return (
      <div className="grid grid-cols-12 px-4 py-3 border-b border-gray-100 dark:border-gray-700 last:border-0 items-center">
        <div className="col-span-5 flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center border border-gray-200 dark:border-gray-700 text-gray-400 dark:text-gray-500">
            {getIcon(file.icon)}
          </div>
          <button
            onClick={() => onNameClick(file)}
            className="text-sm text-gray-700 dark:text-gray-200 truncate hover:text-blue-500 text-left"
          >
            {file.name}
          </button>
        </div>
        <div className="col-span-2">
          <span className="text-xs font-medium" style={{ color: typeColors[file.type].color }}>
            {file.type}
          </span>
        </div>
        <span className="col-span-2 text-xs text-gray-500 dark:text-gray-400">{file.date}</span>
        <span className="col-span-2 text-xs text-gray-500 dark:text-gray-400">{file.size}</span>
        <div className="col-span-1">
          <button
            onClick={() => onAnalysisClick(file)}
            className="text-xs text-blue-500 hover:underline"
          >
            분석
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-600 p-4 hover:border-blue-300 dark:hover:border-blue-600 transition">
      <div className="w-10 h-10 rounded-xl flex items-center justify-center mb-3 border border-gray-200 dark:border-gray-700 text-gray-400 dark:text-gray-500">
        {getIcon(file.icon)}
      </div>
      <button
        onClick={() => onNameClick(file)}
        className="text-sm font-medium text-gray-700 dark:text-gray-200 truncate mb-1 w-full text-left hover:text-blue-500"
      >
        {file.name}
      </button>
      <div className="flex items-center justify-between mt-1">
        <span className="text-xs font-medium" style={{ color: typeColors[file.type].color }}>
          {file.type}
        </span>
        <span className="text-xs text-gray-500 dark:text-gray-400">{file.size}</span>
      </div>
      <div className="flex items-center justify-between mt-2">
        <p className="text-xs text-gray-400 dark:text-gray-500">{file.date}</p>
        <button
          onClick={() => onAnalysisClick(file)}
          className="text-xs text-blue-500 hover:underline"
        >
          분석
        </button>
      </div>
    </div>
  )
}