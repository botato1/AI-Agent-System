import { useEffect, useRef, useState } from 'react'
import * as d3 from 'd3'

const nodes = [
  { id: '마케팅 전략 회의', group: 1, size: 20 },
  { id: '광고 소재 제작', group: 1, size: 14 },
  { id: 'A/B 테스트 계획', group: 1, size: 14 },
  { id: '랜딩페이지 수정', group: 1, size: 12 },
  { id: '개발 스프린트 회의', group: 2, size: 18 },
  { id: '백엔드 API 설계', group: 2, size: 14 },
  { id: '프론트엔드 구현', group: 2, size: 14 },
  { id: '고객 미팅', group: 3, size: 16 },
  { id: '요구사항 정리', group: 3, size: 12 },
  { id: '제안서 작성', group: 3, size: 12 },
  { id: '디자인 리뷰', group: 4, size: 14 },
  { id: '성과 보고서 발표', group: 4, size: 14 },
]

const links = [
  { source: '마케팅 전략 회의', target: '광고 소재 제작', value: 0.9 },
  { source: '마케팅 전략 회의', target: 'A/B 테스트 계획', value: 0.8 },
  { source: '마케팅 전략 회의', target: '랜딩페이지 수정', value: 0.7 },
  { source: '광고 소재 제작', target: 'A/B 테스트 계획', value: 0.6 },
  { source: '개발 스프린트 회의', target: '백엔드 API 설계', value: 0.9 },
  { source: '개발 스프린트 회의', target: '프론트엔드 구현', value: 0.8 },
  { source: '백엔드 API 설계', target: '프론트엔드 구현', value: 0.7 },
  { source: '고객 미팅', target: '요구사항 정리', value: 0.9 },
  { source: '고객 미팅', target: '제안서 작성', value: 0.8 },
  { source: '마케팅 전략 회의', target: '고객 미팅', value: 0.4 },
  { source: '개발 스프린트 회의', target: '마케팅 전략 회의', value: 0.3 },
    // 디자인 그룹 연결
  { source: '디자인 리뷰', target: '성과 보고서 발표', value: 0.8 },
  { source: '디자인 리뷰', target: '마케팅 전략 회의', value: 0.5 },
  { source: '성과 보고서 발표', target: '마케팅 전략 회의', value: 0.4 },
]


const colorPalette = [
  '#7c6af7', '#5b8af5', '#4caf82',
  '#e8a838', '#e05c5c', '#f472b6',
  '#06b6d4', '#a3e635', '#fb923c',
]

const groupLabels: Record<number, string> = {
  1: '마케팅',
  2: '개발',
  3: '영업',
  4: '디자인',
}

const getGroupColor = (group: number) => {
  return colorPalette[(group - 1) % colorPalette.length]
}

export default function Graph() {
  const svgRef = useRef<SVGSVGElement>(null)
  const [selected, setSelected] = useState<string | null>(null)
  const [isDark, setIsDark] = useState(false)
  const [zoomLevel, setZoomLevel] = useState(1)
  const zoomRef = useRef<any>(null)

  useEffect(() => {
    const observer = new MutationObserver(() => {
      setIsDark(document.documentElement.classList.contains('dark'))
    })
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['class']
    })
    setIsDark(document.documentElement.classList.contains('dark'))
    return () => observer.disconnect()
  }, [])

  useEffect(() => {
    if (!svgRef.current) return
    const width = svgRef.current.clientWidth
    const height = svgRef.current.clientHeight
    const textColor = isDark ? '#9CA3AF' : '#4B5563'
    const lineColor = isDark ? '#374151' : '#D1D5DB'

    d3.select(svgRef.current).selectAll('*').remove()
    const svg = d3.select(svgRef.current)

    const g = svg.append('g')

    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.3, 3])
      .on('zoom', (event) => {
        g.attr('transform', event.transform)
        setZoomLevel(Math.round(event.transform.k * 100) / 100)
      })

    svg.call(zoom)
    zoomRef.current = zoom

    const simulation = d3.forceSimulation(nodes as any)
      .force('link', d3.forceLink(links as any).id((d: any) => d.id).distance(100))
      .force('charge', d3.forceManyBody().strength(-300))
      .force('center', d3.forceCenter(width / 2, height / 2))

    const link = g.append('g')
      .selectAll('line')
      .data(links)
      .enter()
      .append('line')
      .attr('stroke', lineColor)
      .attr('stroke-width', (d) => d.value * 2)

    const node = g.append('g')
      .selectAll('g')
      .data(nodes)
      .enter()
      .append('g')
      .style('cursor', 'pointer')
      .call(
        d3.drag<any, any>()
          .on('start', (event, d) => {
            if (!event.active) simulation.alphaTarget(0.3).restart()
            d.fx = d.x
            d.fy = d.y
          })
          .on('drag', (event, d) => {
            d.fx = event.x
            d.fy = event.y
          })
          .on('end', (event, d) => {
            if (!event.active) simulation.alphaTarget(0)
            d.fx = null
            d.fy = null
          })
      )

    node.append('circle')
      .attr('r', (d) => d.size)
      .attr('fill', (d) => getGroupColor(d.group))
      .attr('fill-opacity', 0.2)
      .attr('stroke', (d) => getGroupColor(d.group))
      .attr('stroke-width', 1.5)

    node.append('text')
      .text((d) => d.id)
      .attr('text-anchor', 'middle')
      .attr('dy', (d) => d.size + 12)
      .attr('font-size', '11px')
      .attr('fill', textColor)

    node.on('click', (_, d) => setSelected(d.id))

    simulation.on('tick', () => {
      link
        .attr('x1', (d: any) => d.source.x)
        .attr('y1', (d: any) => d.source.y)
        .attr('x2', (d: any) => d.target.x)
        .attr('y2', (d: any) => d.target.y)
      node.attr('transform', (d: any) => `translate(${d.x},${d.y})`)
    })

    return () => simulation.stop()
  }, [isDark])

  const handleZoomIn = () => {
    if (!svgRef.current || !zoomRef.current) return
    d3.select(svgRef.current).transition().call(zoomRef.current.scaleBy, 1.3)
  }

  const handleZoomOut = () => {
    if (!svgRef.current || !zoomRef.current) return
    d3.select(svgRef.current).transition().call(zoomRef.current.scaleBy, 0.7)
  }

  const handleReset = () => {
    if (!svgRef.current || !zoomRef.current) return
    d3.select(svgRef.current).transition().call(zoomRef.current.transform, d3.zoomIdentity)
  }

  const selectedLinks = links.filter(l =>
    l.source === selected || l.target === selected
  )
  const connectedNodes = selectedLinks.map(l =>
    l.source === selected ? l.target : l.source
  )

  return (
    <div>
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="text-lg font-bold text-gray-800 dark:text-white">그래프 시각화</h1>
          <p className="text-xs text-gray-400 mt-1">문서 간 임베딩 유사도 기반 연관성 시각화</p>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex gap-2">
            {Object.entries(groupLabels).map(([key, label]) => (
              <div key={key} className="flex items-center gap-1.5">
                <div className="w-2.5 h-2.5 rounded-full" style={{ background: getGroupColor(Number(key)) }} />
                <span className="text-xs text-gray-500 dark:text-gray-400">{label}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div className="col-span-2 relative">
          <div className="absolute top-3 right-3 z-10 flex flex-col gap-1.5">
            <button onClick={handleZoomIn} className="w-8 h-8 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg flex items-center justify-center text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 text-sm font-bold shadow-sm">+</button>
            <div className="w-8 h-6 flex items-center justify-center text-xs text-gray-400">{Math.round(zoomLevel * 100)}%</div>
            <button onClick={handleZoomOut} className="w-8 h-8 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg flex items-center justify-center text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 text-sm font-bold shadow-sm">−</button>
            <button onClick={handleReset} className="w-8 h-8 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg flex items-center justify-center text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700 text-xs shadow-sm">↺</button>
          </div>
          <div className="bg-gray-50 dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-700 overflow-hidden" style={{ height: '85vh' }}>
            <svg ref={svgRef} width="100%" height="100%" />
          </div>
        </div>

        <div className="flex flex-col gap-3">
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 p-4">
            <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 mb-3 uppercase tracking-wider">
              {selected ? '선택된 문서' : '문서를 클릭하세요'}
            </h3>
            {selected ? (
              <>
                <p className="text-sm font-semibold text-gray-700 dark:text-gray-200 mb-3">{selected}</p>
                <p className="text-xs text-gray-400 mb-2">연관 문서 {connectedNodes.length}개</p>
                <div className="flex flex-col gap-1.5">
                  {connectedNodes.map((node, i) => (
                    <div key={i} className="flex items-center gap-2 text-xs text-gray-600 dark:text-gray-300 bg-gray-50 dark:bg-gray-700 px-2.5 py-1.5 rounded-lg">
                      <div className="w-1.5 h-1.5 rounded-full bg-blue-400" />
                      {node}
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <p className="text-xs text-gray-400">노드를 클릭하면 연관 문서를 볼 수 있어요</p>
            )}
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 p-4">
            <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 mb-3 uppercase tracking-wider">전체 문서</h3>
            <div className="flex flex-col gap-1.5">
              {nodes.map((node, i) => (
                <div
                  key={i}
                  onClick={() => setSelected(node.id)}
                  className={`flex items-center gap-2 text-xs px-2.5 py-1.5 rounded-lg cursor-pointer transition ${
                    selected === node.id
                      ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400'
                      : 'text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
                  }`}
                >
                  <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: getGroupColor(node.group) }} />
                  {node.id}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}