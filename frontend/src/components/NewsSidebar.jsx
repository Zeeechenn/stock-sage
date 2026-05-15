function SentimentBar({ score }) {
  if (score == null) return null
  const pct = ((score + 1) / 2) * 100
  const color = score > 0.2 ? '#ef4444' : score < -0.2 ? '#22c55e' : '#eab308'
  return (
    <div className="mt-1 flex items-center gap-1.5">
      <div className="flex-1 bg-gray-700 rounded-full h-1">
        <div className="h-1 rounded-full" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="text-xs font-mono w-8 text-right" style={{ color }}>
        {score > 0 ? '+' : ''}{score.toFixed(2)}
      </span>
    </div>
  )
}

export default function NewsSidebar({ news }) {
  if (!news) {
    return (
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 text-center text-gray-500 text-sm">
        加载中…
      </div>
    )
  }
  if (news.length === 0) {
    return (
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 text-center text-gray-500 text-sm">
        近期无相关新闻
      </div>
    )
  }

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
      <div className="text-sm font-medium text-gray-300 mb-3">近期新闻</div>
      <ul className="space-y-3 max-h-[calc(100vh-20rem)] overflow-y-auto pr-1">
        {news.map(item => (
          <li key={item.id} className="border-b border-gray-800 pb-3 last:border-0 last:pb-0">
            <a
              href={item.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-gray-200 hover:text-blue-400 transition-colors leading-snug block"
            >
              {item.title}
            </a>
            <div className="flex items-center gap-2 mt-1">
              <span className="text-xs text-gray-500">{item.source}</span>
              <span className="text-xs text-gray-600">{item.published_at}</span>
            </div>
            <SentimentBar score={item.sentiment_score} />
          </li>
        ))}
      </ul>
    </div>
  )
}
