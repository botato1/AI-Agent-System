import { FileText, File } from 'lucide-react'
import type { FileItem } from '../../data/documentsData'
import { iconColors, typeColors } from '../../data/documentsData'

type Props = {
  file: FileItem
  viewMode: 'list' | 'grid'
  onNameClick: (file: FileItem) => void
  onAnalysisClick: (file: FileItem) => void
}

const getIcon = (type: string) => {
  if (type === 'pdf')  return <FileText size={16} />
  if (type === 'docx') return <File size={16} />
  return <File size={16} />
}

export default function DocumentCard({ file, viewMode, onNameClick, onAnalysisClick }: Props) {
  if (viewMode === 'list') {
    return (
      <div className="grid grid-cols-12 px-4 py-3 border-b border-gray-50 last:border-0 hover:bg-gray-50 transition items-center">
        <div className="col-span-5 flex items-center gap-3">
          <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${iconColors[file.icon]}`}>
            {getIcon(file.icon)}
          </div>
          <button
            onClick={() => onNameClick(file)}
            className="text-sm text-gray-700 truncate hover:text-blue-600 hover:underline text-left"
          >
            {file.name}
          </button>
        </div>
        <div className="col-span-2">
          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${typeColors[file.type]}`}>
            {file.type}
          </span>
        </div>
        <span className="col-span-2 text-xs text-gray-400">{file.date}</span>
        <span className="col-span-2 text-xs text-gray-400">{file.size}</span>
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
    <div className="bg-white rounded-xl border border-gray-100 p-4 hover:border-blue-200 transition">
      <div className={`w-10 h-10 rounded-xl flex items-center justify-center mb-3 ${iconColors[file.icon]}`}>
        {getIcon(file.icon)}
      </div>
      <button
        onClick={() => onNameClick(file)}
        className="text-sm font-medium text-gray-700 truncate mb-1 w-full text-left hover:text-blue-600 hover:underline"
      >
        {file.name}
      </button>
      <div className="flex items-center justify-between mt-1">
        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${typeColors[file.type]}`}>
          {file.type}
        </span>
        <span className="text-xs text-gray-400">{file.size}</span>
      </div>
      <div className="flex items-center justify-between mt-2">
        <p className="text-xs text-gray-300">{file.date}</p>
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