import React, { useState, useEffect } from 'react'
import { setToken, clearToken, fetchTeams, fetchMe, getCoachName, setCoachName } from './api.js'
import AppShell from './AppShell.jsx'
import Login from './screens/Login.jsx'
import TeamSelector from './screens/TeamSelector.jsx'
import TeamOverview from './screens/TeamOverview.jsx'
import RosterList from './screens/RosterList.jsx'
import AthleteDetail from './screens/AthleteDetail.jsx'
import Reports from './screens/Reports.jsx'

export default function App() {
  const [view, setView]               = useState('login')
  const [teamsData, setTeamsData]     = useState(null)   // {generated_at, season, teams:[]}
  const [selectedTeam, setSelectedTeam]         = useState(null)
  const [selectedAthlete, setSelectedAthlete]   = useState(null)
  const [coachName, setCoachNameState]           = useState(getCoachName)

  useEffect(() => {
    if (localStorage.getItem('tc_token')) loadTeams()
  }, [])

  async function loadTeams() {
    try {
      const [data, me] = await Promise.all([
        fetchTeams(),
        getCoachName() ? Promise.resolve(null) : fetchMe(),
      ])
      setTeamsData(data)
      if (me?.name) { setCoachName(me.name); setCoachNameState(me.name) }
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
  function onSelectTeam(t)       { setSelectedTeam(t); setView('overview') }
  function onSelectAthlete(a)    { setSelectedAthlete(a); setView('athlete') }
  function onLogout()            { clearToken(); setTeamsData(null); setSelectedTeam(null); setSelectedAthlete(null); setCoachNameState(''); setView('login') }
  function onDashboard()         { setView('dashboard') }
  function onReports()           { setView('reports') }

  if (view === 'login') return <Login onLogin={onLogin} />

  const activeView = (view === 'roster' || view === 'athlete') ? 'roster' : view === 'reports' ? 'reports' : 'dashboard'

  return (
    <AppShell
      activeView={activeView}
      onDashboard={onDashboard}
      onRoster={() => setView('roster')}
      onReports={onReports}
      onLogout={onLogout}
      hasTeam={!!selectedTeam}
      coachName={coachName}
    >
      {view === 'dashboard' && (
        <TeamSelector teamsData={teamsData} onSelect={onSelectTeam} loading={!teamsData} coachName={coachName} />
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
        <RosterList
          team={selectedTeam}
          onBack={() => setView('overview')}
          onSelectAthlete={onSelectAthlete}
        />
      )}
      {view === 'athlete' && selectedAthlete && (
        <AthleteDetail
          team={selectedTeam}
          athlete={selectedAthlete}
          onBack={() => setView('roster')}
        />
      )}
      {view === 'reports' && (
        <Reports teamsData={teamsData} />
      )}
    </AppShell>
  )
}
