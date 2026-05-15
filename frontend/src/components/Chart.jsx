import { useEffect, useRef } from 'react'
import { createChart, CrosshairMode, LineStyle } from 'lightweight-charts'

export default function Chart({ prices, signal }) {
  const containerRef = useRef(null)
  const chartRef = useRef(null)

  useEffect(() => {
    if (!containerRef.current || !prices?.length) return

    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height: 380,
      layout: {
        background: { color: '#0f172a' },
        textColor: '#94a3b8',
      },
      grid: {
        vertLines: { color: '#1e293b' },
        horzLines: { color: '#1e293b' },
      },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: { borderColor: '#1e293b' },
      timeScale: {
        borderColor: '#1e293b',
        timeVisible: true,
      },
    })
    chartRef.current = chart

    // A股：涨红跌绿
    const candleSeries = chart.addCandlestickSeries({
      upColor: '#ef4444',
      downColor: '#22c55e',
      borderUpColor: '#ef4444',
      borderDownColor: '#22c55e',
      wickUpColor: '#ef4444',
      wickDownColor: '#22c55e',
    })
    candleSeries.setData(prices)

    // 成交量
    const volSeries = chart.addHistogramSeries({
      color: '#334155',
      priceFormat: { type: 'volume' },
      priceScaleId: 'volume',
    })
    chart.priceScale('volume').applyOptions({
      scaleMargins: { top: 0.85, bottom: 0 },
    })
    volSeries.setData(prices.map(p => ({
      time: p.time,
      value: p.volume,
      color: p.close >= p.open ? '#7f1d1d' : '#14532d',
    })))

    // 止损 / 止盈线
    if (signal?.stop_loss) {
      candleSeries.createPriceLine({
        price: signal.stop_loss,
        color: '#22c55e',
        lineWidth: 1,
        lineStyle: LineStyle.Dashed,
        axisLabelVisible: true,
        title: '止损',
      })
    }
    if (signal?.take_profit) {
      candleSeries.createPriceLine({
        price: signal.take_profit,
        color: '#ef4444',
        lineWidth: 1,
        lineStyle: LineStyle.Dashed,
        axisLabelVisible: true,
        title: '止盈',
      })
    }

    chart.timeScale().fitContent()

    // 响应式宽度
    const ro = new ResizeObserver(() => {
      chart.applyOptions({ width: containerRef.current.clientWidth })
    })
    ro.observe(containerRef.current)

    return () => {
      ro.disconnect()
      chart.remove()
      chartRef.current = null
    }
  }, [prices, signal])

  if (!prices?.length) {
    return (
      <div className="bg-gray-900 border border-gray-800 rounded-xl h-96 flex items-center justify-center text-gray-500">
        暂无行情数据
      </div>
    )
  }

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
      <div ref={containerRef} />
    </div>
  )
}
