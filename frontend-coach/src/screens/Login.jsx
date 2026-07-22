import React, { useState } from 'react'
import { login } from '../api.js'

const s = {
  wrap:  { minHeight: '100vh', display: 'flex', alignItems: 'center',
           justifyContent: 'center', background: '#f5f5f5' },
  card:  { background: '#fff', borderRadius: 12, padding: 40, width: 360,
           boxShadow: '0 2px 12px rgba(0,0,0,.08)' },
  logo:  { fontWeight: 700, fontSize: 22, color: '#1a7a4a', marginBottom: 4 },
  sub:   { color: '#888', fontSize: 13, marginBottom: 32 },
  label: { display: 'block', fontSize: 13, fontWeight: 600, color: '#333', marginBottom: 6 },
  input: { width: '100%', padding: '10px 12px', border: '1px solid #ddd',
           borderRadius: 8, fontSize: 15, outline: 'none', marginBottom: 16 },
  btn:   { width: '100%', padding: '12px 0', background: '#1a7a4a', color: '#fff',
           border: 'none', borderRadius: 8, fontSize: 15, fontWeight: 600,
           cursor: 'pointer', marginTop: 8 },
  err:   { color: '#c0392b', fontSize: 13, marginTop: 12, textAlign: 'center' },
}

export default function Login({ onLogin }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const data = await login(email, password)
      onLogin(data)
    } catch (err) {
      setError(err.message || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={s.wrap}>
      <div style={s.card}>
        <div style={s.logo}>TeamCoach</div>
        <div style={s.sub}>FuelUp Coach Dashboard</div>
        <form onSubmit={handleSubmit}>
          <label style={s.label}>Email</label>
          <input style={s.input} type="email" value={email}
                 onChange={e => setEmail(e.target.value)} required autoFocus />
          <label style={s.label}>Password</label>
          <input style={s.input} type="password" value={password}
                 onChange={e => setPassword(e.target.value)} required />
          <button style={s.btn} type="submit" disabled={loading}>
            {loading ? 'Signing in…' : 'Sign In'}
          </button>
          {error && <div style={s.err}>{error}</div>}
        </form>
      </div>
    </div>
  )
}
