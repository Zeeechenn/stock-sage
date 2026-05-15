const BASE = '/api'

async function request(path, options = {}) {
  const res = await fetch(BASE + path, options)
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`${res.status}: ${text}`)
  }
  return res.json()
}

export const getWatchlist = () => request('/watchlist')

export const addStock = (symbol, name, market) =>
  request(`/watchlist?symbol=${encodeURIComponent(symbol)}&name=${encodeURIComponent(name)}&market=${market}`, {
    method: 'POST',
  })

export const removeStock = (symbol) =>
  request(`/watchlist/${symbol}`, { method: 'DELETE' })

export const getLatestSignal = (symbol) =>
  request(`/signals/${symbol}/latest`)

export const getPrices = (symbol, days = 120) =>
  request(`/prices/${symbol}?days=${days}`)

export const getNews = (symbol, hours = 48) =>
  request(`/news/${symbol}?hours=${hours}`)

export const getSignalEval = (symbol, days = 60) =>
  request(`/signals/eval/${symbol}?days=${days}`)

export const getLongTermLabel = (symbol) =>
  request(`/long-term/${symbol}`)

export const triggerLongTermTeam = () =>
  request(`/long-term/run`, { method: 'POST' })
