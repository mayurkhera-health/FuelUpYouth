import { useState, useRef, useEffect } from "react";
import HomeScreen from "./HomeScreen";
import NutritionDashboard from "./NutritionDashboard";
import ScheduleScreen from "./ScheduleScreen";
import RecipesScreen from "./RecipesScreen";
import ReportsScreen from "./ReportsScreen";
import HydrationScreen from "./HydrationScreen";
import MealPlannerScreen from "./MealPlannerScreen";
import SettingsScreen from "./SettingsScreen";
import Blueprint from "./Blueprint";

const TABS = [
  { id: "home",      label: "Today"       },
  { id: "nutrition", label: "Nutrition"   },
  { id: "schedule",  label: "Schedule"    },
  { id: "meal-plan", label: "🍳 Meal Plan" },
  { id: "blueprint", label: "🏅 Blueprint" },
  { id: "reports",   label: "Reports"     },
  { id: "hydration", label: "💧 Hydration" },
];

export default function AppShell({ athlete: initialAthlete, parent, initialTab = "home", isNewAccount = false, onUnlockApp, onSignOut }) {
  const [tab, setTab]           = useState(initialTab);
  const [athlete, setAthlete]   = useState(initialAthlete);
  const [showSettings, setShowSettings] = useState(false);
  const [newAccount, setNewAccount] = useState(isNewAccount);

  function handleUnlockAndNavigate(tabId) {
    setNewAccount(false);
    onUnlockApp?.();
    setTab(tabId);
  }

  const [freshImport, setFreshImport] = useState(false);
  const tabBarRef = useRef(null);

  // Scroll tab bar so the active tab is always visible
  useEffect(() => {
    const bar = tabBarRef.current;
    if (!bar) return;
    const activeBtn = bar.querySelector("[data-active='true']");
    if (activeBtn) {
      const { offsetLeft, offsetWidth } = activeBtn;
      const { scrollLeft, clientWidth } = bar;
      if (offsetLeft < scrollLeft) {
        bar.scrollTo({ left: offsetLeft - 16, behavior: "smooth" });
      } else if (offsetLeft + offsetWidth > scrollLeft + clientWidth) {
        bar.scrollTo({ left: offsetLeft + offsetWidth - clientWidth + 16, behavior: "smooth" });
      }
    }
  }, [tab]);

  function handleScheduleImported() {
    setFreshImport(true);
    setTab("meal-plan");
  }

  // Blueprint only shows during first-run onboarding flow
  const visibleTabs = newAccount
    ? TABS.filter(t => t.id === "blueprint")
    : TABS.filter(t => t.id !== "blueprint");

  const initials = `${athlete.first_name?.[0] || ""}${athlete.last_name?.[0] || ""}`.toUpperCase();

  return (
    <div style={s.wrapper}>
      <div style={s.card}>

        {/* Top bar */}
        <div style={s.topBar}>
          <div>
            <div style={s.logo}>⚽ FuelUp Youth</div>
            <div style={s.athleteLabel}>{athlete.first_name} {athlete.last_name}</div>
          </div>
          <button
            style={s.avatarBtn}
            onClick={() => setShowSettings(true)}
            title="Settings"
          >
            <div style={s.avatarCircle}>{initials}</div>
            <div style={s.gearBadge}>⚙</div>
          </button>
        </div>

        {/* Tab bar */}
        <div style={s.tabBar} ref={tabBarRef}>
          {visibleTabs.map(t => (
            <button
              key={t.id}
              data-active={tab === t.id}
              style={{ ...s.tab, ...(tab === t.id ? s.tabActive : {}) }}
              onClick={() => { setShowSettings(false); setTab(t.id); }}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* Main content */}
        <div style={s.content}>
          {tab === "home"      && <HomeScreen         athlete={athlete} onNavigate={setTab} />}
          {tab === "nutrition" && <NutritionDashboard athlete={athlete} />}
          {tab === "schedule"  && <ScheduleScreen     athlete={athlete} onScheduleImported={handleScheduleImported} />}
          {tab === "recipes"   && <RecipesScreen      athlete={athlete} />}
          {tab === "meal-plan" && <MealPlannerScreen   athlete={athlete} onNavigate={setTab} freshImport={freshImport} onFreshImportSeen={() => setFreshImport(false)} />}
          {tab === "blueprint" && <Blueprint           athlete={athlete} onAddSchedule={newAccount ? () => handleUnlockAndNavigate("schedule") : null} />}
          {tab === "reports"   && <ReportsScreen      athlete={athlete} />}
          {tab === "hydration" && <HydrationScreen    athlete={athlete} />}
        </div>

        {/* Settings overlay */}
        {showSettings && (
          <>
            {/* Backdrop */}
            <div style={s.backdrop} onClick={() => setShowSettings(false)} />

            {/* Drawer */}
            <div style={s.drawer}>
              <div style={s.drawerHeader}>
                <div style={s.drawerTitle}>Settings</div>
                <button style={s.drawerClose} onClick={() => setShowSettings(false)}>✕</button>
              </div>
              <div style={s.drawerBody}>
                <SettingsScreen
                  athlete={athlete}
                  parent={parent}
                  onSave={(updated) => { setAthlete(updated); }}
                  onSignOut={onSignOut}
                  onClose={() => setShowSettings(false)}
                />
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

const s = {
  wrapper: {
    minHeight: "100vh",
    background: "linear-gradient(135deg, #0f4c35 0%, #1a7a54 100%)",
    display: "flex",
    justifyContent: "center",
    padding: "20px",
    fontFamily: "'Inter', -apple-system, sans-serif",
  },
  card: {
    background: "#fff",
    borderRadius: "20px",
    width: "100%",
    maxWidth: "700px",
    boxShadow: "0 24px 60px rgba(0,0,0,0.25)",
    height: "fit-content",
    overflow: "hidden",
    position: "relative",
  },

  topBar: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "18px 28px 12px",
    borderBottom: "1px solid #e5e7eb",
  },
  logo: { fontSize: "20px", fontWeight: "800", color: "#0f4c35" },
  athleteLabel: { fontSize: "13px", color: "#6b7280", marginTop: "1px" },

  avatarBtn: {
    position: "relative",
    background: "none",
    border: "none",
    cursor: "pointer",
    padding: "0",
    display: "flex",
    alignItems: "center",
  },
  avatarCircle: {
    width: "40px",
    height: "40px",
    borderRadius: "50%",
    background: "#0f4c35",
    color: "#fff",
    fontSize: "14px",
    fontWeight: "800",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    letterSpacing: "0.5px",
  },
  gearBadge: {
    position: "absolute",
    bottom: "-2px",
    right: "-4px",
    background: "#fff",
    borderRadius: "50%",
    width: "16px",
    height: "16px",
    fontSize: "11px",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    boxShadow: "0 1px 4px rgba(0,0,0,0.15)",
  },

  tabBar: {
    display: "flex",
    borderBottom: "1.5px solid #e5e7eb",
    padding: "0 28px",
    overflowX: "auto",
    scrollbarWidth: "none",
  },
  tab: {
    background: "none",
    border: "none",
    borderBottom: "2.5px solid transparent",
    padding: "12px 14px",
    fontSize: "13px",
    fontWeight: "600",
    color: "#9ca3af",
    cursor: "pointer",
    marginBottom: "-1.5px",
    whiteSpace: "nowrap",
  },
  tabActive: { color: "#0f4c35", borderBottomColor: "#0f4c35" },

  content: { padding: "28px" },

  // Settings overlay
  backdrop: {
    position: "absolute",
    inset: 0,
    background: "rgba(0,0,0,0.35)",
    zIndex: 10,
    borderRadius: "20px",
  },
  drawer: {
    position: "absolute",
    top: 0,
    right: 0,
    bottom: 0,
    width: "min(380px, 100%)",
    background: "#fff",
    zIndex: 11,
    borderRadius: "0 20px 20px 0",
    display: "flex",
    flexDirection: "column",
    boxShadow: "-8px 0 32px rgba(0,0,0,0.15)",
    animation: "slideIn 0.22s ease",
  },
  drawerHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "20px 24px 16px",
    borderBottom: "1.5px solid #e5e7eb",
    flexShrink: 0,
  },
  drawerTitle: { fontSize: "17px", fontWeight: "800", color: "#111827" },
  drawerClose: {
    background: "#f3f4f6",
    border: "none",
    borderRadius: "50%",
    width: "30px",
    height: "30px",
    fontSize: "14px",
    cursor: "pointer",
    color: "#6b7280",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontWeight: "700",
  },
  drawerBody: {
    flex: 1,
    overflowY: "auto",
    padding: "20px 24px 28px",
  },
};
