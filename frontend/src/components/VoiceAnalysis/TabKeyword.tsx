const keywords = [
  { word: '마케팅', size: 28, color: '#6366f1', x: 50, y: 45 },
  { word: '전략', size: 22, color: '#818cf8', x: 72, y: 25 },
  { word: '캠페인', size: 22, color: '#3b82f6', x: 25, y: 30 },
  { word: '예산', size: 18, color: '#8b5cf6', x: 70, y: 65 },
  { word: '유튜브', size: 16, color: '#6b7280', x: 20, y: 60 },
  { word: '인스타그램', size: 15, color: '#6b7280', x: 45, y: 75 },
  { word: '성과', size: 17, color: '#14b8a6', x: 15, y: 45 },
  { word: '목표', size: 13, color: '#9ca3af', x: 60, y: 82 },
  { word: '브랜드', size: 13, color: '#9ca3af', x: 78, y: 48 },
  { word: '광고', size: 13, color: '#9ca3af', x: 33, y: 18 },
  { word: '실행', size: 12, color: '#9ca3af', x: 12, y: 75 },
  { word: '콘텐츠', size: 15, color: '#9ca3af', x: 55, y: 15 },
]

const keywordList = [
  { word: '마케팅', count: 24 },
  { word: '캠페인', count: 18 },
  { word: '전략', count: 15 },
  { word: '예산', count: 12 },
  { word: '유튜브', count: 9 },
  { word: '인스타그램', count: 8 },
]

export default function TabKeyword() {
  return (
    <div className="grid grid-cols-2 gap-4">
      {/* 워드 클라우드 */}
      <div className="bg-white dark:bg-[#1c1a1a] rounded-xl border border-gray-100 dark:border-gray-700 p-6">
        <h3 className="text-sm font-medium text-gray-700 dark:text-gray-200 mb-3">핵심 키워드</h3>
        <div className="w-full" style={{ aspectRatio: '4/3', maxHeight: '300px' }}>
          <svg
            viewBox="0 0 300 220"
            className="w-full h-full"
            xmlns="http://www.w3.org/2000/svg"
          >
            {keywords.map((kw, i) => (
              <text
                key={i}
                x={`${kw.x}%`}
                y={`${kw.y}%`}
                textAnchor="middle"
                dominantBaseline="middle"
                fontSize={kw.size}
                fontWeight={kw.size >= 20 ? 600 : 400}
                fill={kw.color}
                style={{ cursor: 'pointer' }}
              >
                {kw.word}
              </text>
            ))}
          </svg>
        </div>
        <button className="mt-2 text-xs text-blue-500 hover:text-blue-600 transition-colors">
          전체 키워드 보기 →
        </button>
      </div>

      {/* 키워드 빈도 */}
      <div className="bg-white dark:bg-[#1c1a1a] rounded-xl border border-gray-100 dark:border-gray-700 p-6">
        <h3 className="text-sm font-medium text-gray-700 dark:text-gray-200 mb-4">키워드 빈도</h3>
        <div className="flex flex-col gap-3">
          {keywordList.map((kw, i) => (
            <div key={i} className="flex items-center gap-3">
              <span className="text-xs text-gray-600 dark:text-gray-300 w-20">{kw.word}</span>
              <div className="flex-1 bg-gray-100 dark:bg-gray-700 rounded-full h-1.5">
                <div
                  className="bg-blue-400 h-1.5 rounded-full"
                  style={{ width: `${(kw.count / 24) * 100}%` }}
                />
              </div>
              <span className="text-xs text-gray-400 w-6 text-right">{kw.count}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}