//텍스트 탭 - 전체 대화 스크립트
import { useState } from 'react'

const scripts = [
  { speaker: '김나연', time: '00:00:00', text: '안녕하세요, 오늘 마케팅 전략 회의를 시작하겠습니다.' },
  { speaker: '박민수', time: '00:00:08', text: '지난 캠페인 성과부터 간단히 공유드릴게요.' },
  { speaker: '박민수', time: '00:00:20', text: '전체적으로 목표 대비 120%를 달성했고, 특히 유튜브 채널의 성과가 좋았습니다.' },
  { speaker: '이애전', time: '00:00:35', text: '인스타그램도 팔로워 증가율이 35%로도 높게 나왔습니다.' },
  { speaker: '김나연', time: '00:00:45', text: '잘됐네요. 그럼 신규 채널 확대 전략에 대해 논의해 볼까요.' },
  { speaker: '최지우', time: '00:01:02', text: '저는 유튜브 쇼츠 포맷을 추가로 활용하는 방안을 제안하고 싶습니다.' },
]

const speakerColors: Record<string, string> = {
  '김나연': 'text-indigo-500 dark:text-indigo-400',
  '박민수': 'text-blue-500 dark:text-blue-400',
  '이애전': 'text-violet-500 dark:text-violet-400',
  '최지우': 'text-teal-500 dark:text-teal-400',
}

export default function TabScript() {
  const [search, setSearch] = useState('')

    // 검색 필터
  const filtered = scripts.filter(s =>
    s.text.includes(search) || s.speaker.includes(search)
  )

  return (
    <div className="bg-white dark:bg-[#1c1a1a] rounded-xl border border-gray-100 dark:border-gray-700">
      {/* 검색 헤더 */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-gray-100 dark:border-gray-700">
        <div className="flex items-center gap-2 flex-1">
          <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="키워드를 입력하세요"
            className="flex-1 text-sm bg-transparent text-gray-700 dark:text-gray-300 placeholder-gray-300 dark:placeholder-gray-600 focus:outline-none"
          />
        </div>
        <div className="flex items-center gap-3">
          <button className="text-xs text-gray-500 dark:text-gray-400 border border-gray-200 dark:border-gray-700 px-3 py-1 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
            내보내기 ↓
          </button>
        </div>
      </div>

      {/* 스크립트 목록 */}
      <div className="p-5 flex flex-col gap-3 max-h-[400px] overflow-y-auto">
        {filtered.map((item, i) => (
          <div key={i} className="flex gap-4">
            <span className="text-xs text-gray-400 w-16 flex-shrink-0 mt-0.5">{item.time}</span>
            <div className="flex-1">
              <span className={`text-xs font-medium mr-2 ${speakerColors[item.speaker] ?? 'text-gray-500'}`}>
                {item.speaker}
              </span>
              <span className="text-xs text-gray-600 dark:text-gray-300 leading-relaxed">
                {item.text}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
