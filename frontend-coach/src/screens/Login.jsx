import React, { useState } from 'react'
import { login } from '../api.js'
import illoSrc from '../assets/login-illustration.png'

const T = {
  pageBg:     '#F7F5ED',
  darkGreen:  '#123D2F',
  lime:       '#CBEA58',
  primary:    '#17231D',
  muted:      '#65716B',
  surface:    '#FFFFFF',
  border:     '#DCE4DE',
  error:      '#C0392B',
}

const s = {
  page: {
    minHeight: '100vh',
    display: 'flex',
    background: T.pageBg,
    overflow: 'hidden',
    position: 'relative',
  },
  // Left illustration panel — hidden on mobile via CSS class
  illoPanel: {
    flex: '1 1 55%',
    position: 'relative',
    overflow: 'hidden',
    // hidden below 768px via .login-illo-panel CSS class
  },
  illoImg: {
    width: '100%',
    height: '100%',
    objectFit: 'cover',
    objectPosition: 'center center',
    display: 'block',
  },
  // Right panel holding the card
  rightPanel: {
    flex: '0 0 auto',
    width: '100%',
    maxWidth: 480,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '40px 32px',
    position: 'relative',
    zIndex: 1,
    boxSizing: 'border-box',
  },
  card: {
    background: T.surface,
    borderRadius: 20,
    padding: '40px 36px',
    width: '100%',
    maxWidth: 380,
    border: `1px solid ${T.border}`,
    boxShadow: '0 8px 32px rgba(23, 35, 29, 0.12)',
  },
  logoRow: { display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 },
  logoMark: {
    width: 38, height: 38, background: T.darkGreen, borderRadius: 10,
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    fontSize: 17, fontWeight: 800, color: T.lime,
  },
  brand: { fontWeight: 800, fontSize: 20, color: T.primary },
  sub:   { color: T.muted, fontSize: 14, marginBottom: 32, lineHeight: 1.5 },
  label: { display: 'block', fontSize: 13, fontWeight: 600, color: T.primary, marginBottom: 6 },
  input: {
    width: '100%', padding: '12px 14px',
    border: `1.5px solid ${T.border}`, borderRadius: 10,
    fontSize: 15, outline: 'none', marginBottom: 16,
    fontFamily: 'inherit', background: T.surface, color: T.primary,
    transition: 'border-color .15s',
    boxSizing: 'border-box',
  },
  btn: {
    width: '100%', padding: '14px 0',
    background: T.darkGreen, color: T.lime,
    border: 'none', borderRadius: 12,
    fontSize: 15, fontWeight: 700, cursor: 'pointer',
    marginTop: 4, letterSpacing: '.02em',
    boxShadow: '0 4px 16px rgba(18, 61, 47, 0.2)',
    transition: 'opacity .15s',
  },
  err: { color: T.error, fontSize: 13, marginTop: 12, textAlign: 'center' },
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
    <div style={s.page}>
      {/* Illustration — hidden on mobile */}
      <div className="login-illo-panel" style={s.illoPanel} aria-hidden="true">
        <img
          src={illoSrc}
          alt=""
          style={s.illoImg}
          draggable={false}
        />
      </div>

      {/* Login card */}
      <div style={s.rightPanel}>
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
            <button style={{ ...s.btn, opacity: loading ? 0.7 : 1 }} type="submit" disabled={loading}>
              {loading ? 'Signing in…' : 'Sign In'}
            </button>
            {error && <div style={s.err}>{error}</div>}
          </form>
        </div>
      </div>
    </div>
  )
}
