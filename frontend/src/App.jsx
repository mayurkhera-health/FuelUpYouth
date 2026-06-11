import { useState } from "react";
import Login from "./Login";
import Onboarding from "./Onboarding";
import Dashboard from "./Dashboard";
import LibraryAdmin from "./pages/LibraryAdmin";
import PhoneFrame from "./components/PhoneFrame";

const API = import.meta.env.VITE_API_URL ?? "";

export default function App() {
  if (window.location.pathname === "/admin/library") {
    return <LibraryAdmin />;
  }
  const [view, setView] = useState("login"); // "login" | "onboarding" | "dashboard"
  const [session, setSession] = useState(null); // { parent, athletes }
  const [initialTab, setInitialTab] = useState("nutrition");
  const [isNewAccount, setIsNewAccount] = useState(false);

  function handleLogin({ parent, athletes }) {
    setSession({ parent, athletes });
    setInitialTab("home");
    setView("dashboard");
  }

  async function handleOnboardingComplete({ parentId, athleteId }) {
    try {
      const [parentRes, athleteRes] = await Promise.all([
        fetch(`${API}/api/parents/${parentId}`),
        fetch(`${API}/api/athletes/${athleteId}`),
      ]);
      const parent = await parentRes.json();
      const athlete = await athleteRes.json();
      setSession({ parent, athletes: [athlete] });
      setInitialTab("blueprint");
      setIsNewAccount(true);
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
      <PhoneFrame>
        <Dashboard
          parent={session.parent}
          athletes={session.athletes}
          initialTab={initialTab}
          isNewAccount={isNewAccount}
          onUnlockApp={() => setIsNewAccount(false)}
          onSignOut={handleSignOut}
        />
      </PhoneFrame>
    );
  }

  if (view === "onboarding") {
    return (
      <PhoneFrame>
        <Onboarding onComplete={handleOnboardingComplete} />
      </PhoneFrame>
    );
  }

  return (
    <PhoneFrame>
      <Login
        onLogin={handleLogin}
        onNewAccount={() => setView("onboarding")}
      />
    </PhoneFrame>
  );
}
