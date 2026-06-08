const tasks = [
  { title: '인스타그램 릴스 콘텐츠 기획안 작성', assignee: '김나연', due: '5월 25일(토)', priority: 'high', status: '진행중', statusColor: 'bg-orange-100 text-orange-600' },
  { title: '타겟 광고 예산 산정', assignee: '문지수', due: '5월 26일(일)', priority: 'high', status: '진행중', statusColor: 'bg-orange-100 text-orange-600' },
  { title: '경쟁사 SNS 분석 리포트', assignee: '이승주', due: '5월 23일(목)', priority: 'mid', status: '대기', statusColor: 'bg-gray-100 text-gray-500' },
  { title: 'A/B 테스트 계획 수립', assignee: '김나연', due: '5월 27일(월)', priority: 'mid', status: '대기', statusColor: 'bg-gray-100 text-gray-500' },
  { title: '캠페인 성과 지표 정의', assignee: '문지수', due: '5월 28일(화)', priority: 'low', status: '대기', statusColor: 'bg-gray-100 text-gray-500' },
]

const priorityColors: Record<string, string> = {
  high: 'bg-red-400',
  mid: 'bg-amber-400',
  low: 'bg-green-400',
}

const priorityLabel: Record<string, string> = {
  high: '높음',
  mid: '보통',
  low: '낮음',
}

export default function TabTasks() {
  return (
    <div className="grid grid-cols-2 gap-4">
      {tasks.map((task, i) => (
        <div key={i} className="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 p-4 hover:border-blue-200 transition">
          <div className="flex items-center justify-between mb-3">
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${task.statusColor}`}>{task.status}</span>
            <span className="text-xs text-gray-400">{task.due}</span>
          </div>
          <p className="text-sm font-medium text-gray-700 dark:text-gray-200 mb-3">{task.title}</p>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-5 h-5 bg-blue-100 dark:bg-blue-900 rounded-full flex items-center justify-center">
                <span className="text-xs text-blue-600 dark:text-blue-300">{task.assignee[0]}</span>
              </div>
              <span className="text-xs text-gray-500 dark:text-gray-400">{task.assignee}</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className={`w-2 h-2 rounded-full ${priorityColors[task.priority]}`} />
              <span className="text-xs text-gray-400">{priorityLabel[task.priority]}</span>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}