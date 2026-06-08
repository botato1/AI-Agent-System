import { useState, useEffect } from 'react'
import { Home, CheckSquare, FolderOpen, Settings, Activity, GitFork, Moon, Sun, MessageSquare, ChevronLeft, ChevronRight, Mic } from 'lucide-react'

const BASE_URL = 'http://192.168.0.235:8000'

const menuItems = [
  { icon: Home, label: '홈', id: 'home' },
  { icon: Activity, label: '문서분석', id: 'pipeline' },
  { icon: Mic, label: '음성분석', id: 'voice' },
  { icon: CheckSquare, label: '업무 (Task)', id: 'tasks' },
  { icon: GitFork, label: '그래프', id: 'graph' },
  { icon: FolderOpen, label: '문서 보관함', id: 'documents' },
  { icon: Settings, label: '설정', id: 'settings' },
]

interface Conversation {
  room_id: string
  title: string
  created_at: string
  updated_at: string
}

interface SidebarProps {
  activePage: string
  onPageChange: (id: string) => void
  isDark: boolean
  onToggleDark: () => void
  onChatSelect: (chatId: number) => void
  onCollapse: (v: boolean) => void
  refreshKey?: number
  onRoomSelect: (room_id: string) => void
}

export default function Sidebar({ activePage, onPageChange, isDark, onToggleDark, onChatSelect, onCollapse, refreshKey, onRoomSelect }: SidebarProps) {
  const [collapsed, setCollapsed] = useState(false)
  const [chatCollapsed, setChatCollapsed] = useState(false)
  const [recentChats, setRecentChats] = useState<Conversation[]>([])

  const fetchChats = () => {
    fetch(`${BASE_URL}/api/conversations`)
      .then(r => r.json())
      .then(data => setRecentChats(data.conversations ?? []))
      .catch(err => console.error('채팅 목록 조회 실패:', err))
  }

  useEffect(() => {
    fetchChats()
  }, [refreshKey])

  return (
    <div className={`h-screen bg-white dark:bg-[#161616] border-r border-gray-100 dark:border-[#2a2a2a] flex flex-col fixed left-0 top-0 transition-all duration-300 ${collapsed ? 'w-14' : 'w-52'}`}>

      <div className="p-3 border-b border-gray-100 dark:border-gray-700 flex items-center justify-between">
        {!collapsed && (
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 bg-blue-600 rounded-lg flex items-center justify-center flex-shrink-0">
              <span className="text-white text-xs font-bold">A</span>
            </div>
            <span className="font-bold text-gray-800 dark:text-white text-lg">Agentra</span>
          </div>
        )}
        {collapsed && (
          <div className="w-7 h-7 bg-blue-600 rounded-lg flex items-center justify-center mx-auto">
            <span className="text-white text-xs font-bold">A</span>
          </div>
        )}
        {!collapsed && (
          <button
            onClick={() => { setCollapsed(true); onCollapse(true) }}
            className="w-6 h-6 flex items-center justify-center rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 flex-shrink-0"
          >
            <ChevronLeft size={14} className="text-gray-400" />
          </button>
        )}
      </div>

      {collapsed && (
        <button
          onClick={() => { setCollapsed(false); onCollapse(false) }}
          className="mx-auto mt-2 w-8 h-8 flex items-center justify-center rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
        >
          <ChevronRight size={14} className="text-gray-400" />
        </button>
      )}

      <nav className="flex-1 p-2 overflow-y-auto">
        {menuItems.map((item) => {
          const Icon = item.icon
          const isActive = activePage === item.id
          return (
            <button
              key={item.id}
              onClick={() => onPageChange(item.id)}
              title={collapsed ? item.label : ''}
              className={`w-full flex items-center gap-3 px-2 py-2 rounded-lg mb-1 text-sm transition-all ${
                collapsed ? 'justify-center' : ''
              } ${
                isActive
                  ? 'bg-blue-50 dark:bg-blue-900 text-blue-600 dark:text-blue-400 font-medium'
                  : 'text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700 hover:text-gray-700 dark:hover:text-white'
              }`}
            >
              <Icon size={16} className="flex-shrink-0" />
              {!collapsed && item.label}
            </button>
          )
        })}

        {!collapsed && (
          <div className="mt-3 pt-3 border-t border-gray-100 dark:border-gray-700">
            <button
              onClick={() => setChatCollapsed(!chatCollapsed)}
              className="w-full flex items-center justify-between px-2 mb-2"
            >
              <div className="flex items-center gap-2">
                <MessageSquare size={13} className="text-gray-400" />
                <span className="text-xs font-medium text-gray-400 dark:text-gray-500">최근 채팅</span>
              </div>
              {chatCollapsed
                ? <ChevronRight size={12} className="text-gray-400" />
                : <ChevronLeft size={12} className="text-gray-400" />
              }
            </button>

            {!chatCollapsed && recentChats.length === 0 && (
              <p className="text-xs text-gray-400 px-3 py-1">대화 기록이 없어요</p>
            )}

            {!chatCollapsed && (
          <div className="flex flex-col max-h-64 overflow-y-auto">
            {recentChats.map((chat) => (
  <div
    key={chat.room_id}
    className="group flex items-center rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition mb-0.5"
  >
    <button
      onClick={() => onRoomSelect(chat.room_id)}
      className="flex-1 text-left px-3 py-1.5 text-xs text-gray-500 dark:text-gray-400 truncate"
    >
      {chat.title}
    </button>
    <button
      onClick={async (e) => {
        e.stopPropagation()
        if (!confirm('이 대화를 삭제할까요?')) return
        await fetch(`${BASE_URL}/api/conversations/${chat.room_id}`, { method: 'DELETE' })
        fetchChats()
      }}
      className="opacity-0 group-hover:opacity-100 pr-2 transition text-gray-500 dark:text-gray-400 hover:text-red-400 dark:hover:text-red-400"
    >
      <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4h6v2"/></svg>
    </button>
  </div>
))}
      </div>
            )}
          </div>
        )}
      </nav>

      {!collapsed && (
        <div className="p-4 border-t border-gray-100 dark:border-gray-700">
          <button
            onClick={onToggleDark}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-lg mb-2 text-sm text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700 transition"
          >
            {isDark ? <Sun size={16} /> : <Moon size={16} />}
            {isDark ? '라이트 모드' : '다크 모드'}
          </button>
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 bg-gray-200 dark:bg-gray-600 rounded-full flex items-center justify-center">
              <span className="text-gray-600 dark:text-gray-200 text-xs font-medium">김</span>
            </div>
            <div>
              <div className="text-xs font-medium text-gray-700 dark:text-gray-200">김나연</div>
              <div className="text-xs text-gray-400 dark:text-gray-500">팀 리더</div>
            </div>
          </div>
        </div>
      )}

      {collapsed && (
        <div className="p-2 border-t border-gray-100 dark:border-gray-700 flex flex-col items-center gap-2">
          <button onClick={onToggleDark} className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700">
            {isDark ? <Sun size={16} className="text-gray-400" /> : <Moon size={16} className="text-gray-400" />}
          </button>
          <div className="w-7 h-7 bg-gray-200 dark:bg-gray-600 rounded-full flex items-center justify-center">
            <span className="text-gray-600 dark:text-gray-200 text-xs font-medium">김</span>
          </div>
        </div>
      )}
    </div>
  )
}