import { useState } from 'react'

const analysisStats = [
  { label: '핵심 문장 추출', value: '12개' },
  { label: '감지된 액션 아이템', value: '8개' },
  { label: '연관 문서', value: '3개' },
  { label: '분석 소요 시간', value: '2.3초' },
]

const initialTasks = [
  { id: 1, title: '신규 광고 소재 3종 제작', assignee: '김나연', due: '5월 25일(토)', status: '진행중', done: false },
  { id: 2, title: 'A/B 테스트 계획 수립', assignee: '이지원', due: '5월 26일(일)', status: '진행중', done: false },
  { id: 3, title: '랜딩페이지 디자인 수정', assignee: '박민수', due: '5월 21일(화)', status: '완료', done: true },
  { id: 4, title: '성과 측정 지표 정의', assignee: '박민수', due: '5월 23일(목)', status: '대기', done: false },
]

const statusColor: Record<string, string> = {
  '진행중': 'text-blue-500 dark:text-blue-400',
  '완료': 'text-gray-400 dark:text-[#555]',
  '대기': 'text-blue-300 dark:text-[#7aa4c8]',
}

export default function TabSummary() {
  const [tasks, setTasks] = useState(initialTasks)

  const toggleDone = (id: number) => {
    setTasks(prev => prev.map(t => t.id === id ? { ...t, done: !t.done } : t))
  }

  return (
    <div className="flex flex-col gap-4">

      {/* 분석 통계 */}
      <div className="grid grid-cols-4 gap-3">
        {analysisStats.map((stat, i) => (
          <div key={i} className="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 p-4 text-center">
            <p className="text-lg font-bold text-blue-600 dark:text-blue-400">{stat.value}</p>
            <p className="text-xs text-gray-400 mt-1">{stat.label}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="flex flex-col gap-4">

          {/* 회의 요약 */}
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 p-4">
            <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-200 mb-3">회의 요약</h3>
            <ul className="flex flex-col gap-2">
              {[
                '2024년 하반기 마케팅 전략 및 캠페인 방향 논의',
                '신규 광고 소재 제작 일정 및 담당자 확정',
                '랜딩페이지 디자인 수정 및 A/B 테스트 계획 수립',
                '성과 측정 지표 및 목표 설정',
                '다음 회의 일정: 5월 27일 (월)',
              ].map((item, i) => (
                <li key={i} className="flex items-start gap-2 text-xs text-gray-600 dark:text-gray-300">
                  <span className="w-1 h-1 rounded-full bg-gray-400 mt-1.5 flex-shrink-0"></span>
                  {item}
                </li>
              ))}
            </ul>
          </div>

          {/* 키워드 */}
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 p-4">
            <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-200 mb-3">키워드</h3>
            <div className="flex flex-wrap gap-2">
              {['마케팅 전략', '광고 소재', '랜딩페이지', 'A/B 테스트', '성과 지표', '캠페인 분석'].map((tag, i) => (
                <span key={i} className="text-xs text-gray-600 dark:text-gray-400 px-3 py-1 rounded-full border border-gray-400 dark:border-gray-500">
                  {tag}
                </span>
              ))}
            </div>
          </div>
        </div>

        <div className="flex flex-col gap-4">

          {/* Task */}
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-200">할 일 (Tasks)</h3>
              <button className="text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300">전체 보기 →</button>
            </div>
            {tasks.map((task) => (
              <div key={task.id} className="flex items-center gap-3 py-2 border-b border-gray-50 dark:border-gray-700 last:border-0">
                <input
                  type="checkbox"
                  checked={task.done}
                  onChange={() => toggleDone(task.id)}
                  className="w-3.5 h-3.5 accent-gray-300 cursor-pointer"
                />
                <div className="flex-1 min-w-0">
                  <p className={`text-xs truncate transition-all ${
                    task.done ? 'line-through text-gray-400 dark:text-gray-600' : 'text-gray-700 dark:text-gray-200'
                  }`}>{task.title}</p>
                  <p className={`text-xs transition-all ${
                    task.done ? 'text-gray-400 dark:text-gray-600' : 'text-gray-400'
                  }`}>{task.assignee} · {task.due}</p>
                </div>
                <span className={`text-xs font-medium flex-shrink-0 ${
                  task.done ? 'text-gray-400 dark:text-[#555]' : statusColor[task.status]
                }`}>
                  {task.done ? '완료' : task.status}
                </span>
              </div>
            ))}
          </div>

          {/* 저장 상태 */}
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 p-4">
            <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-200 mb-3">저장 상태</h3>
            <div className="flex flex-col gap-2">
              {[
                { label: 'Notion 페이지', value: '자동 생성 완료' },
                { label: '연관 문서', value: '유사 문서 3개 발견' },
                { label: 'RAG 인덱싱', value: '벡터 DB 저장 완료' },
              ].map((item, i) => (
                <div key={i} className="flex items-center justify-between py-1.5 border-b border-gray-50 dark:border-gray-700 last:border-0">
                  <span className="text-xs text-gray-500 dark:text-gray-400">{item.label}</span>
                  <span className="text-xs font-medium text-gray-600 dark:text-gray-400">{item.value}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}