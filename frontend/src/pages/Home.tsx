import ChatArea from '../components/home/ChatArea'
import RecentList from '../components/home/RecentList'

interface HomeProps {
  selectedChatId: number | null
}

export default function Home({ selectedChatId }: HomeProps) {
  return (
    <div className="flex flex-col h-[calc(100vh-48px)]">
      <div className="mb-4">
        <h1 className="text-xl font-bold text-gray-800 dark:text-white">안녕하세요, 김나연님! 👋</h1>
        <p className="text-sm text-gray-400 mt-1">Agentra가 오늘도 당신의 업무를 스마트하게 도와드릴게요.</p>
      </div>
      <div className="flex gap-6 flex-1 min-h-0">
        <ChatArea />
        <RecentList />
      </div>
    </div>
  )
}