import { useState } from 'react'

const USER_SERVICE_URL = 'http://localhost:8001'
const PORTFOLIO_SERVICE_URL = 'http://localhost:8002'

function LoginScreen({ onLogin }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await fetch(`${USER_SERVICE_URL}/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      })
      if (!res.ok) throw new Error(`Login failed (${res.status})`)
      const data = await res.json()
      if (data.success) {
        onLogin(data.username)
      } else {
        setError('Login failed')
      }
    } catch (err) {
      setError(err.message || 'Could not reach the user service')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="card">
      <h1>Sign in</h1>
      <form className="form" onSubmit={handleSubmit}>
        <label className="field">
          <span>Username</span>
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="Enter any username"
            autoFocus
          />
        </label>
        <label className="field">
          <span>Password</span>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Enter any password"
          />
        </label>
        <button type="submit" className="btn primary" disabled={loading}>
          {loading ? 'Signing in…' : 'Login'}
        </button>
        {error && <p className="error">{error}</p>}
      </form>
    </div>
  )
}

function PortfolioScreen({ username, onLogout }) {
  const [holdings, setHoldings] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const loadPortfolio = async () => {
    setError('')
    setLoading(true)
    try {
      const res = await fetch(`${PORTFOLIO_SERVICE_URL}/portfolio`)
      if (!res.ok) throw new Error(`Request failed (${res.status})`)
      const data = await res.json()
      setHoldings(data.holdings)
    } catch (err) {
      setError(err.message || 'Could not reach the portfolio service')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="card">
      <h1>Welcome, {username}</h1>
      <div className="actions">
        <button className="btn primary" onClick={loadPortfolio} disabled={loading}>
          {loading ? 'Loading…' : 'View My Portfolio'}
        </button>
        <button className="btn ghost" onClick={onLogout}>
          Logout
        </button>
      </div>

      {error && <p className="error">{error}</p>}

      {holdings && (
        <ul className="holdings">
          {holdings.map((h) => (
            <li key={h.ticker} className="holding">
              You own <strong>{h.shares}</strong> shares of {h.company} (
              <code>{h.ticker}</code>)
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export default function App() {
  const [username, setUsername] = useState(null)

  return (
    <div className="app">
      {username ? (
        <PortfolioScreen username={username} onLogout={() => setUsername(null)} />
      ) : (
        <LoginScreen onLogin={setUsername} />
      )}
    </div>
  )
}
