import { useState } from 'react'

interface Props {
  analysisData?: any
}

const statusColor: Record<string, string> = {
  '진행중': 'text-blue-500 dark:text-blue-400',
  '완료': 'text-gray-400 dark:text-[#555]',
  '대기': 'text-blue-300 dark:text-[#7aa4c8]',
}

export default function TabSummary({ analysisData }: Props) {
  const [tasks, setTasks] = useState(
    (analysisData?.chunks ?? [])
      .filter((c: any) => c.metadata?.style === 'title' || c.type === 'text')
      .slice(0, 4)
      .map((c: any, i: number) => ({
        id: i + 1,
        title: c.content,
        assignee: '-',
        due: '-',
        status: '대기',
        done: false,
      }))
  )

  const toggleDone = (id: number) => {
    setTasks((prev: any[]) => prev.map(t => t.id === id ? { ...t, done: !t.done } : t))
  }

  const analysisStats = [
    { label: '핵심 문장 추출', value: `${analysisData?.chunks?.length ?? 0}개` },
    { label: '감지된 액션 아이템', value: '—' },
    { label: '연관 문서', value: '—' },
    { label: '분석 소요 시간', value: `${analysisData?.metadata?.processing_time_sec?.toFixed(1) ?? '—'}초` },
  ]

  // content를 줄바꿈으로 분리해서 요약 포인트로 표시
  const summaryPoints = analysisData?.content
    ? analysisData.content.split('\n').filter((s: string) => s.trim()).slice(0, 5)
    : ['요약 데이터가 없습니다.']

  // chunks에서 키워드 추출 (title 스타일)
  const keywords = analysisData?.chunks
    ? analysisData.chunks
        .filter((c: any) => c.metadata?.style === 'title' || c.metadata?.style === 'heading')
        .map((c: any) => c.content)
        .slice(0, 6)
    : ['마케팅 전략', '광고 소재', '랜딩페이지', 'A/B 테스트', '성과 지표']

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
            <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-200 mb-3">문서 요약</h3>
            <ul className="flex flex-col gap-2">
              {summaryPoints.map((item: string, i: number) => (
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
              {keywords.map((tag: string, i: number) => (
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
              <button className="text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400">전체 보기 →</button>
            </div>
            {tasks.length === 0 ? (
              <p className="text-xs text-gray-400 text-center py-4">추출된 Task가 없어요</p>
            ) : (
              tasks.map((task: any) => (
                <div key={task.id} className="flex items-center gap-3 py-2 border-b border-gray-50 dark:border-gray-700 last:border-0">
                  <input
                    type="checkbox"
                    checked={task.done}
                    onChange={() => toggleDone(task.id)}
                    className="w-3.5 h-3.5 accent-gray-300 cursor-pointer"
                  />
                  <div className="flex-1 min-w-0">
                    <p className={`text-xs truncate transition-all ${task.done ? 'line-through text-gray-400' : 'text-gray-700 dark:text-gray-200'}`}>{task.title}</p>
                    <p className="text-xs text-gray-400">{task.assignee} · {task.due}</p>
                  </div>
                  <span className={`text-xs font-medium flex-shrink-0 ${task.done ? 'text-gray-400' : statusColor[task.status]}`}>
                    {task.done ? '완료' : task.status}
                  </span>
                </div>
              ))
            )}
          </div>

          {/* 저장 상태 */}
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 p-4">
            <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-200 mb-3">저장 상태</h3>
            <div className="flex flex-col gap-2">
              {[
                { label: '문서 처리', value: analysisData?.status === 'processed' ? '완료' : '—' },
                { label: '페이지 수', value: `${analysisData?.metadata?.page_count ?? '—'}페이지` },
                { label: 'OCR 엔진', value: analysisData?.metadata?.engines?.join(', ') ?? '—' },
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