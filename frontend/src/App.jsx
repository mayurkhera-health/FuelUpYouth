import { useState } from "react";
import Login from "./Login";
import Onboarding from "./Onboarding";
import Dashboard from "./Dashboard";

export default function App() {
  const [view, setView] = useState("login"); // "login" | "onboarding" | "dashboard"
  const [session, setSession] = useState(null); // { parent, athletes }
  const [initialTab, setInitialTab] = useState("nutrition");

  function handleLogin({ parent, athletes }) {
    setSession({ parent, athletes });
    setInitialTab("home");
    setView("dashboard");
  }

  async function handleOnboardingComplete({ parentId, athleteId }) {
    try {
      const [parentRes, athleteRes] = await Promise.all([
        fetch(`http://localhost:8000/api/parents/${parentId}`),
        fetch(`http://localhost:8000/api/athletes/${athleteId}`),
      ]);
      const parent = await parentRes.json();
      const athlete = await athleteRes.json();
      setSession({ parent, athletes: [athlete] });
      setInitialTab("schedule");
      setView("dashboard");
    } catch {
      setView("login");
    }
  }

  function handleSignOut() {
    setSession(null);
    setView("login");
  }

  if (view === "dashboard" && session) {
    return (
      <Dashboard
        parent={session.parent}
        athletes={session.athletes}
        initialTab={initialTab}
        onSignOut={handleSignOut}
      />
    );
  }

  if (view === "onboarding") {
    return <Onboarding onComplete={handleOnboardingComplete} />;
  }

  return (
    <Login
      onLogin={handleLogin}
      onNewAccount={() => setView("onboarding")}
    />
  );
}
