import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import WatchlistPage from './pages/WatchlistPage'
import StockDetailPage from './pages/StockDetailPage'

function Navbar() {
  return (
    <nav className="bg-gray-900 border-b border-gray-800 px-6 py-3 flex items-center gap-4">
      <Link to="/" className="text-lg font-bold text-blue-400 hover:text-blue-300">
        StockSage
      </Link>
      <span className="text-gray-500 text-sm">A股辅助决策</span>
    </nav>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-950 text-gray-100">
        <Navbar />
        <main className="max-w-7xl mx-auto px-4 py-6">
          <Routes>
            <Route path="/" element={<WatchlistPage />} />
            <Route path="/stock/:symbol" element={<StockDetailPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
