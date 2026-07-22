import React, { useState, useEffect } from 'react'
import { setToken, clearToken, fetchTeams } from './api.js'
import Login from './screens/Login.jsx'
import TeamSelector from './screens/TeamSelector.jsx'
import TeamOverview from './screens/TeamOverview.jsx'
import RosterList from './screens/RosterList.jsx'

export default function App() {
  const [view, setView] = useState('login')
  const [teams, setTeams] = useState([])
  const [selectedTeam, setSelectedTeam] = useState(null)

  useEffect(() => {
    if (localStorage.getItem('tc_token')) loadTeams()
  }, [])

  async function loadTeams() {
    try {
      const data = await fetchTeams()
      setTeams(data)
      if (data.length === 1) { setSelectedTeam(data[0]); setView('overview') }
      else setView('selector')
    } catch {
      clearToken(); setView('login')
    }
  }

  function onLogin(token) { setToken(token); loadTeams() }

  function onSelectTeam(team) { setSelectedTeam(team); setView('overview') }

  function onLogout() {
    clearToken(); setTeams([]); setSelectedTeam(null); setView('login')
  }

  if (view === 'login') return <Login onLogin={onLogin} />
  if (view === 'selector') return <TeamSelector teams={teams} onSelect={onSelectTeam} />
  if (view === 'overview') return (
    <TeamOverview
      team={selectedTeam}
      onViewRoster={() => setView('roster')}
      onSwitchTeam={teams.length > 1 ? () => setView('selector') : null}
      onLogout={onLogout}
    />
  )
  if (view === 'roster') return (
    <RosterList team={selectedTeam} onBack={() => setView('overview')} />
  )
}
