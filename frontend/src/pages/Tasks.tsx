import { useState } from 'react'
import { Plus, MoreHorizontal } from 'lucide-react'

const initialTasks = [
  { id: 1, title: '신규 광고 소재 3종 제작', assignee: '김나연', due: '5월 25일', priority: '높음', status: 'todo', done: false },
  { id: 2, title: 'A/B 테스트 계획 수립', assignee: '이지원', due: '5월 26일', priority: '중간', status: 'todo', done: false },
  { id: 3, title: '인플루언서 리스트업', assignee: '박민수', due: '5월 27일', priority: '낮음', status: 'todo', done: false },
  { id: 4, title: '랜딩페이지 디자인 수정', assignee: '박민수', due: '5월 21일', priority: '높음', status: 'inprogress', done: false },
  { id: 5, title: '이메일 템플릿 제작', assignee: '이지원', due: '5월 22일', priority: '중간', status: 'inprogress', done: false },
  { id: 6, title: '타겟 고객 분석', assignee: '김나연', due: '5월 19일', priority: '높음', status: 'inprogress', done: false },
  { id: 7, title: '기존 캠페인 성과 분석', assignee: '박민수', due: '5월 18일', priority: '낮음', status: 'inprogress', done: false },
  { id: 8, title: '경쟁사 분석', assignee: '이지원', due: '5월 15일', priority: '중간', status: 'done', done: true },
  { id: 9, title: '시장 조사', assignee: '김나연', due: '5월 14일', priority: '낮음', status: 'done', done: true },
  { id: 10, title: '광고 예산 검토', assignee: '김나연', due: '5월 10일', priority: '높음', status: 'delayed', done: false },
  { id: 11, title: 'SNS 콘텐츠 기획', assignee: '이지원', due: '5월 12일', priority: '중간', status: 'delayed', done: false },
]

const priorityDot: Record<string, { active: string; done: string }> = {
  '높음': { active: 'bg-[#ff8fa3] dark:bg-[#c4607a]', done: 'bg-red-200 dark:bg-[#5a3a3f]' },
  '중간': { active: 'bg-[#ffd166] dark:bg-[#b89a40]', done: 'bg-amber-200 dark:bg-[#5a4e2a]' },
  '낮음': { active: 'bg-[#06d6a0] dark:bg-[#0a9e76]', done: 'bg-green-200 dark:bg-[#1e4a3a]' },
}

const columns = [
  { id: 'todo', title: '해야 할 일', barColor: 'bg-[#555]' },
  { id: 'inprogress', title: '진행 중', barColor: 'bg-[#ffd166] dark:bg-[#b89a40]' },
  { id: 'done', title: '완료', barColor: 'bg-[#06d6a0] dark:bg-[#0a9e76]' },
  { id: 'delayed', title: '지연', barColor: 'bg-[#ff8fa3] dark:bg-[#c4607a]' },
]

const filters = [
  { label: '전체', value: 'all' },
  { label: '해야 할 일', value: 'todo' },
  { label: '진행 중', value: 'inprogress' },
  { label: '완료', value: 'done' },
  { label: '지연', value: 'delayed' },
]

export default function Tasks() {
  const [taskList, setTaskList] = useState(initialTasks)
  const [activeFilter, setActiveFilter] = useState('all')

  const toggleDone = (id: number) => {
    setTaskList(prev => prev.map(task =>
      task.id === id ? { ...task, done: !task.done } : task
    ))
  }

  const getFilteredColumns = () => {
    if (activeFilter === 'all') {
      return columns.map(col => ({
        ...col,
        tasks: taskList.filter(t => t.status === col.id)
      }))
    }
    return columns
      .filter(col => col.id === activeFilter)
      .map(col => ({
        ...col,
        tasks: taskList.filter(t => t.status === col.id)
      }))
  }

  const filteredColumns = getFilteredColumns()

  return (
    <div>
      {/* 헤더 */}
      <div className="flex items-center justify-between mb-5">
        <h1 className="text-lg font-bold text-gray-800 dark:text-white">업무 (Task)</h1>
        <button className="flex items-center gap-1.5 text-xs text-white bg-blue-600 px-3 py-2 rounded-lg hover:bg-blue-700">
          <Plus size={13} /> 새 업무
        </button>
      </div>

      {/* 필터 탭 */}
      <div className="flex gap-1 mb-5 border-b border-gray-100 dark:border-gray-700">
        {filters.map((f) => (
          <button
            key={f.value}
            onClick={() => setActiveFilter(f.value)}
            className={`text-xs px-3 py-2 border-b-2 transition ${
              activeFilter === f.value
                ? 'border-blue-600 text-blue-600 font-medium'
                : 'border-transparent text-gray-400 hover:text-gray-600 dark:hover:text-gray-300'
            }`}
          >
            {f.label}
            <span className="ml-1 text-gray-300">
              {f.value === 'all' ? taskList.length : taskList.filter(t => t.status === f.value).length}
            </span>
          </button>
        ))}
      </div>

      {/* 칸반 보드 */}
      <div className={`grid gap-4 ${
        filteredColumns.length === 1 ? 'grid-cols-1 max-w-sm' :
        filteredColumns.length === 2 ? 'grid-cols-2' : 'grid-cols-4'
      }`}>
        {filteredColumns.map((col) => (
          <div key={col.id} className="flex flex-col gap-3">
            {/* 컬럼 헤더 */}
            <div className="flex items-center justify-between">
  <div className="flex items-center gap-2">
    <div className="flex items-center gap-1.5">
      <div className={`w-[1.5px] h-3.5 rounded-sm ${col.barColor}`} />
      <span className="text-xs text-gray-500 dark:text-gray-400 font-medium">{col.title}</span>
      <span className="text-xs text-gray-400 dark:text-gray-600">{col.tasks.length}</span>
    </div>
  </div>
  <button className="w-5 h-5 flex items-center justify-center rounded hover:bg-gray-100 dark:hover:bg-gray-700">
    <Plus size={12} className="text-gray-400" />
  </button>
</div>

            {/* 태스크 카드 */}
            {col.tasks.map((task) => (
              <div
                key={task.id}
                className={`rounded-xl border p-3 transition cursor-pointer ${
                  task.done
                    ? 'bg-gray-50 border-gray-100 dark:bg-[#181818] dark:border-[#222]'
                    : 'bg-white dark:bg-gray-800 border-gray-100 dark:border-gray-700 hover:border-blue-200 dark:hover:border-blue-800 hover:shadow-sm'
                }`}
              >
                {/* 우선순위 + 더보기 */}
                <div className="flex items-start justify-between mb-2">
                  <div
                    className="flex items-center gap-1.5 cursor-pointer"
                    onClick={() => toggleDone(task.id)}
                  >
                    <span className={`w-2.5 h-2.5 rounded-full flex-shrink-0 transition-all ${
                      task.done
                        ? priorityDot[task.priority].done
                        : priorityDot[task.priority].active
                    }`} />
                    <span className={`text-xs transition-colors ${
                      task.done
                        ? 'text-gray-300 dark:text-[#333]'
                        : 'text-gray-400 dark:text-gray-500'
                    }`}>
                      {task.priority}
                    </span>
                  </div>
                  <button className="w-5 h-5 flex items-center justify-center rounded hover:bg-gray-100 dark:hover:bg-gray-700">
                    <MoreHorizontal size={12} className="text-gray-300" />
                  </button>
                </div>

                {/* 제목 */}
                <p className={`text-xs font-medium mb-3 leading-relaxed transition-all ${
                  task.done
                    ? 'line-through text-gray-300 dark:text-[#444]'
                    : 'text-gray-700 dark:text-gray-200'
                }`}>
                  {task.title}
                </p>

                {/* 담당자 + 날짜 */}
                <div className="flex items-center justify-between">
                  <span className={`text-xs transition-colors ${
                    task.done ? 'text-gray-300 dark:text-[#333]' : 'text-gray-400'
                  }`}>
                    {task.assignee}
                  </span>
                  <span className={`text-xs transition-colors ${
                    task.done ? 'text-gray-300 dark:text-[#333]' : 'text-gray-400'
                  }`}>
                    {task.due}
                  </span>
                </div>
              </div>
            ))}

            {/* 업무 추가 버튼 */}
            <button className="w-full py-2 border border-dashed border-gray-200 dark:border-gray-600 rounded-xl text-xs text-gray-300 dark:text-gray-600 hover:border-blue-300 hover:text-blue-400 transition">
              + 업무 추가
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}