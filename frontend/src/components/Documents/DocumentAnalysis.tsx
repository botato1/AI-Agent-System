//문서보관함 - 문서 분석 결과 보기
import { ArrowLeft, CheckCircle } from 'lucide-react'
import type { FileItem } from '../../data/documentsData'

type Props = {
  file: FileItem
  onBack: () => void
}

const dummyAnalysis: Record<number, {
  summary: string
  keywords: string[]
  tasks: { title: string; assignee: string; priority: 'high' | 'mid' | 'low' }[]
}> = {
  1: {
    summary: '마케팅 전략 회의에서 2분기 SNS 캠페인 방향을 확정하였습니다. 인스타그램 릴스 중심으로 콘텐츠를 제작하고, 타겟 연령대를 20~35세로 설정하는 방향으로 결정되었습니다.',
    keywords: ['SNS 캠페인', '인스타그램', '2분기', '타겟 마케팅', '콘텐츠 제작'],
    tasks: [
      { title: '인스타그램 릴스 콘텐츠 기획안 작성', assignee: '김나연', priority: 'high' },
      { title: '타겟 광고 예산 산정', assignee: '문지수', priority: 'high' },
      { title: '경쟁사 SNS 분석 리포트', assignee: '이승주', priority: 'mid' },
    ],
  },
  2: {
    summary: '개발 스프린트 회의에서 이번 주 핵심 목표를 파이프라인 연동으로 확정하였습니다. 백엔드 API 명세서를 먼저 완성한 후 프론트엔드와 연동하는 순서로 진행하기로 했습니다.',
    keywords: ['스프린트', '파이프라인', 'API 연동', '백엔드', '프론트엔드'],
    tasks: [
      { title: 'API 명세서 작성 완료', assignee: '문지수', priority: 'high' },
      { title: '파이프라인 UI 더미→실제 연동', assignee: '김나연', priority: 'high' },
      { title: 'LangGraph 워크플로우 테스트', assignee: '가동현', priority: 'mid' },
    ],
  },
}

const priorityColors = { high: 'bg-red-400', mid: 'bg-amber-400', low: 'bg-green-400' }
const priorityLabel = { high: '높음', mid: '보통', low: '낮음' }

export default function DocumentAnalysis({ file, onBack }: Props) {
  const analysis = dummyAnalysis[file.id]

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
        <h1 className="text-sm font-medium text-gray-700 dark:text-gray-200">{file.name}</h1>
        <span className="text-xs px-2 py-0.5 rounded-full bg-blue-50 dark:bg-blue-900/30 text-blue-400 ml-auto flex items-center gap-1">
          <CheckCircle size={11} /> 분석 완료
        </span>
      </div>

      {!analysis ? (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-600 p-12 text-center">
          <p className="text-gray-400 text-sm">분석 데이터가 없습니다.</p>
          <p className="text-gray-300 dark:text-gray-600 text-xs mt-1">백엔드 연동 후 표시됩니다.</p>
        </div>
      ) : (
        <div className="flex flex-col gap-4">
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-600 p-5">
            <p className="text-xs font-medium text-gray-400 mb-2">요약</p>
            <p className="text-sm text-gray-700 dark:text-gray-200 leading-7">{analysis.summary}</p>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-600 p-5">
            <p className="text-xs font-medium text-gray-400 mb-3">키워드</p>
            <div className="flex flex-wrap gap-2">
              {analysis.keywords.map((kw) => (
                <span key={kw} className="text-xs px-3 py-1 rounded-full bg-blue-50 dark:bg-blue-900/30 text-blue-500 dark:text-blue-400">{kw}</span>
              ))}
            </div>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-600 p-5">
            <p className="text-xs font-medium text-gray-400 mb-3">추출된 Task</p>
            <div className="flex flex-col gap-2">
              {analysis.tasks.map((task, i) => (
                <div key={i} className="flex items-center gap-3 p-3 rounded-lg border border-gray-100 dark:border-gray-700 bg-gray-50 dark:bg-gray-700/50">
                  <div className={`w-2 h-2 rounded-full flex-shrink-0 ${priorityColors[task.priority]}`} />
                  <span className="text-sm text-gray-700 dark:text-gray-200 flex-1">{task.title}</span>
                  <span className="text-xs text-gray-400 dark:text-gray-400 bg-white dark:bg-gray-700 px-2 py-0.5 rounded-full border border-gray-100 dark:border-gray-600">{task.assignee}</span>
                  <span className="text-xs text-gray-300 dark:text-gray-500">{priorityLabel[task.priority]}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}