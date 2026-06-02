import { useState } from 'react'
import { Home, CheckSquare, FolderOpen, Settings, Activity, GitFork, Moon, Sun, MessageSquare, ChevronLeft, ChevronRight, Mic } from 'lucide-react'

const menuItems = [
  { icon: Home, label: '홈', id: 'home' },
  { icon: Activity, label: '문서분석', id: 'pipeline' },
  { icon: Mic, label: '음성분석', id: 'voice' },
  { icon: CheckSquare, label: '업무 (Task)', id: 'tasks' },
  { icon: GitFork, label: '그래프', id: 'graph' },
  { icon: FolderOpen, label: '문서 보관함', id: 'documents' },
  { icon: Settings, label: '설정', id: 'settings' },
]

const recentChats = [
  { id: 1, title: '마케팅 전략 회의 요약' },
  { id: 2, title: '담당자별 업무 정리' },
  { id: 3, title: 'A/B 테스트 계획' },
  { id: 4, title: '고객 미팅 후속 조치' },
]

interface SidebarProps {
  activePage: string
  onPageChange: (id: string) => void
  isDark: boolean
  onToggleDark: () => void
  onChatSelect: (chatId: number) => void
  onCollapse: (v: boolean) => void
}

export default function Sidebar({ activePage, onPageChange, isDark, onToggleDark, onChatSelect , onCollapse}: SidebarProps) {
  const [collapsed, setCollapsed] = useState(false)
  const [chatCollapsed, setChatCollapsed] = useState(false)

  return (
    <div className={`h-screen bg-white dark:bg-[#161616] border-r border-gray-100 dark:border-[#2a2a2a] flex flex-col fixed left-0 top-0 transition-all duration-300 ${collapsed ? 'w-14' : 'w-52'}`}>

      {/* 로고 + 접기 버튼 */}
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

      {/* 접혔을 때 펼치기 버튼 */}
      {collapsed && (
        <button
          onClick={() => { setCollapsed(false); onCollapse(false) } }
          className="mx-auto mt-2 w-8 h-8 flex items-center justify-center rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
        >
          <ChevronRight size={14} className="text-gray-400" />
        </button>
      )}

      {/* 메뉴 */}
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

        {/* 최근 채팅 */}
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

            {!chatCollapsed && recentChats.map((chat) => (
              <button
                key={chat.id}
                onClick={() => {
                  onPageChange('home')
                  onChatSelect(chat.id)
                }}
                className="w-full text-left px-3 py-1.5 rounded-lg text-xs text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700 truncate transition mb-0.5"
              >
                {chat.title}
              </button>
            ))}
          </div>
        )}
      </nav>

      {/* 하단 */}
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

      {/* 접혔을 때 하단 아이콘만 */}
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