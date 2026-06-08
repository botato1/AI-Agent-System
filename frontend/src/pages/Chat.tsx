import { useState, useEffect } from 'react'
import RecentList from '../components/home/RecentList'
import ChatArea from '../components/home/ChatArea'

const BASE_URL = 'http://192.168.0.235:8000'

export interface Conversation {
  room_id: string
  title: string
  created_at: string
  updated_at: string
}

export default function Chat() {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [activeRoomId, setActiveRoomId] = useState<string | null>(null)

  const fetchConversations = async () => {
    try {
      const res = await fetch(`${BASE_URL}/api/conversations`)
      const data = await res.json()
      setConversations(data.conversations ?? [])
    } catch (err) {
      console.error('목록 조회 실패:', err)
    }
  }

  useEffect(() => {
    fetchConversations()
  }, [])

  return (
    <div className="flex gap-4 h-[calc(100vh-80px)]">
      <RecentList
        conversations={conversations}
        activeRoomId={activeRoomId}
        onSelect={(room_id) => setActiveRoomId(room_id)}
        onNewChat={() => setActiveRoomId(null)}
      />
      <ChatArea
        activeRoomId={activeRoomId}
        setActiveRoomId={setActiveRoomId}
        onRoomCreated={fetchConversations}
      />
    </div>
  )
}