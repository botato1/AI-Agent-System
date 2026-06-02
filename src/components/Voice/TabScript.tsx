//텍스트 탭 - 전체 대화 스크립트
export default function TabScript() {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 p-6">
      <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-200 mb-4">전체 텍스트</h3>
      <div className="flex flex-col gap-4">
        {[
          { speaker: '김나연', time: '00:00', text: '안녕하세요, 오늘 마케팅 전략 회의 시작하겠습니다.' },
          { speaker: '이지원', time: '02:15', text: '네, 저는 A/B 테스트 관련해서 제안드릴 내용이 있는데요.' },
          { speaker: '박민수', time: '05:30', text: '디자인 수정 건은 제가 담당하겠습니다. 5월 21일까지 완료할 수 있을 것 같습니다.' },
          { speaker: '김나연', time: '08:45', text: '좋습니다. 그러면 광고 소재 3종 제작은 제가 맡고, 일정은 5월 25일로 잡겠습니다.' },
        ].map((item, i) => (
          <div key={i} className="flex gap-3">
            <div className="flex-shrink-0 text-right w-12">
              <span className="text-xs text-gray-400">{item.time}</span>
            </div>
            <div className="flex-1">
              <span className="text-xs font-semibold text-blue-600 dark:text-blue-400 mr-2">{item.speaker}</span>
              <span className="text-xs text-gray-600 dark:text-gray-300">{item.text}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}