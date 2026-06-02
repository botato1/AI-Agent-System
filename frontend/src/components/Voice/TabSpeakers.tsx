//발언자 탭 - 발언자별 비율 상세
const attendees = [
  { name: '김나연', tags: ['SNS 캠페인', '인스타그램', '콘텐츠'], percent: 42 },
  { name: '문지수', tags: ['광고 예산', '타겟 마케팅'], percent: 33 },
  { name: '이승주', tags: ['경쟁사 분석', '성과 지표'], percent: 25 },
]

export default function TabSpeakers() {
  return (
    <div className="flex flex-col gap-4">
      {attendees.map((a, i) => (
        <div key={i} className="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 p-4">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 bg-blue-100 dark:bg-blue-900 rounded-full flex items-center justify-center">
              <span className="text-sm text-blue-600 dark:text-blue-300 font-medium">{a.name[0]}</span>
            </div>
            <div>
              <p className="text-sm font-semibold text-gray-700 dark:text-gray-200">{a.name}</p>
              <p className="text-xs text-gray-400">발언 비율 {a.percent}%</p>
            </div>
          </div>
          <div className="w-full bg-gray-100 dark:bg-gray-700 rounded-full h-2 mb-3">
            <div className="bg-blue-500 h-2 rounded-full" style={{ width: `${a.percent}%` }}></div>
          </div>
          <div className="flex gap-1 flex-wrap">
            {a.tags.map((tag, j) => (
              <span key={j} className="text-xs bg-blue-50 dark:bg-blue-900 text-blue-500 dark:text-blue-300 px-2 py-0.5 rounded-full border border-blue-100 dark:border-blue-800">{tag}</span>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}