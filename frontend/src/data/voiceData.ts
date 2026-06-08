export type VoiceItem = {
  id: number
  name: string
  type: 'WAV' | 'MP3' | 'M4A'
  size: string
  date: string
  duration: string
}

export const voices: VoiceItem[] = [
  { id: 1, name: '마케팅 전략 회의', type: 'WAV', size: '28.7MB', date: '2024.05.20 14:00', duration: '42:30' },
  { id: 2, name: '개발 스프린트 회의', type: 'MP3', size: '15.2MB', date: '2024.05.18 10:00', duration: '28:15' },
  { id: 3, name: '고객 미팅 녹음', type: 'WAV', size: '35.1MB', date: '2024.05.16 09:00', duration: '51:20' },
  { id: 4, name: '팀 빌딩 회의', type: 'M4A', size: '12.4MB', date: '2024.05.14 11:00', duration: '22:10' },
  { id: 5, name: '신제품 기획 회의', type: 'MP3', size: '18.9MB', date: '2024.05.10 08:00', duration: '33:45' },
]

export const typeColors: Record<string, string> = {
  WAV:  'bg-red-100 text-red-500 dark:bg-red-900/30 dark:text-red-400',
  MP3: 'bg-blue-100 text-blue-500 dark:bg-blue-900/30 dark:text-blue-400',
  M4A:  'bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-300',
}

export const FILTERS = ['전체', 'WAV', 'MP3', 'M4A'] as const