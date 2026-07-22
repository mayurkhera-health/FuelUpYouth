import React, { useState } from 'react'
import { login } from '../api.js'

const T = { emerald: '#0f2a1f', neon: '#3dfc3d', surface: '#faf9f7', border: '#dadad8' }

const s = {
  wrap:  { minHeight: '100vh', display: 'flex', alignItems: 'center',
           justifyContent: 'center', background: T.surface, padding: '20px' },
  card:  { background: '#fff', borderRadius: 16, padding: '36px 32px',
           width: '100%', maxWidth: 380,
           border: `1px solid ${T.border}`,
           boxShadow: '0 4px 24px rgba(0,0,0,.06)' },
  logoRow: { display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 },
  logoMark: { width: 36, height: 36, background: T.emerald, borderRadius: 8,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 16, fontWeight: 800, color: T.neon },
  brand: { fontWeight: 800, fontSize: 20, color: T.emerald },
  sub:   { color: '#aaa', fontSize: 13, marginBottom: 28 },
  label: { display: 'block', fontSize: 13, fontWeight: 600, color: '#444', marginBottom: 6 },
  input: {
    width: '100%', padding: '11px 14px',
    border: `1.5px solid ${T.border}`, borderRadius: 10,
    fontSize: 15, outline: 'none', marginBottom: 14,
    fontFamily: 'inherit', background: '#fff',
    transition: 'border-color .15s',
  },
  btn: {
    width: '100%', padding: '13px 0',
    background: T.emerald, color: T.neon,
    border: 'none', borderRadius: 10,
    fontSize: 15, fontWeight: 700, cursor: 'pointer',
    marginTop: 4, letterSpacing: '.02em',
    boxShadow: `0 2px 10px rgba(15,42,31,.2)`,
  },
  err: { color: '#e91e63', fontSize: 13, marginTop: 12, textAlign: 'center' },
}

export default function Login({ onLogin }) {
  const [email, setEmail]       = useState('')
  const [password, setPassword] = useState('')
  const [error, setError]       = useState('')
  const [loading, setLoading]   = useState(false)

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
        <div style={s.logoRow}>
          <div style={s.logoMark}>F</div>
          <span style={s.brand}>FuelUp Coach</span>
        </div>
        <div style={s.sub}>Coach dashboard · Sign in to continue</div>
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
