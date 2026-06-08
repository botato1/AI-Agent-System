import { useState, useEffect, useRef } from 'react'
import { nodes, links } from '../data/graphData'
import * as d3 from 'd3'
import GraphCanvas from '../components/Graph/GraphCanvas'
import SelectedDocument from '../components/Graph/SelectedDocument'
import DocumentList from '../components/Graph/DocumentList'

const colorPalette = ['#7c6af7', '#5b8af5', '#4caf82', '#e8a838', '#e05c5c', '#f472b6']
const getGroupColor = (group: number) => colorPalette[(group - 1) % colorPalette.length]

// const nodes = [
//   { id: '마케팅 전략 회의', group: 1, size: 20 },
//   { id: '광고 소재 제작', group: 1, size: 14 },
//   { id: 'A/B 테스트 계획', group: 1, size: 14 },
//   { id: '랜딩페이지 수정', group: 1, size: 12 },
//   { id: '개발 스프린트 회의', group: 2, size: 18 },
//   { id: '백엔드 API 설계', group: 2, size: 14 },
//   { id: '프론트엔드 구현', group: 2, size: 14 },
//   { id: '고객 미팅', group: 3, size: 16 },
//   { id: '요구사항 정리', group: 3, size: 12 },
//   { id: '제안서 작성', group: 3, size: 12 },
//   { id: '디자인 리뷰', group: 4, size: 14 },
//   { id: '성과 보고서 발표', group: 4, size: 14 },
// ]

// const links = [
//   { source: '마케팅 전략 회의', target: '광고 소재 제작', value: 0.9 },
//   { source: '마케팅 전략 회의', target: 'A/B 테스트 계획', value: 0.8 },
//   { source: '마케팅 전략 회의', target: '랜딩페이지 수정', value: 0.7 },
//   { source: '광고 소재 제작', target: 'A/B 테스트 계획', value: 0.6 },
//   { source: '개발 스프린트 회의', target: '백엔드 API 설계', value: 0.9 },
//   { source: '개발 스프린트 회의', target: '프론트엔드 구현', value: 0.8 },
//   { source: '백엔드 API 설계', target: '프론트엔드 구현', value: 0.7 },
//   { source: '고객 미팅', target: '요구사항 정리', value: 0.9 },
//   { source: '고객 미팅', target: '제안서 작성', value: 0.8 },
//   { source: '마케팅 전략 회의', target: '고객 미팅', value: 0.4 },
//   { source: '개발 스프린트 회의', target: '마케팅 전략 회의', value: 0.3 },
//   { source: '디자인 리뷰', target: '성과 보고서 발표', value: 0.8 },
//   { source: '디자인 리뷰', target: '마케팅 전략 회의', value: 0.5 },
//   { source: '성과 보고서 발표', target: '마케팅 전략 회의', value: 0.4 },
// ]

const groupLabels: Record<number, string> = {
  1: '마케팅', 2: '개발', 3: '영업', 4: '디자인',
}

interface GraphProps {
  onGoToAnalysis: () => void
}

export default function Graph({ onGoToAnalysis }: GraphProps) {
  const [selected, setSelected] = useState<string | null>(null)
  const [isDark, setIsDark] = useState(false)
  const [zoomLevel, setZoomLevel] = useState(1)
  const svgRef = useRef<SVGSVGElement>(null)
  const zoomRef = useRef<any>(null)

  useEffect(() => {
    const observer = new MutationObserver(() => {
      setIsDark(document.documentElement.classList.contains('dark'))
    })
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] })
    setIsDark(document.documentElement.classList.contains('dark'))
    return () => observer.disconnect()
  }, [])

  const connectedNodes = links
    .filter(l => l.source === selected || l.target === selected)
    .map(l => l.source === selected ? l.target : l.source)

  return (
    <div>
      {/* 헤더 */}
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="text-lg font-bold text-gray-800 dark:text-white">그래프 시각화</h1>
          <p className="text-xs text-gray-400 mt-1">문서 간 임베딩 유사도 기반 연관성 시각화</p>
        </div>
        <div className="flex gap-3">
          {Object.entries(groupLabels).map(([key, label]) => (
            <div key={key} className="flex items-center gap-1.5">
              <div className="w-2 h-2 rounded-full" style={{ background: getGroupColor(Number(key)) }} />
              <span className="text-xs text-gray-400">{label}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4">

        {/* 그래프 캔버스 */}
        <div className="col-span-2 relative">
         <div className="absolute top-3 right-3 z-10 flex flex-col gap-1.5">
  <button
    onClick={() => { if(zoomRef.current && svgRef.current) d3.select(svgRef.current).transition().call(zoomRef.current.scaleBy, 1.3) }}
    className="w-8 h-8 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg flex items-center justify-center text-gray-600 dark:text-gray-300 hover:bg-gray-50 text-sm font-bold shadow-sm"
  >+</button>
  <div className="w-8 h-6 flex items-center justify-center text-xs text-gray-400">{Math.round(zoomLevel * 100)}%</div>
  <button
    onClick={() => { if(zoomRef.current && svgRef.current) d3.select(svgRef.current).transition().call(zoomRef.current.scaleBy, 0.7) }}
    className="w-8 h-8 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg flex items-center justify-center text-gray-600 dark:text-gray-300 hover:bg-gray-50 text-sm font-bold shadow-sm"
  >−</button>
  <button
    onClick={() => { if(zoomRef.current && svgRef.current) d3.select(svgRef.current).transition().call(zoomRef.current.transform, d3.zoomIdentity) }}
    className="w-8 h-8 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg flex items-center justify-center text-gray-400 hover:bg-gray-50 text-xs shadow-sm"
  >↺</button>
</div>
          <div className="rounded-xl overflow-hidden border border-gray-100 dark:border-gray-800" style={{ height: '85vh' }}>
            <svg ref={svgRef} width="100%" height="100%" />
            <GraphCanvas
              nodes={nodes}
              links={links}
              isDark={isDark}
              getGroupColor={getGroupColor}
              onSelect={setSelected}
              onZoomChange={setZoomLevel}
              zoomRef={zoomRef}
              svgRef={svgRef}
            />
          </div>
        </div>

        {/* 사이드 패널 */}
 <div className="flex flex-col gap-3">
  <DocumentList
    nodes={nodes}
    selected={selected}
    onSelect={setSelected}
    getGroupColor={getGroupColor}
  />
{selected && (
  <SelectedDocument
    selected={selected}
    connectedNodes={connectedNodes}
    onGoToAnalysis={onGoToAnalysis}
  />
)}
</div>
      </div>
    </div>
  )
}