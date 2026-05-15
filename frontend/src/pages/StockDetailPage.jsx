import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { getLatestSignal, getPrices, getNews, getSignalEval } from '../api'
import SignalCard from '../components/SignalCard'
import SignalEvalCard from '../components/SignalEvalCard'
import Chart from '../components/Chart'
import NewsSidebar from '../components/NewsSidebar'

export default function StockDetailPage() {
  const { symbol } = useParams()
  const [signal, setSignal] = useState(null)
  const [prices, setPrices] = useState([])
  const [news, setNews] = useState(null)
  const [evalData, setEvalData] = useState(null)
  const [evalDays, setEvalDays] = useState(60)
  const [evalLoading, setEvalLoading] = useState(true)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    setLoading(true)
    setError('')
    Promise.all([
      getLatestSignal(symbol).catch(() => null),
      getPrices(symbol, 120).catch(() => []),
      getNews(symbol, 48).catch(() => []),
    ]).then(([sig, px, nw]) => {
      setSignal(sig)
      setPrices(px)
      setNews(nw)
    }).catch(e => {
      setError(e.message)
    }).finally(() => setLoading(false))
  }, [symbol])

  useEffect(() => {
    setEvalLoading(true)
    getSignalEval(symbol, evalDays)
      .then((data) => setEvalData(data))
      .catch(() => setEvalData(null))
      .finally(() => setEvalLoading(false))
  }, [symbol, evalDays])

  return (
    <div>
      <div className="flex items-center gap-3 mb-6">
        <Link to="/" className="text-gray-500 hover:text-gray-300 text-sm transition-colors">
          ← 自选股
        </Link>
        <span className="text-gray-600">/</span>
        <h1 className="text-xl font-bold">{symbol}</h1>
      </div>

      {loading ? (
        <div className="text-center text-gray-500 py-20">加载中…</div>
      ) : error ? (
        <div className="text-center text-red-400 py-20">{error}</div>
      ) : (
        <div className="space-y-4">
          {/* 主图 */}
          <Chart prices={prices} signal={signal} />

          {/* 信号卡片 + 新闻侧栏 */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <div className="lg:col-span-2 space-y-4">
              <SignalCard signal={signal} />
              <SignalEvalCard
                evalData={evalData}
                days={evalDays}
                onDaysChange={setEvalDays}
                loading={evalLoading}
              />
            </div>
            <div>
              <NewsSidebar news={news} />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
