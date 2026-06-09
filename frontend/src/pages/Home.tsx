import ChatArea from '../components/home/ChatArea'

interface HomeProps {
  selectedChatId: number | null
  onRoomCreated: () => void
  onSelectRoom: (room_id: string) => void
  activeRoomId: string | null
  setActiveRoomId: (id: string | null) => void
  targetFilename: string | null
}

export default function Home({ selectedChatId, onRoomCreated, onSelectRoom, activeRoomId, setActiveRoomId, targetFilename }: HomeProps) {
  return (
    <div className="flex flex-col h-[calc(100vh-48px)]">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-xl font-bold text-gray-800 dark:text-white">안녕하세요, 김나연님! 👋</h1>
          <p className="text-sm text-gray-400 mt-1">Agentra가 오늘도 당신의 업무를 스마트하게 도와드릴게요.</p>
        </div>
        <button
          onClick={() => setActiveRoomId(null)}
          className="flex items-center gap-1.5 text-xs text-white bg-blue-600 px-3 py-2 rounded-lg hover:bg-blue-700 transition"
        >
          + 새 채팅
        </button>
      </div>
      <div className="flex gap-6 flex-1 min-h-0">
        <ChatArea
          activeRoomId={activeRoomId}
          setActiveRoomId={setActiveRoomId}
          onRoomCreated={onRoomCreated}
          targetFilename={targetFilename}
        />
      </div>
    </div>
  )
}