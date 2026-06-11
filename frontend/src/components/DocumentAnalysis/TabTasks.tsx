const tasks = [
  { title: '신규 광고 소재 3종 제작', assignee: '김나연', due: '5월 25일(토)', priority: 'high', status: '진행중' },
  { title: 'A/B 테스트 계획 수립', assignee: '이지원', due: '5월 26일(일)', priority: 'high', status: '진행중' },
  { title: '랜딩페이지 디자인 수정', assignee: '박민수', due: '5월 21일(화)', priority: 'mid', status: '완료' },
  { title: '성과 측정 지표 정의', assignee: '박민수', due: '5월 23일(목)', priority: 'low', status: '대기' },
]

const statusColor: Record<string, string> = {
  '진행중': 'text-blue-500 dark:text-blue-400',
  '완료': 'text-gray-400 dark:text-[#555]',
  '대기': 'text-blue-300 dark:text-[#7aa4c8]',
}

const priorityDot: Record<string, string> = {
  high: 'bg-[#ff8fa3] dark:bg-[#c4607a]',
  mid: 'bg-[#ffd166] dark:bg-[#b89a40]',
  low: 'bg-[#06d6a0] dark:bg-[#0a9e76]',
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
        <div key={i} className="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 p-4 hover:border-blue-200 dark:hover:border-blue-800 transition">
          <div className="flex items-center justify-between mb-3">
            <span className={`text-xs font-medium ${statusColor[task.status]}`}>{task.status}</span>
            <span className="text-xs text-gray-400">{task.due}</span>
          </div>
          <p className="text-sm font-medium text-gray-700 dark:text-gray-200 mb-3">{task.title}</p>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-5 h-5 bg-gray-100 dark:bg-gray-700 rounded-full flex items-center justify-center">
                <span className="text-xs text-gray-500 dark:text-gray-400">{task.assignee[0]}</span>
              </div>
              <span className="text-xs text-gray-500 dark:text-gray-400">{task.assignee}</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className={`w-2 h-2 rounded-full ${priorityDot[task.priority]}`} />
              <span className="text-xs text-gray-400">{priorityLabel[task.priority]}</span>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}