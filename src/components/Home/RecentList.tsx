import { FileText, ArrowRight, Plus } from 'lucide-react'

const recentItems = [
  { name: '마케팅 전략 회의', date: '2024.05.20 14:00', status: '분석 완료', statusColor: 'text-blue-500' },
  { name: '개발 스프린트 회의', date: '2024.05.18 10:00', status: '분석 완료', statusColor: 'text-blue-500' },
  { name: '고객 미팅 회의', date: '2024.05.16 09:00', status: '분석 완료', statusColor: 'text-blue-500' },
  { name: '신대물 기획 회의', date: '2024.05.14 11:00', status: '분석 중', statusColor: 'text-orange-500' },
]

export default function RecentList() {
  return (
    <div className="w-64 flex flex-col gap-4 flex-shrink-0">
      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-200">최근 분석</h3>
          <button className="text-xs text-blue-500 flex items-center gap-1 hover:underline">
            전체 보기 <ArrowRight size={10} />
          </button>
        </div>
        <div className="flex flex-col gap-2">
          {recentItems.map((item, i) => (
            <div key={i} className="bg-white dark:bg-gray-800 rounded-xl p-3 border border-gray-100 dark:border-gray-700 hover:border-blue-200 transition cursor-pointer">
              <div className="flex items-start gap-2">
                <div className="w-7 h-7 bg-blue-50 dark:bg-blue-900/30 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5">
                  <FileText size={12} className="text-blue-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium text-gray-700 dark:text-gray-200 truncate">{item.name}</p>
                  <p className="text-xs text-gray-400">{item.date}</p>
                  <p className={`text-xs font-medium mt-1 ${item.statusColor}`}>{item.status}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <button className="w-full flex items-center justify-center gap-2 py-2.5 border border-dashed border-gray-200 dark:border-gray-600 rounded-xl text-xs text-gray-400 hover:border-blue-300 hover:text-blue-400 transition">
        <Plus size={13} /> 새 채팅 시작
      </button>
    </div>
  )
}