import { useState } from 'react'
import { Send } from 'lucide-react'

const suggestions = [
  '마케팅 전략 회의 요약해줘',
  '이번 주 할 일 정리해줘',
  '담당자별 업무 알려줘',
  '다음 회의 일정 잡아줘',
]

export default function ChatArea() {
  const [messages, setMessages] = useState<{ id: number; role: string; text: string }[]>([])
  const [input, setInput] = useState('')
  const [started, setStarted] = useState(false)

  const handleSend = () => {
    if (!input.trim()) return
    setStarted(true)
    setMessages(prev => [
      ...prev,
      { id: prev.length + 1, role: 'user', text: input },
      { id: prev.length + 2, role: 'assistant', text: '네, 말씀하신 내용을 처리하고 있어요. 잠시만 기다려주세요! 🤖' },
    ])
    setInput('')
  }

  return (
    <div className="flex-1 flex flex-col">

      {/* 채팅 시작 전 인사말 */}
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

          {/* 추천 질문 카드 */}
          <div className="grid grid-cols-2 gap-3 w-full max-w-lg">
            {suggestions.map((s, i) => (
              <button
                key={i}
                onClick={() => setInput(s)}
                className="text-left p-3 bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 rounded-xl text-xs text-gray-600 dark:text-gray-300 hover:border-blue-300 dark:hover:border-blue-700 hover:text-blue-500 transition"
              >
                {s}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* 채팅 시작 후 메시지 */}
      {started && (
        <div className="flex-1 overflow-y-auto flex flex-col gap-4 mb-4 pr-1">
          {messages.map((msg) => (
            <div key={msg.id} className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
              <div className={`w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 ${
                msg.role === 'assistant' ? 'bg-blue-600' : 'bg-gray-200 dark:bg-gray-600'
              }`}>
                <span className={`text-xs font-medium ${
                  msg.role === 'assistant' ? 'text-white' : 'text-gray-600 dark:text-gray-200'
                }`}>
                  {msg.role === 'assistant' ? 'AI' : '나'}
                </span>
              </div>
              <div className={`max-w-lg px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-line ${
                msg.role === 'assistant'
                  ? 'bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 text-gray-700 dark:text-gray-200'
                  : 'bg-blue-600 text-white'
              }`}>
                {msg.text}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 추천 질문 (채팅 시작 후) */}
      {started && (
        <div className="flex gap-2 mb-3 flex-wrap">
          {suggestions.map((s, i) => (
            <button
              key={i}
              onClick={() => setInput(s)}
              className="text-xs text-blue-500 border border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-900/30 px-3 py-1.5 rounded-full hover:bg-blue-100 dark:hover:bg-blue-900/50 transition"
            >
              {s}
            </button>
          ))}
        </div>
      )}

      {/* 입력창 */}
      <div className="flex gap-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-2xl p-2">
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
          className="flex-1 text-sm text-gray-700 dark:text-gray-200 placeholder-gray-300 dark:placeholder-gray-600 bg-transparent resize-none outline-none px-2 py-1 max-h-32"
          rows={1}
        />
        <button
          onClick={handleSend}
          className={`w-8 h-8 rounded-xl flex items-center justify-center transition flex-shrink-0 self-end ${
            input.trim() ? 'bg-blue-600 hover:bg-blue-700' : 'bg-gray-100 dark:bg-gray-700'
          }`}
        >
          <Send size={14} className={input.trim() ? 'text-white' : 'text-gray-300'} />
        </button>
      </div>

    </div>
  )
}