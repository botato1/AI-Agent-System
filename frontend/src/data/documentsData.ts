export type FileItem = {
  id: number
  name: string
  type: 'PDF' | 'DOCX' | 'TXT'
  size: string
  date: string
  icon: 'pdf' | 'docx' | 'txt'
}

export const files: FileItem[] = [
  { id: 1, name: '마케팅 전략 회의.pdf',   type: 'PDF',  size: '2.4MB', date: '2024.05.20 14:00', icon: 'pdf' },
  { id: 2, name: '개발 스프린트 회의.pdf', type: 'PDF',  size: '3.2MB', date: '2024.05.18 10:00', icon: 'pdf' },
  { id: 3, name: '고객 미팅 회의록.docx',  type: 'DOCX', size: '1.2MB', date: '2024.05.16 09:00', icon: 'docx' },
  { id: 4, name: '신제품 기획 회의.pdf',   type: 'PDF',  size: '2.1MB', date: '2024.05.14 11:00', icon: 'pdf' },
  { id: 5, name: '팀 빌딩 행사 계획.docx', type: 'DOCX', size: '0.8MB', date: '2024.05.10 08:00', icon: 'docx' },
  { id: 6, name: '회의 메모.txt',          type: 'TXT',  size: '0.1MB', date: '2024.05.08 15:29', icon: 'txt' },
]

export const iconColors: Record<string, string> = {
  pdf:  'bg-indigo-50 text-[#818cf8] dark:bg-[#222] dark:text-[#818cf8]',
  docx: 'bg-emerald-50 text-[#34d399] dark:bg-[#222] dark:text-[#34d399]',
  txt:  'bg-orange-50 text-[#fb923c] dark:bg-[#222] dark:text-[#fb923c]',
}


export const typeColors: Record<string, string> = {
  PDF:  'text-[#818cf8]',
  DOCX: 'text-[#34d399]',
  TXT:  'text-[#fb923c]',
}

export const FILTERS = ['전체', 'PDF', 'DOCX', 'TXT'] as const