//문서보관함 원본 보기
import { ArrowLeft, FileText, File } from 'lucide-react'
import type { FileItem } from '../../data/documentsData'

type Props = {
  file: FileItem
  onBack: () => void
}

const dummyContent: Record<string, string> = {
  pdf: `회의 일시: 2024년 5월 20일 14:00
참석자: 김나연, 가동현, 문지수, 이승주

1. 안건: AI Agent 플랫폼 MVP 범위 확정
   - 파이프라인 핵심 기능 우선 개발
   - 문서 업로드 → 요약 → Task 추출 순서로 진행
   - 6월 2주차 완료 목표

2. 백엔드-프론트 API 명세 공유
   - 이번 주 내로 문서 작성 완료
   - Notion에 공유 예정

3. 다음 회의: 5월 27일 10:00`,
  docx: `프로젝트 기획서

작성일: 2024년 5월 16일
작성자: 문지수

개요
본 문서는 AI 업무 자동화 Agent 플랫폼 Agentra의 기획 내용을 담고 있습니다.

목표
- 회의록, 문서, 음성 파일을 AI가 자동 분석
- Task 자동 생성 및 담당자 배분
- Notion 자동 저장`,
  txt: `팀 미팅 메모 - 2024.05.08

- 각자 진행 상황 공유
- 가동현: LangGraph 기본 구조 완성
- 문지수: FastAPI 라우터 설정 완료
- 김나연: 홈/파이프라인 UI 완성`,
}

export default function DocumentOriginal({ file, onBack }: Props) {
  const content = dummyContent[file.icon] ?? '내용을 불러올 수 없습니다.'

  return (
    <div>
      <div className="flex items-center gap-3 mb-5">
        <button
          onClick={onBack}
          className="flex items-center gap-1.5 text-sm text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition"
        >
          <ArrowLeft size={16} /> 목록으로
        </button>
        <span className="text-gray-200 dark:text-gray-700">|</span>
        <div className="flex items-center gap-2">
          <FileText size={15} className="text-gray-400" />
          <h1 className="text-sm font-medium text-gray-700 dark:text-gray-200">{file.name}</h1>
        </div>
        <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-400 dark:text-gray-400 ml-auto">
          원본 파일
        </span>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-600 p-8 min-h-[500px]">
        <div className="flex items-center gap-3 mb-6 pb-4 border-b border-gray-100 dark:border-gray-700">
          <div className="w-10 h-10 rounded-xl bg-red-50 dark:bg-red-900/30 flex items-center justify-center">
            <File size={18} className="text-red-400" />
          </div>
          <div>
            <p className="text-sm font-medium text-gray-700 dark:text-gray-200">{file.name}</p>
            <p className="text-xs text-gray-400 dark:text-gray-500">{file.size} · {file.date}</p>
          </div>
        </div>
        <pre className="text-sm text-gray-700 dark:text-gray-300 leading-7 whitespace-pre-wrap font-sans">
          {content}
        </pre>
      </div>
    </div>
  )
}