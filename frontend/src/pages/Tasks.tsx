import { useState } from 'react'
import { Plus, MoreHorizontal } from 'lucide-react'

const initialTasks = [
  { id: 1, title: '신규 광고 소재 3종 제작', assignee: '김나연', due: '5월 25일', priority: '높음', priorityColor: 'border border-red-300 text-red-400 dark:border-[#e05c5c] dark:text-[#e05c5c]', status: 'todo', done: false },
  { id: 2, title: 'A/B 테스트 계획 수립', assignee: '이지원', due: '5월 26일', priority: '중간', priorityColor: 'border border-orange-300 text-orange-400 dark:border-[#e8a838] dark:text-[#e8a838]', status: 'todo', done: false },
  { id: 3, title: '인플루언서 리스트업', assignee: '박민수', due: '5월 27일', priority: '낮음', priorityColor: 'border border-green-300 text-green-400 dark:border-[#4caf82] dark:text-[#4caf82]', status: 'todo', done: false },
  { id: 4, title: '랜딩페이지 디자인 수정', assignee: '박민수', due: '5월 21일', priority: '높음', priorityColor: 'border border-red-300 text-red-400 dark:border-[#e05c5c] dark:text-[#e05c5c]', status: 'inprogress', done: false },
  { id: 5, title: '이메일 템플릿 제작', assignee: '이지원', due: '5월 22일', priority: '중간', priorityColor: 'border border-orange-300 text-orange-400 dark:border-[#e8a838] dark:text-[#e8a838]', status: 'inprogress', done: false },
  { id: 6, title: '타겟 고객 분석', assignee: '김나연', due: '5월 19일', priority: '높음', priorityColor: 'border border-red-300 text-red-400 dark:border-[#e05c5c] dark:text-[#e05c5c]', status: 'inprogress', done: false },
  { id: 7, title: '기존 캠페인 성과 분석', assignee: '박민수', due: '5월 18일', priority: '낮음', priorityColor: 'border border-green-300 text-green-400 dark:border-[#4caf82] dark:text-[#4caf82]', status: 'inprogress', done: false },
  { id: 8, title: '경쟁사 분석', assignee: '이지원', due: '5월 15일', priority: '중간', priorityColor: 'border border-orange-300 text-orange-400 dark:border-[#e8a838] dark:text-[#e8a838]', status: 'done', done: true },
  { id: 9, title: '시장 조사', assignee: '김나연', due: '5월 14일', priority: '낮음', priorityColor: 'border border-green-300 text-green-400 dark:border-[#4caf82] dark:text-[#4caf82]', status: 'done', done: true },
  { id: 10, title: '광고 예산 검토', assignee: '김나연', due: '5월 10일', priority: '높음', priorityColor: 'border border-red-300 text-red-400 dark:border-[#e05c5c] dark:text-[#e05c5c]', status: 'delayed', done: false },
  { id: 11, title: 'SNS 콘텐츠 기획', assignee: '이지원', due: '5월 12일', priority: '중간', priorityColor: 'border border-orange-300 text-orange-400 dark:border-[#e8a838] dark:text-[#e8a838]', status: 'delayed', done: false },
]

const columns = [
  { id: 'todo', title: '해야 할 일', color: 'bg-gray-100 text-gray-600 dark:bg-[#2a2a2a] dark:text-gray-300' },
  { id: 'inprogress', title: '진행 중', color: 'bg-orange-50 text-orange-500 dark:bg-[#2a2215] dark:text-[#e8a838]' },
  { id: 'done', title: '완료', color: 'bg-green-50 text-green-500 dark:bg-[#152a1e] dark:text-[#4caf82]' },
  { id: 'delayed', title: '지연', color: 'bg-red-50 text-red-500 dark:bg-[#2a1515] dark:text-[#e05c5c]' },
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
      <div className="flex items-center justify-between mb-5">
        <h1 className="text-lg font-bold text-gray-800 dark:text-white">업무 (Task)</h1>
        <button className="flex items-center gap-1.5 text-xs text-white bg-blue-600 px-3 py-2 rounded-lg hover:bg-blue-700">
          <Plus size={13} /> 새 업무
        </button>
      </div>

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

      <div className={`grid gap-4 ${filteredColumns.length === 1 ? 'grid-cols-1 max-w-sm' : filteredColumns.length === 2 ? 'grid-cols-2' : 'grid-cols-4'}`}>
        {filteredColumns.map((col) => (
          <div key={col.id} className="flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${col.color}`}>{col.title}</span>
                <span className="text-xs text-gray-400">{col.tasks.length}</span>
              </div>
              <button className="w-5 h-5 flex items-center justify-center rounded hover:bg-gray-100 dark:hover:bg-gray-700">
                <Plus size={12} className="text-gray-400" />
              </button>
            </div>

            {col.tasks.map((task) => (
              <div key={task.id} className="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 p-3 hover:border-blue-200 hover:shadow-sm transition cursor-pointer">
                <div className="flex items-start justify-between mb-2">
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${task.priorityColor}`}>{task.priority}</span>
                  <button className="w-5 h-5 flex items-center justify-center rounded hover:bg-gray-100 dark:hover:bg-gray-700">
                    <MoreHorizontal size={12} className="text-gray-300" />
                  </button>
                </div>
                <p className={`text-xs font-medium mb-3 leading-relaxed transition-all ${
                  task.done
                    ? 'line-through text-gray-300 dark:text-gray-600'
                    : 'text-gray-700 dark:text-gray-200'
                }`}>
                  {task.title}
                </p>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5">
                    <input
                      type="checkbox"
                      checked={task.done}
                      onChange={() => toggleDone(task.id)}
                      className="w-3.5 h-3.5 accent-blue-500 cursor-pointer"
                    />
                    <div className="w-5 h-5 bg-blue-100 dark:bg-blue-900 rounded-full flex items-center justify-center">
                      <span className="text-xs text-blue-600 dark:text-blue-300">{task.assignee[0]}</span>
                    </div>
                    <span className="text-xs text-gray-400">{task.assignee}</span>
                  </div>
                  <span className="text-xs text-gray-400">{task.due}</span>
                </div>
              </div>
            ))}

            <button className="w-full py-2 border border-dashed border-gray-200 dark:border-gray-600 rounded-xl text-xs text-gray-300 dark:text-gray-600 hover:border-blue-300 hover:text-blue-400 transition">
              + 업무 추가
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}