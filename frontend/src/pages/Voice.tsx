import { useState } from 'react'

interface VoiceFile {
  id: string
  name: string
  duration: string
  size: string
  uploadDate: string
}

const dummyFiles: VoiceFile[] = [
  { id: '1', name: '마케팅 전략 회의_2024-05-15.mp3', duration: '48:32', size: '76.4MB', uploadDate: '2024.05.15 14:30' },
  { id: '2', name: '개발 주간 회의_2024-05-14.wav', duration: '35:18', size: '54.1MB', uploadDate: '2024.05.14 10:15' },
  { id: '3', name: '고객 콜_김나연_2024-05-13.m4a', duration: '22:07', size: '32.6MB', uploadDate: '2024.05.13 16:45' },
]

interface Props {
  onAnalyze: (fileId: string) => void
}

export default function Voice({ onAnalyze }: Props) {
  // 선택된 파일 상태
  const [files, setFiles] = useState<VoiceFile[]>(dummyFiles)
  // 프롬프트 텍스트 상태
  const [prompt, setPrompt] = useState('')
  // 드래그 오버 상태
  const [isDragging, setIsDragging] = useState(false)

  // 파일 선택 핸들러 (더미)
  const handleFileSelect = () => {
    alert('파일 선택 (백엔드 연결 후 구현)')
  }

    // 드래그 이벤트
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }
  const handleDragLeave = () => setIsDragging(false)
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    // 백엔드 연결 후 구현
  }

  // 새로고침
  const handleRefresh = () => {
    setFiles([...dummyFiles])
  }

  return (
    <div className="flex-1 p-8 overflow-y-auto bg-white dark:bg-[#161616]">
      {/* 페이지 헤더 */}
      <div className="mb-6">
        <h1 className="text-xl font-medium text-gray-900 dark:text-white">음성 파일 관리</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          음성 파일을 업로드하고 분석 결과를 확인하세요.
        </p>
      </div>
      {/* 상단 2열: 업로드 + 프롬프트 */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        {/* 업로드 영역 */}
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className={`border-2 border-dashed rounded-xl p-8 flex flex-col items-center justify-center text-center transition-colors
            ${isDragging
              ? 'border-blue-400 bg-blue-50 dark:bg-blue-900/20'
              : 'border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-[#1c1a1a]'
            }`}
        >
          {/* 업로드 아이콘 */}
          <div className="w-14 h-14 rounded-full bg-blue-50 dark:bg-blue-900/30 flex items-center justify-center mb-4">
            <svg className="w-7 h-7 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
            </svg>
          </div>
          <p className="text-sm font-medium text-gray-700 dark:text-gray-200 mb-1">
            음성 파일을 드래그하거나 클릭하여 업로드
          </p>
          <p className="text-xs text-gray-400 dark:text-gray-500 mb-4">
            MP3, WAV, M4A, AAC 파일 지원 (최대 500MB)
          </p>
          <button
            onClick={handleFileSelect}
            className="px-5 py-2 bg-blue-500 hover:bg-blue-600 text-white text-sm rounded-lg transition-colors"
          >
            파일 선택
          </button>
          <p className="text-xs text-gray-400 dark:text-gray-500 mt-3">
            ⓘ 실시간 녹음 기능은 지원하지 않습니다.
          </p>
        </div>

        {/* 초기 프롬프트 입력 */}
        <div className="border border-gray-200 dark:border-gray-700 rounded-xl p-5 flex flex-col bg-white dark:bg-[#1c1a1a]">
          <h2 className="text-sm font-medium text-gray-800 dark:text-white mb-1">초기 분석 프롬프트</h2>
          <p className="text-xs text-gray-400 dark:text-gray-500 mb-3">
            AI가 분석 시 참고할 맥락이나 요청 사항을 입력하세요
          </p>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="예) 이 회의에서 결정된 액션 아이템과 담당자를 중심으로 요약해줘. 마케팅 전략 관련 내용을 특히 강조해줘."
            className="flex-1 resize-none text-sm bg-gray-50 dark:bg-[#161616] border border-gray-200 dark:border-gray-700 rounded-lg p-3 text-gray-700 dark:text-gray-300 placeholder-gray-300 dark:placeholder-gray-600 focus:outline-none focus:ring-1 focus:ring-blue-400 min-h-[120px]"
          />
          <div className="flex justify-end gap-2 mt-3">
            <button
              onClick={() => setPrompt('')}
              className="px-4 py-1.5 text-xs text-gray-500 dark:text-gray-400 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
            >
              초기화
            </button>
            <button
              className="px-4 py-1.5 text-xs text-white bg-blue-500 hover:bg-blue-600 rounded-lg transition-colors"
            >
              저장
            </button>
          </div>
        </div>
      </div>

      {/* 업로드된 파일 목록 */}
      <div className="border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-[#1c1a1a]">
        {/* 목록 헤더 */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100 dark:border-gray-700">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-gray-800 dark:text-white">업로드된 파일</span>
            <span className="text-xs px-2 py-0.5 bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400 rounded-full">
              {files.length}개
            </span>
          </div>
          <button
            onClick={handleRefresh}
            className="text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 flex items-center gap-1 transition-colors"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            새로고침
          </button>
        </div>

        {/* 테이블 헤더 */}
        <div className="grid grid-cols-[2fr_1fr_1fr_1fr_120px_32px] px-5 py-2 text-xs text-gray-400 dark:text-gray-500 border-b border-gray-100 dark:border-gray-700">
          <span>파일명</span>
          <span>길이</span>
          <span>크기</span>
          <span>업로드 날짜</span>
          <span>작업</span>
          <span></span>
        </div>

        {/* 파일 행 */}
        {files.map((file) => (
          <div
            key={file.id}
            className="grid grid-cols-[2fr_1fr_1fr_1fr_120px_32px] items-center px-5 py-3.5 border-b border-gray-50 dark:border-gray-800 last:border-none hover:bg-gray-50 dark:hover:bg-gray-800/40 transition-colors"
          >
            {/* 파일명 + 웨이브폼 */}
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-blue-50 dark:bg-blue-900/30 flex items-center justify-center flex-shrink-0">
                <svg className="w-4 h-4 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                    d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
                </svg>
              </div>
              <div>
                <p className="text-sm text-gray-800 dark:text-gray-200 font-medium truncate max-w-[200px]">
                  {file.name}
                </p>
                {/* 간단 웨이브폼 */}
                <div className="flex items-center gap-[2px] mt-1">
                  {Array.from({ length: 20 }).map((_, i) => (
                    <div
                      key={i}
                      className="w-[2px] bg-blue-300 dark:bg-blue-600 rounded-full"
                      style={{ height: `${4 + Math.sin(i * 0.8) * 4 + Math.random() * 4}px` }}
                    />
                  ))}
                </div>
              </div>
            </div>
            <span className="text-sm text-gray-600 dark:text-gray-400">{file.duration}</span>
            <span className="text-sm text-gray-600 dark:text-gray-400">{file.size}</span>
            <span className="text-sm text-gray-600 dark:text-gray-400">{file.uploadDate}</span>
            {/* 분석하기 버튼 */}
            <button
              onClick={() => onAnalyze(file.id)}
              className="px-4 py-1.5 text-xs font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
            >
              분석하기
            </button>
            {/* 더보기 */}
            <button className="text-gray-300 dark:text-gray-600 hover:text-gray-500 dark:hover:text-gray-400">
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                <path d="M12 5a1.5 1.5 0 110-3 1.5 1.5 0 010 3zm0 7a1.5 1.5 0 110-3 1.5 1.5 0 010 3zm0 7a1.5 1.5 0 110-3 1.5 1.5 0 010 3z" />
              </svg>
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}