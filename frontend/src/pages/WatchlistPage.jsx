import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { getWatchlist, addStock, removeStock } from '../api'

const REC_STYLE = {
  '可小仓试错': 'bg-red-500 text-white',
  '可关注': 'bg-orange-400 text-gray-950',
  '强买': 'bg-red-600 text-white',
  '买入': 'bg-red-400 text-white',
  '观望': 'bg-yellow-500 text-gray-900',
  '规避': 'bg-green-600 text-white',
  '卖出': 'bg-green-500 text-white',
  '强卖': 'bg-green-700 text-white',
}

const LONG_TERM_STYLE = {
  '值得持有': { cls: 'bg-emerald-600 text-white', icon: '✓' },
  '估值偏高': { cls: 'bg-amber-500 text-gray-900', icon: '⚠' },
  '观望':     { cls: 'bg-gray-500 text-white', icon: '·' },
  '规避':     { cls: 'bg-rose-700 text-white', icon: '✕' },
}

function LongTermBadge({ label }) {
  if (!label) return null
  const style = LONG_TERM_STYLE[label.label] || { cls: 'bg-gray-600 text-white', icon: '?' }
  const title = `${label.label} · score=${label.score.toFixed(0)} · ${label.key_findings?.[0] || ''}`
  return (
    <span
      title={title}
      className={`text-xs px-2 py-0.5 rounded font-medium ${style.cls}`}
    >
      {style.icon} {label.label}
    </span>
  )
}

function ScoreBar({ score }) {
  const pct = ((score + 100) / 200) * 100
  const color = score > 20 ? 'bg-red-500' : score < -20 ? 'bg-green-500' : 'bg-yellow-500'
  return (
    <div className="w-full bg-gray-700 rounded-full h-1.5 mt-1">
      <div className={`h-1.5 rounded-full ${color}`} style={{ width: `${pct}%` }} />
    </div>
  )
}

function StockCard({ item, onRemove }) {
  const sig = item.latest_signal
  const lt = item.long_term_label
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 hover:border-gray-600 transition-colors">
      <div className="flex justify-between items-start">
        <Link to={`/stock/${item.symbol}`} className="group">
          <div className="flex items-center gap-2">
            <div className="font-bold text-lg group-hover:text-blue-400 transition-colors">{item.name}</div>
            <LongTermBadge label={lt} />
          </div>
          <div className="text-gray-400 text-sm">
            {item.symbol} · {item.market}
            {item.industry && <span className="text-gray-500"> · {item.industry}</span>}
          </div>
        </Link>
        <button
          onClick={() => onRemove(item.symbol)}
          className="text-gray-600 hover:text-red-400 text-xl leading-none transition-colors"
          title="移除"
        >×</button>
      </div>

      {sig ? (
        <div className="mt-3">
          <div className="flex items-center gap-2">
            <span className={`text-xs px-2 py-0.5 rounded font-medium ${REC_STYLE[sig.recommendation] || 'bg-gray-600 text-white'}`}>
              {sig.recommendation}
            </span>
            <span className="text-gray-400 text-xs">{sig.date}</span>
            <span className="text-gray-500 text-xs">置信度 {sig.confidence}</span>
          </div>
          <div className="mt-1.5 flex items-center gap-2">
            <span className="text-sm font-mono">{sig.composite_score > 0 ? '+' : ''}{sig.composite_score.toFixed(0)}</span>
            <ScoreBar score={sig.composite_score} />
          </div>
          {sig.stop_loss && (
            <div className="mt-1 text-xs text-gray-500">
              止损 <span className="text-green-400">{sig.stop_loss.toFixed(2)}</span>
              &nbsp;·&nbsp;止盈 <span className="text-red-400">{sig.take_profit?.toFixed(2)}</span>
            </div>
          )}
        </div>
      ) : (
        <div className="mt-3 text-gray-500 text-sm">暂无信号</div>
      )}
    </div>
  )
}

function AddStockForm({ onAdd }) {
  const [symbol, setSymbol] = useState('')
  const [name, setName] = useState('')
  const [market, setMarket] = useState('CN')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(e) {
    e.preventDefault()
    if (!symbol.trim() || !name.trim()) return
    setLoading(true)
    setError('')
    try {
      await addStock(symbol.trim(), name.trim(), market)
      setSymbol('')
      setName('')
      onAdd()
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="bg-gray-900 border border-gray-800 rounded-xl p-4">
      <div className="text-sm font-medium text-gray-300 mb-3">添加自选股</div>
      <div className="flex gap-2 flex-wrap">
        <input
          value={symbol}
          onChange={e => setSymbol(e.target.value)}
          placeholder="代码 (如 600519)"
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm w-36 focus:outline-none focus:border-blue-500"
        />
        <input
          value={name}
          onChange={e => setName(e.target.value)}
          placeholder="名称 (如 贵州茅台)"
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm w-40 focus:outline-none focus:border-blue-500"
        />
        <select
          value={market}
          onChange={e => setMarket(e.target.value)}
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:border-blue-500"
        >
          <option value="CN">A股</option>
          <option value="US">美股</option>
        </select>
        <button
          type="submit"
          disabled={loading}
          className="bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-lg px-4 py-1.5 text-sm font-medium transition-colors"
        >
          {loading ? '添加中…' : '添加'}
        </button>
      </div>
      {error && <div className="mt-2 text-red-400 text-xs">{error}</div>}
    </form>
  )
}

export default function WatchlistPage() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)

  async function load() {
    setLoading(true)
    try {
      const data = await getWatchlist()
      setItems(data)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  async function handleRemove(symbol) {
    await removeStock(symbol)
    load()
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">自选股</h1>
      <AddStockForm onAdd={load} />

      {loading ? (
        <div className="mt-8 text-gray-500 text-center">加载中…</div>
      ) : items.length === 0 ? (
        <div className="mt-8 text-gray-500 text-center">暂无自选股，添加第一只吧</div>
      ) : (
        <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {items.map(item => (
            <StockCard key={item.symbol} item={item} onRemove={handleRemove} />
          ))}
        </div>
      )}
    </div>
  )
}
