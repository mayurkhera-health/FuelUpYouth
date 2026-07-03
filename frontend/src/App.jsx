import { useState } from "react";
import Login from "./Login";
import Onboarding from "./Onboarding";
import Dashboard from "./Dashboard";
import LibraryAdmin from "./pages/LibraryAdmin";
import AdminApp from "./pages/admin/AdminApp";

const API = import.meta.env.VITE_API_URL ?? "";

export default function App() {
  if (window.location.pathname === "/admin/library") {
    return <LibraryAdmin />;
  }
  // Admin Module (Users + Analytics). Checked before the hooks below, mirroring
  // the /admin/library early-return above — path is constant per page load.
  if (window.location.pathname.startsWith("/admin")) {
    return <AdminApp />;
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
      <Dashboard
        parent={session.parent}
        athletes={session.athletes}
        initialTab={initialTab}
        isNewAccount={isNewAccount}
        onUnlockApp={() => setIsNewAccount(false)}
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
