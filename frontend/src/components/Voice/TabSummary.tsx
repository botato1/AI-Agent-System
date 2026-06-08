const analysisStats = [
  { label: '총 발언 시간', value: '42분' },
  { label: '발언자 수', value: '3명' },
  { label: '추출된 Task', value: '5개' },
  { label: '분석 소요 시간', value: '3.1초' },
]

export default function TabSummary() {
  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-4 gap-3">
        {analysisStats.map((stat, i) => (
          <div key={i} className="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 p-4 text-center">
            <p className="text-lg font-bold text-blue-600 dark:text-blue-400">{stat.value}</p>
            <p className="text-xs text-gray-400 mt-1">{stat.label}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 p-4">
          <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-200 mb-3">회의 요약</h3>
          <ul className="flex flex-col gap-2">
            {[
              '마케팅 전략 회의에서 SNS 캠페인 방향 확정',
              '인스타그램 릴스 중심 콘텐츠 제작 결정',
              '타겟 연령대 20~35세로 설정',
              '광고 예산 산정 및 담당자 배분',
              '다음 회의: 5월 27일 (월)',
            ].map((item, i) => (
              <li key={i} className="flex items-start gap-2 text-xs text-gray-600 dark:text-gray-300">
                <span className="w-1 h-1 rounded-full bg-blue-400 mt-1.5 flex-shrink-0"></span>
                {item}
              </li>
            ))}
          </ul>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 p-4">
          <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-200 mb-3">키워드</h3>
          <div className="flex flex-wrap gap-2">
            {['SNS 캠페인', '인스타그램', '타겟 마케팅', '광고 예산', '콘텐츠 제작', '2분기'].map((tag, i) => (
              <span key={i} className="text-xs bg-blue-50 dark:bg-blue-900 text-blue-500 dark:text-blue-300 px-3 py-1 rounded-full border border-blue-100 dark:border-blue-800">{tag}</span>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}