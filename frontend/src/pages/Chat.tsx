import { useState } from 'react'
import { Send, Plus } from 'lucide-react'

const initialMessages = [
  { id: 1, role: 'assistant', text: '안녕하세요! 저는 Agentra AI Assistant예요. 회의록 분석, 업무 정리, 이메일 초안 작성 등 무엇이든 도와드릴게요 😊' },
  { id: 2, role: 'user', text: '오늘 회의에서 나온 마케팅 전략 회의 요약해줘' },
  { id: 3, role: 'assistant', text: '마케팅 전략 회의 (2024.05.20) 요약이에요:\n\n1. 광고 소재 3종 제작 → 김나연 (5월 25일)\n2. A/B 테스트 계획 수립 → 이지원 (5월 26일)\n3. 랜딩페이지 디자인 수정 → 박민수 (5월 21일)\n4. 성과 측정 지표 정의 → 박민수 (5월 23일)\n\n다음 회의는 5월 27일 (월)로 예정되어 있어요.' },
]

const suggestions = ['이메일 초안 작성해줘', '담당자별 업무 정리해줘', '다음 회의 일정 잡아줘', '성과 지표 추천해줘']

export default function Chat() {
  const [messages, setMessages] = useState(initialMessages)
  const [input, setInput] = useState('')

  const handleSend = () => {
    if (!input.trim()) return
    setMessages(prev => [
      ...prev,
      { id: prev.length + 1, role: 'user', text: input },
      { id: prev.length + 2, role: 'assistant', text: '네, 말씀하신 내용을 처리하고 있어요. 잠시만 기다려주세요! 🤖' },
    ])
    setInput('')
  }

  return (
    <div className="flex flex-col h-[calc(100vh-80px)]">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 bg-blue-600 rounded-lg flex items-center justify-center">
            <span className="text-white text-xs font-bold">AI</span>
          </div>
          <h1 className="text-lg font-bold text-gray-800 dark:text-white">AI Assistant</h1>
        </div>
        <button className="flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400 border border-gray-200 dark:border-gray-600 px-3 py-1.5 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700">
          <Plus size={13} /> 새 대화
        </button>
      </div>

      <div className="flex-1 overflow-y-auto flex flex-col gap-4 mb-4">
        {messages.map((msg) => (
          <div key={msg.id} className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
            <div className={`w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 ${msg.role === 'assistant' ? 'bg-blue-600' : 'bg-gray-200 dark:bg-gray-600'}`}>
              <span className={`text-xs font-medium ${msg.role === 'assistant' ? 'text-white' : 'text-gray-600 dark:text-gray-200'}`}>
                {msg.role === 'assistant' ? 'AI' : '나'}
              </span>
            </div>
            <div className={`max-w-md px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-line ${
              msg.role === 'assistant'
                ? 'bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 text-gray-700 dark:text-gray-200'
                : 'bg-blue-600 text-white'
            }`}>
              {msg.text}
            </div>
          </div>
        ))}
      </div>

      <div className="flex gap-2 mb-3 flex-wrap">
        {suggestions.map((s, i) => (
          <button key={i} onClick={() => setInput(s)} className="text-xs text-blue-500 border border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-900/30 px-3 py-1.5 rounded-full hover:bg-blue-100 dark:hover:bg-blue-900/50 transition">
            {s}
          </button>
        ))}
      </div>

      <div className="flex gap-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-2xl p-2">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() } }}
          placeholder="메시지를 입력하세요... (Enter로 전송)"
          className="flex-1 text-sm text-gray-700 dark:text-gray-200 placeholder-gray-300 dark:placeholder-gray-600 bg-transparent resize-none outline-none px-2 py-1 max-h-32"
          rows={1}
        />
        <button
          onClick={handleSend}
          className={`w-8 h-8 rounded-xl flex items-center justify-center transition flex-shrink-0 self-end ${input.trim() ? 'bg-blue-600 hover:bg-blue-700' : 'bg-gray-100 dark:bg-gray-700'}`}
        >
          <Send size={14} className={input.trim() ? 'text-white' : 'text-gray-300'} />
        </button>
      </div>
    </div>
  )
}