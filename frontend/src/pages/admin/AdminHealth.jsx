import { useEffect, useRef, useState } from "react";
import { adminFetch, AuthError } from "./adminApi";
import { C, FONT_DISPLAY } from "./theme";
import { Card, Button, Skeleton, EmptyState, ErrorRetry } from "./ui";

const TITLES = {
  bedrock_ping: "Bedrock · ping",
  bedrock_inference: "Bedrock · inference",
  gmail_smtp: "Gmail SMTP",
  db_writable: "Database",
  disk_space: "Disk",
  scheduler_notifications: "Notif. scheduler",
  scheduler_calendar_sync: "Calendar scheduler",
  calendar_sync_systemic: "Sync feeds",
  expo_push: "Expo push",
};

function parseUtc(iso) {
  if (!iso) return null;
  let s = iso.replace(" ", "T");
  if (!/[zZ]|[+-]\d\d:?\d\d$/.test(s)) s += "Z"; // stored values are UTC-naive
  const d = new Date(s);
  return isNaN(d) ? null : d;
}
function timeAgo(iso) {
  const d = parseUtc(iso);
  if (!d) return "—";
  const secs = Math.floor((Date.now() - d.getTime()) / 1000);
  if (secs < 60) return "just now";
  const m = Math.floor(secs / 60);
  if (m < 60) return `${m} min ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

// Status → color. Disk gets amber early-warning at ≥70% even while still green.
function dotColor(check) {
  if (check.status === "red") return C.danger;
  if (check.status === "unknown") return C.text3;
  if (check.check_name === "disk_space" && (check.metric_value ?? 0) >= 70) return C.warm;
  return C.brandMid;
}
function overallMeta(overall, redCount) {
  if (overall === "red") return { color: C.danger, label: `${redCount} ${redCount === 1 ? "issue" : "issues"}` };
  if (overall === "unknown") return { color: C.text3, label: "Starting up" };
  return { color: C.brandMid, label: "All systems green" };
}

function Dot({ color, size = 12 }) {
  return <span style={{ display: "inline-block", width: size, height: size, borderRadius: "50%", background: color, flexShrink: 0 }} />;
}

export default function AdminHealth({ onLoggedOut }) {
  const [data, setData] = useState(null);
  const [incidents, setIncidents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [running, setRunning] = useState(false);
  const [cooldown, setCooldown] = useState(0);
  const timerRef = useRef(null);

  useEffect(() => {
    load();
    return () => clearTimeout(timerRef.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function load() {
    setLoading(true);
    setError("");
    try {
      const [snap, inc] = await Promise.all([
        adminFetch("/health"),
        adminFetch("/health/incidents?limit=50"),
      ]);
      setData(snap);
      setIncidents(inc.items || []);
    } catch (err) {
      if (err instanceof AuthError) return onLoggedOut();
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function checkNow() {
    if (running || cooldown > 0) return;
    setRunning(true);
    try {
      const snap = await adminFetch("/health/run", { method: "POST" });
      setData(snap);
      const inc = await adminFetch("/health/incidents?limit=50");
      setIncidents(inc.items || []);
      // disable for 60s
      setCooldown(60);
      timerRef.current = setInterval(() => {
        setCooldown((n) => {
          if (n <= 1) { clearInterval(timerRef.current); return 0; }
          return n - 1;
        });
      }, 1000);
    } catch (err) {
      if (err instanceof AuthError) return onLoggedOut();
      setError(err.message);
    } finally {
      setRunning(false);
    }
  }

  if (loading) return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      <Skeleton height={28} width={200} />
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(200px,1fr))", gap: 12 }}>
        {Array.from({ length: 8 }).map((_, i) => <Skeleton key={i} height={92} />)}
      </div>
    </div>
  );
  if (error) return <ErrorRetry message={error} onRetry={load} />;
  if (!data) return null;

  const redCount = data.checks.filter((c) => c.status === "red").length;
  const om = overallMeta(data.overall, redCount);

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 18, flexWrap: "wrap", gap: 12 }}>
        <h1 style={{ font: `800 24px ${FONT_DISPLAY}`, color: C.text1, margin: 0 }}>System Health</h1>
        <div style={{ display: "flex", gap: 14, alignItems: "center" }}>
          <span style={{ display: "inline-flex", gap: 8, alignItems: "center", font: `700 14px ${FONT_DISPLAY}`, color: om.color }}>
            <Dot color={om.color} /> Overall: {om.label}
          </span>
          <Button variant="ghost" onClick={checkNow} disabled={running || cooldown > 0}>
            {running ? "Checking…" : cooldown > 0 ? `Check now (${cooldown}s)` : "Check now"}
          </Button>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(210px,1fr))", gap: 12, marginBottom: 22 }}>
        {data.checks.map((c) => {
          const color = dotColor(c);
          const amber = color === C.warm;
          return (
            <Card key={c.check_name} style={{
              padding: 14,
              borderColor: c.status === "red" ? C.dangerBorder : amber ? "#f0d9a8" : C.border,
              background: c.status === "red" ? C.dangerBg : amber ? C.warmLight : C.surface,
            }}>
              <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                <Dot color={color} />
                <span style={{ font: `800 14px ${FONT_DISPLAY}`, color: C.text1 }}>
                  {TITLES[c.check_name] || c.check_name}
                </span>
              </div>
              <div style={{ font: `500 13px ${FONT_DISPLAY}`, color: C.text2, marginTop: 6, minHeight: 18 }}>
                {c.detail || (c.status === "unknown" ? "not yet checked" : "—")}
              </div>
              <div style={{ font: `500 11px ${FONT_DISPLAY}`, color: C.text3, marginTop: 6 }}>
                {c.last_checked_at ? timeAgo(c.last_checked_at) : "—"}
              </div>
            </Card>
          );
        })}
      </div>

      <h2 style={{ font: `800 18px ${FONT_DISPLAY}`, color: C.text1, margin: "0 0 12px" }}>Incident history</h2>
      <Card style={{ padding: 0 }}>
        {incidents.length === 0 ? (
          <EmptyState title="No incidents recorded" subtitle="Status transitions will appear here." />
        ) : (
          incidents.map((i) => (
            <div key={i.id} style={{
              display: "flex", gap: 12, alignItems: "baseline", padding: "10px 16px",
              borderBottom: `1px solid ${C.border}`, font: `500 13px ${FONT_DISPLAY}`, color: C.text1,
            }}>
              <span style={{ color: C.text3, minWidth: 96, fontSize: 12 }}>
                {(i.created_at || "").slice(5, 16).replace("T", " ")}
              </span>
              <span style={{ minWidth: 150, fontWeight: 700 }}>{TITLES[i.check_name] || i.check_name}</span>
              <span style={{ display: "inline-flex", gap: 5, alignItems: "center" }}>
                <Dot color={i.from_status === "red" ? C.danger : i.from_status === "green" ? C.brandMid : C.text3} size={8} />
                →
                <Dot color={i.to_status === "red" ? C.danger : i.to_status === "green" ? C.brandMid : C.text3} size={8} />
              </span>
              <span style={{ color: C.text2, flex: 1 }}>{i.detail}</span>
            </div>
          ))
        )}
      </Card>
    </div>
  );
}
