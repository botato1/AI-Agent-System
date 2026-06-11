//발언자 탭 - 발언자별 비율 상세
const speakers = [
  { name: '김나연', percent: 35, time: '17:02', color: 'bg-indigo-500' },
  { name: '박민수', percent: 28, time: '13:36', color: 'bg-blue-400' },
  { name: '이애전', percent: 22, time: '10:41', color: 'bg-violet-400' },
  { name: '최지우', percent: 15, time: '07:13', color: 'bg-teal-400' },
]

export default function TabSpeakers() {
  // 도넛 차트 SVG 계산
  const radius = 40
  const cx = 60
  const cy = 60
  const circumference = 2 * Math.PI * radius
  let offset = 0

  const segments = speakers.map(s => {
    const dash = (s.percent / 100) * circumference
    const seg = { ...s, dash, offset }
    offset += dash
    return seg
  })

  const colorMap: Record<string, string> = {
    'bg-indigo-500': '#6366f1',
    'bg-blue-400': '#60a5fa',
    'bg-violet-400': '#a78bfa',
    'bg-teal-400': '#2dd4bf',
  }
    
 return (
    <div className="bg-white dark:bg-[#1c1a1a] rounded-xl border border-gray-100 dark:border-gray-700 p-5">
      <h3 className="text-sm font-medium text-gray-700 dark:text-gray-200 mb-4">발언자 비중</h3>

       {/* 도넛 차트 */}
      <div className="flex justify-center mb-4">
        <svg width="120" height="120" viewBox="0 0 120 120">
          {segments.map((s, i) => (
            <circle
              key={i}
              cx={cx} cy={cy} r={radius}
              fill="none"
              stroke={colorMap[s.color]}
              strokeWidth="18"
              strokeDasharray={`${s.dash} ${circumference - s.dash}`}
              strokeDashoffset={-s.offset}
              style={{ transform: 'rotate(-90deg)', transformOrigin: '60px 60px' }}
            />
          ))}
        </svg>
      </div>

      {/* 범례 */}
      <div className="flex flex-col gap-2">
        {speakers.map((s, i) => (
          <div key={i} className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className={`w-2.5 h-2.5 rounded-full ${s.color}`} />
              <span className="text-xs text-gray-600 dark:text-gray-300">{s.name}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-gray-700 dark:text-gray-200">{s.percent}%</span>
              <span className="text-xs text-gray-400">({s.time})</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

