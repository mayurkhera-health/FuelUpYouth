import React, { useState, useEffect } from 'react'
import { setToken, clearToken, fetchTeams, getCoachName, setCoachName } from './api.js'
import AppShell from './AppShell.jsx'
import Login from './screens/Login.jsx'
import TeamSelector from './screens/TeamSelector.jsx'
import TeamOverview from './screens/TeamOverview.jsx'
import RosterList from './screens/RosterList.jsx'

export default function App() {
  const [view, setView]               = useState('login')
  const [teamsData, setTeamsData]     = useState(null)   // {generated_at, season, teams:[]}
  const [selectedTeam, setSelectedTeam] = useState(null)
  const [coachName, setCoachNameState]  = useState(getCoachName)

  useEffect(() => {
    if (localStorage.getItem('tc_token')) loadTeams()
  }, [])

  async function loadTeams() {
    try {
      const data = await fetchTeams()
      setTeamsData(data)
      setView('dashboard')
    } catch {
      clearToken(); setView('login')
    }
  }

  function onLogin({ token, coach_name }) {
    setToken(token)
    setCoachName(coach_name)
    setCoachNameState(coach_name)
    loadTeams()
  }
  function onSelectTeam(t)   { setSelectedTeam(t); setView('overview') }
  function onLogout()        { clearToken(); setTeamsData(null); setSelectedTeam(null); setCoachNameState(''); setView('login') }
  function onDashboard()     { setView('dashboard') }

  if (view === 'login') return <Login onLogin={onLogin} />

  const activeView = view === 'roster' ? 'roster' : 'dashboard'

  return (
    <AppShell
      activeView={activeView}
      onDashboard={onDashboard}
      onRoster={() => setView('roster')}
      onLogout={onLogout}
      hasTeam={!!selectedTeam}
      coachName={coachName}
    >
      {view === 'dashboard' && (
        <TeamSelector teamsData={teamsData} onSelect={onSelectTeam} />
      )}
      {view === 'overview' && (
        <TeamOverview
          team={selectedTeam}
          onViewRoster={() => setView('roster')}
          onSwitchTeam={() => setView('dashboard')}
          onLogout={null}
        />
      )}
      {view === 'roster' && (
        <RosterList team={selectedTeam} onBack={() => setView('overview')} />
      )}
    </AppShell>
  )
}
