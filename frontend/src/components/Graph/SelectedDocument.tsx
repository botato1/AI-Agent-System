type Props = {
  selected: string
  connectedNodes: string[]
  onGoToAnalysis: () => void
}

export default function SelectedDocument({ selected, connectedNodes, onGoToAnalysis }: Props) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 p-4 flex flex-col gap-3">
      <p className="text-sm font-semibold text-gray-700 dark:text-gray-200">{selected}</p>
      <div>
        <p className="text-xs text-gray-400 mb-1.5">연관 문서 {connectedNodes.length}개</p>
        <div className="flex flex-col gap-1">
          {connectedNodes.map((node, i) => (
            <div key={i} className="flex items-center gap-2 text-xs text-gray-600 dark:text-gray-300 bg-gray-50 dark:bg-gray-700 px-2.5 py-1.5 rounded-lg">
              <div className="w-1.5 h-1.5 rounded-full bg-blue-400 flex-shrink-0" />
              {node}
            </div>
          ))}
        </div>
      </div>
      <button
        onClick={onGoToAnalysis}
        className="w-full text-xs text-white bg-blue-600 px-3 py-2 rounded-lg hover:bg-blue-700"
      >
        분석 결과 보기 →
      </button>
    </div>
  )
}