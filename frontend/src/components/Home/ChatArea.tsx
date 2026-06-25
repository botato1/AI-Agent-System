import { useState, useEffect, useRef } from 'react'
import { Send } from 'lucide-react'
import ReactMarkdown from 'react-markdown'

const BASE_URL = import.meta.env.VITE_API_URL

const suggestions = [
  '이 문서 요약해줘',
  '주요 할 일 정리해줘',
  '담당자별 업무 알려줘',
  '중요한 내용 알려줘',
]

interface ChatTask {
  task_id: string
  task: string
  assignee: string | null
  deadline: string | null
  status: string
  priority?: string
}

interface Message {
  id: string
  role: 'user' | 'assistant'
  text: string
  tasks?: ChatTask[]
}

interface Props {
  activeRoomId: string | null
  setActiveRoomId: (id: string) => void
  onRoomCreated: () => void
  targetFilename?: string | null
  onGoToAnalysis?: () => void
}

const TASKS_KEY = 'chatTasks'
const ADDED_KEY = 'addedTaskIds'

// 새로고침해도 유지되도록 채팅방별 업무 목록을 localStorage에 저장 (task_id 기준 중복 제거)
const saveRoomTasks = (roomId: string, tasks: ChatTask[]) => {
  try {
    const all = JSON.parse(localStorage.getItem(TASKS_KEY) ?? '{}')
    const existing: ChatTask[] = all[roomId] ?? []
    const merged = [...existing]
    tasks.forEach(t => {
      if (!merged.find(e => e.task_id === t.task_id)) merged.push(t)
    })
    all[roomId] = merged
    localStorage.setItem(TASKS_KEY, JSON.stringify(all))
  } catch {}
}

const loadRoomTasks = (roomId: string): ChatTask[] => {
  try {
    const all = JSON.parse(localStorage.getItem(TASKS_KEY) ?? '{}')
    return all[roomId] ?? []
  } catch { return [] }
}

const saveAddedIds = (ids: Set<string>) => {
  try {
    localStorage.setItem(ADDED_KEY, JSON.stringify([...ids]))
  } catch {}
}

const loadAddedIds = (): Set<string> => {
  try {
    const saved = localStorage.getItem(ADDED_KEY)
    return saved ? new Set(JSON.parse(saved)) : new Set()
  } catch { return new Set() }
}

export default function ChatArea({ activeRoomId, setActiveRoomId, onRoomCreated, targetFilename, onGoToAnalysis }: Props) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [addedTaskIds, setAddedTaskIds] = useState<Set<string>>(loadAddedIds)
  const bottomRef = useRef<HTMLDivElement>(null)
  const abortControllerRef = useRef<AbortController | null>(null)
  // loading state는 비동기라 useEffect 안에서 즉시 참조가 안 되므로 ref로 동기 추적
  const loadingRef = useRef(false)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    if (!activeRoomId) {
      setMessages([])
      return
    }
    // 전송 처리 중에는 handleSend에서 setActiveRoomId가 호출되면서 이 effect도 같이 실행됨
    // → 이때 메시지를 덮어쓰면 방금 보낸 메시지가 사라지므로 가드
    if (loadingRef.current) return

    fetch(`${BASE_URL}/api/conversations/${activeRoomId}/messages`)
      .then(r => r.json())
      .then(data => {
        const msgs: Message[] = (data.messages ?? []).map((m: any) => ({
          id: m.message_id,
          role: m.role as 'user' | 'assistant',
          text: m.content,
        }))
        // 업무 목록은 백엔드 메시지 응답에 포함되지 않아 localStorage에서 복원,
        // 가장 최근 assistant 메시지에 다시 매칭
        const roomTasks = loadRoomTasks(activeRoomId)
        if (roomTasks.length > 0) {
          const lastAssistantIdx = [...msgs].reverse().findIndex(m => m.role === 'assistant')
          if (lastAssistantIdx !== -1) {
            const realIdx = msgs.length - 1 - lastAssistantIdx
            msgs[realIdx].tasks = roomTasks
          }
        }
        setMessages(msgs)
      })
      .catch(err => console.error('기록 불러오기 실패:', err))
  }, [activeRoomId])

  const createRoom = async (title: string): Promise<string> => {
    const res = await fetch(`${BASE_URL}/api/conversations`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title }),
    })
    if (!res.ok) throw new Error('채팅방 생성 실패')
    const data = await res.json()
    return data.room_id
  }

  const handleAddTask = async (task: ChatTask) => {
    try {
      const res = await fetch(`${BASE_URL}/api/tasks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task: task.task,
          assignee: task.assignee ?? null,
          deadline: task.deadline ?? null,
          status: 'todo',
          priority: task.priority ?? 'medium',
          room_id: activeRoomId,
          document_id: null, // 채팅 기반 업무는 특정 문서와 연결하지 않음
        }),
      })
      if (!res.ok) throw new Error()
      const data = await res.json()
      if (!data.error) {
        setAddedTaskIds(prev => {
          const next = new Set(prev).add(task.task_id)
          saveAddedIds(next)
          return next
        })
      }
    } catch {}
  }

  const handleSend = async (overrideText?: string) => {
    const userText = (overrideText ?? input).trim()
    if (!userText || loading) return

    setInput('')
    setLoading(true)
    loadingRef.current = true

    let roomId = activeRoomId
    if (!roomId) {
      try {
        roomId = await createRoom(userText)
        setActiveRoomId(roomId)
        onRoomCreated()
      } catch {
        setLoading(false)
        loadingRef.current = false
        return
      }
    }

    const loadingMsgId = `loading_${Date.now()}`
    setMessages(prev => [
      ...prev,
      { id: `user_${Date.now()}`, role: 'user', text: userText },
      { id: loadingMsgId, role: 'assistant', text: '...' },
    ])

    try {
      abortControllerRef.current = new AbortController()

      const res = await fetch(`${BASE_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          room_id: roomId,
          content: userText,
          source: targetFilename ? 'pdf' : 'text',
        }),
        signal: abortControllerRef.current.signal,
      })

      if (!res.ok) throw new Error(`HTTP error: ${res.status}`)
      const data = await res.json()
      const answerText = data.answer ?? data.error ?? '응답을 받지 못했어요.'
      const tasks = Array.isArray(data.tasks) && data.tasks.length > 0 ? data.tasks : undefined

      if (tasks && roomId) saveRoomTasks(roomId, tasks)

      setMessages(prev =>
        prev.map(m =>
          m.id === loadingMsgId ? { ...m, text: answerText, tasks } : m
        )
      )
    } catch (err: any) {
      if (err.name === 'AbortError') {
        // 사용자가 직접 중지한 경우는 에러로 취급하지 않고 로딩 메시지만 제거
        setMessages(prev => prev.filter(m => m.id !== loadingMsgId))
      } else {
        setMessages(prev =>
          prev.map(m =>
            m.id === loadingMsgId
              ? { ...m, text: '오류가 발생했어요. 백엔드 연결을 확인해주세요.' }
              : m
          )
        )
      }
    } finally {
      setLoading(false)
      loadingRef.current = false
      onRoomCreated()
    }
  }

  const started = messages.length > 0

  return (
    <div className="flex-1 flex flex-col">

      {targetFilename && (
        <div className="mb-3">
          <button
            onClick={() => onGoToAnalysis?.()}
            className="flex items-center gap-2 text-xs text-blue-500 border border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-900/30 px-4 py-2 rounded-xl hover:bg-blue-100 dark:hover:bg-blue-900/50 transition"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            📄 {targetFilename} 분석 결과 보기 →
          </button>
        </div>
      )}

      {!started && (
        <div className="flex-1 flex flex-col items-center justify-center gap-6">
          <div className="text-center">
            <h2 className="text-2xl font-bold text-gray-800 dark:text-white mb-2">
              무엇을 도와드릴까요?
            </h2>
            <p className="text-sm text-gray-400">
              회의록 분석, 업무 정리, 일정 관리 등 무엇이든 물어보세요
            </p>
          </div>
          <div className="grid grid-cols-2 gap-3 w-full max-w-lg">
            {suggestions.map((s, i) => (
              <button
                key={i}
                onClick={() => handleSend(s)}
                className="text-left p-3 bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 rounded-xl text-xs text-gray-600 dark:text-gray-300 hover:border-blue-300 dark:hover:border-blue-700 hover:text-blue-500 transition"
              >
                {s}
              </button>
            ))}
          </div>
        </div>
      )}

      {started && (
        <div className="flex-1 overflow-y-auto flex flex-col gap-4 mb-4 pr-1">
          {messages.map((msg) => (
            <div key={msg.id} className={`group flex gap-3 items-start ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>

              <div className={`w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 ${
                msg.role === 'assistant' ? 'bg-blue-600' : 'bg-gray-200 dark:bg-gray-600'
              }`}>
                <span className={`text-xs font-medium ${
                  msg.role === 'assistant' ? 'text-white' : 'text-gray-600 dark:text-gray-200'
                }`}>
                  {msg.role === 'assistant' ? 'AI' : '나'}
                </span>
              </div>

              <div className="flex flex-col gap-2 max-w-lg">
                <div className={`px-4 py-3 rounded-2xl text-sm leading-relaxed ${
                  msg.role === 'assistant'
                    ? 'bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 text-gray-700 dark:text-gray-200'
                    : 'bg-blue-600 text-white'
                }`}>
                  {msg.text === '...' && loading
                    ? <span className="animate-pulse text-gray-400">응답 생성 중...</span>
                    : msg.role === 'user'
                      ? msg.text
                      : (
                        <div className="prose prose-sm dark:prose-invert max-w-none prose-p:my-0.5 prose-li:my-0 prose-ul:my-1 prose-ol:my-1 [&_*]:text-gray-700 dark:[&_*]:text-gray-200">
                          <ReactMarkdown>{msg.text}</ReactMarkdown>
                        </div>
                      )
                  }
                </div>

                {msg.role === 'assistant' && msg.tasks && msg.tasks.length > 0 && (
                  <div className="bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 rounded-2xl p-3 flex flex-col gap-2">
                    <p className="text-[10px] text-gray-400 dark:text-gray-500 font-medium">업무에 추가할 항목을 선택하세요</p>
                    {msg.tasks.map((task) => {
                      const isAdded = addedTaskIds.has(task.task_id)
                      return (
                        <div key={task.task_id} className="flex items-center justify-between gap-2 py-1.5 border-b border-gray-50 dark:border-gray-700 last:border-0">
                          <div className="flex flex-col gap-0.5">
                            <span className="text-xs text-gray-700 dark:text-gray-200">{task.task}</span>
                            <span className="text-[10px] text-gray-400">
                              {task.assignee && `${task.assignee}`}
                              {task.assignee && task.deadline && ' · '}
                              {task.deadline && `${task.deadline}`}
                            </span>
                          </div>
                          <button
                            onClick={() => handleAddTask(task)}
                            disabled={isAdded}
                            className={`flex-shrink-0 text-[10px] px-3 py-1 rounded-full border transition ${
                              isAdded
                                ? 'border-green-300 text-green-500 dark:border-green-700 dark:text-green-400'
                                : 'border-blue-300 text-blue-500 hover:bg-blue-50 dark:border-blue-700 dark:text-blue-400 dark:hover:bg-blue-900/20'
                            }`}
                          >
                            {isAdded ? '✓ 추가됨' : '+ 추가'}
                          </button>
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>

              <button
                onClick={async () => {
                  if (!confirm('이 메시지를 삭제할까요?')) return
                  await fetch(`${BASE_URL}/api/messages/${msg.id}`, { method: 'DELETE' })
                  setMessages(prev => prev.filter(m => m.id !== msg.id))
                }}
                className={`transition self-center flex-shrink-0 text-gray-400 dark:text-gray-500 hover:text-red-400 dark:hover:text-red-400 ${
                  msg.role === 'user' ? 'mr-1' : 'ml-1'
                }`}
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="3 6 5 6 21 6"/>
                  <path d="M19 6l-1 14H6L5 6"/>
                  <path d="M10 11v6"/>
                  <path d="M14 11v6"/>
                  <path d="M9 6V4h6v2"/>
                </svg>
              </button>
            </div>
          ))}
          <div ref={bottomRef} />
        </div>
      )}

      {started && (
        <div className="flex gap-2 mb-3 flex-wrap">
          {suggestions.map((s, i) => (
            <button
              key={i}
              onClick={() => handleSend(s)}
              className="text-xs text-blue-500 border border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-900/30 px-3 py-1.5 rounded-full hover:bg-blue-100 dark:hover:bg-blue-900/50 transition"
            >
              {s}
            </button>
          ))}
        </div>
      )}

      <div className="flex gap-2 bg-gray-100 dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-2xl p-2 shadow-sm">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              handleSend()
            }
          }}
          placeholder="메시지를 입력하세요... (Enter로 전송)"
          className="flex-1 text-sm text-gray-700 dark:text-gray-200 placeholder-gray-400 dark:placeholder-gray-500 bg-transparent resize-none outline-none px-2 py-1 max-h-32"
          rows={1}
        />
        <button
          onClick={loading ? () => abortControllerRef.current?.abort() : () => handleSend()}
          className={`w-8 h-8 rounded-xl flex items-center justify-center transition flex-shrink-0 self-end ${
            loading ? 'bg-red-500 hover:bg-red-600' : input.trim() ? 'bg-blue-600 hover:bg-blue-700' : 'bg-gray-100 dark:bg-gray-700'
          }`}
        >
          {loading ? (
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="white">
              <rect x="6" y="6" width="12" height="12"/>
            </svg>
          ) : (
            <Send size={14} className={input.trim() ? 'text-white' : 'text-gray-300'} />
          )}
        </button>
      </div>
    </div>
  )
}