import { useEffect } from 'react'
import type React from 'react'
import * as d3 from 'd3'

type Node = { id: string; group: number; size: number }
type Link = { source: string; target: string; value: number }

type Props = {
  nodes: Node[]
  links: Link[]
  isDark: boolean
  getGroupColor: (group: number) => string
  onSelect: (id: string) => void
  onZoomChange: (level: number) => void
  zoomRef: React.MutableRefObject<any>
  svgRef: React.RefObject<SVGSVGElement | null>
}

export default function GraphCanvas({ nodes, links, isDark, getGroupColor, onSelect, onZoomChange, zoomRef, svgRef }: Props) {
  useEffect(() => {
    if (!svgRef.current) return
    const width = svgRef.current.clientWidth
    const height = svgRef.current.clientHeight

    const bg = isDark ? '#0d0d0d' : '#ffffff'
    const lineColor = isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.08)'
    const textColor = isDark ? 'rgba(255,255,255,0.35)' : 'rgba(0,0,0,0.35)'
    const textHoverColor = isDark ? '#ffffff' : '#111111'
    const nodeDefaultColor = isDark ? 'rgba(255,255,255,0.25)' : 'rgba(0,0,0,0.15)'

    d3.select(svgRef.current).selectAll('*').remove()
    const svg = d3.select(svgRef.current)

    svg.append('rect').attr('width', width).attr('height', height).attr('fill', bg)

    const g = svg.append('g')

    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.2, 4])
      .on('zoom', (event) => {
        g.attr('transform', event.transform)
        onZoomChange(Math.round(event.transform.k * 100) / 100)
      })
    svg.call(zoom)
    zoomRef.current = zoom


const simulation = d3.forceSimulation(nodes as any)
  .force('link', d3.forceLink(links as any).id((d: any) => d.id).distance(25))
  .force('charge', d3.forceManyBody().strength(-8))
  .force('collision', d3.forceCollide(6))
  .force('x', d3.forceX(width / 2).strength(0.03))
  .force('y', d3.forceY(height / 2).strength(0.03))

    // 글로우 필터
    const defs = svg.append('defs')
    const filter = defs.append('filter').attr('id', 'glow')
    filter.append('feGaussianBlur').attr('stdDeviation', '6').attr('result', 'coloredBlur')
    const feMerge = filter.append('feMerge')
    feMerge.append('feMergeNode').attr('in', 'coloredBlur')
    feMerge.append('feMergeNode').attr('in', 'SourceGraphic')

    const link = g.append('g')
      .selectAll('line')
      .data(links)
      .enter()
      .append('line')
      .attr('stroke', lineColor)
      .attr('stroke-width', (d) => d.value * 1.2)
      .attr('stroke-linecap', 'round')

    const nodeGroup = g.append('g')
      .selectAll('g')
      .data(nodes)
      .enter()
      .append('g')
      .style('cursor', 'pointer')
      .call(
        d3.drag<any, any>()
          .on('start', (event, d) => {
            if (!event.active) simulation.alphaTarget(0.3).restart()
            d.fx = d.x; d.fy = d.y
          })
          .on('drag', (event, d) => { d.fx = event.x; d.fy = event.y })
          .on('end', (event, d) => {
            if (!event.active) simulation.alphaTarget(0)
            d.fx = null; d.fy = null
          })
      )

    // 작은 점 노드 (옵시디언 스타일)
    nodeGroup.append('circle')
      .attr('r', (d) => d.size * 1.0)  // 0.4 → 0.8
      .attr('fill', (d) => getGroupColor(d.group))
      .attr('fill-opacity', 0.4)
      .attr('stroke', (d) => getGroupColor(d.group))
      .attr('stroke-width', 1.5)

    // 텍스트 (기본엔 희미하게)
    nodeGroup.append('text')
      .text((d) => d.id)
      .attr('text-anchor', 'middle')
      .attr('dy', (d) => d.size * 0.8 + 12)
      .attr('font-size', '0px')        // 기본엔 안보이게
      .attr('fill', textColor)
      .attr('pointer-events', 'none')

    // 호버 이벤트
    nodeGroup
      .on('mouseover', function(_, d: any) {
        const connectedIds = new Set<string>()
        links.forEach(l => {
          const src = typeof l.source === 'string' ? l.source : (l.source as any).id
          const tgt = typeof l.target === 'string' ? l.target : (l.target as any).id
          if (src === d.id) connectedIds.add(tgt)
          if (tgt === d.id) connectedIds.add(src)
        })

        // 노드 하이라이트
        nodeGroup.selectAll('circle')
          .attr('fill', (n: any) => {
            if (n.id === d.id) return getGroupColor(n.group)
            if (connectedIds.has(n.id)) return getGroupColor(n.group)
            return isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.05)'
          })
          .attr('r', (n: any) => {
            if (n.id === d.id) return n.size * 2.0
            if (connectedIds.has(n.id)) return n.size * 1.4
            return n.size * 0.4
          })
          .attr('filter', (n: any) => n.id === d.id ? 'url(#glow)' : 'none')

        // 텍스트 하이라이트
    nodeGroup.selectAll('text')
  .attr('fill', (n: any) => {
    if (n.id === d.id || connectedIds.has(n.id)) return textHoverColor
    return 'rgba(0,0,0,0)'  // 나머지는 완전 투명
  })
  .attr('font-size', (n: any) => n.id === d.id ? '12px' : '10px')
  .attr('font-weight', (n: any) => n.id === d.id ? '600' : '400')

        // 연결선 하이라이트
        link
          .attr('stroke', (l: any) => {
            const src = typeof l.source === 'string' ? l.source : l.source.id
            const tgt = typeof l.target === 'string' ? l.target : l.target.id
            if (src === d.id || tgt === d.id) return getGroupColor(d.group)
            return isDark ? 'rgba(255,255,255,0.02)' : 'rgba(0,0,0,0.02)'
          })
          .attr('stroke-width', (l: any) => {
            const src = typeof l.source === 'string' ? l.source : l.source.id
            const tgt = typeof l.target === 'string' ? l.target : l.target.id
            return src === d.id || tgt === d.id ? l.value * 2 : l.value * 1.2
          })
      })
      .on('mouseout', function() {
        nodeGroup.selectAll('circle')
  .attr('fill', (n: any) => getGroupColor(n.group))
  .attr('fill-opacity', 0.3)
  .attr('filter', 'none')
  .attr('r', (n: any) => n.size * 1.0)

nodeGroup.selectAll('text')
  .attr('fill', 'rgba(0,0,0,0)')
  .attr('font-size', '0px')
        link
          .attr('stroke', lineColor)
          .attr('stroke-width', (d: any) => d.value * 1.2)
      })
      .on('click', (_, d: any) => onSelect(d.id))

    simulation.on('tick', () => {
      link
        .attr('x1', (d: any) => d.source.x)
        .attr('y1', (d: any) => d.source.y)
        .attr('x2', (d: any) => d.target.x)
        .attr('y2', (d: any) => d.target.y)
      nodeGroup.attr('transform', (d: any) => `translate(${d.x},${d.y})`)
    })

    return () => simulation.stop()
  }, [isDark])

  return null
}