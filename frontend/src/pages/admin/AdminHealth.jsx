import { useEffect, useRef, useState } from "react";
import { adminFetch, AuthError } from "./adminApi";
import { C, FONT_DISPLAY } from "./theme";
import { Card, Button, Skeleton, EmptyState, ErrorRetry } from "./ui";

// Checks whose metric_value is a genuine response time (ms). Only these get a
// "latency" pill — we never fabricate a latency for checks that don't have one.
const LATENCY_CHECKS = new Set(["bedrock_ping", "bedrock_inference", "gmail_smtp"]);

// Friendly name + a one-line "what this watches" for each sensor, so the page
// makes sense to a non-engineer. Keyed by backend check_name.
const META = {
  bedrock_ping: { title: "AI service", blurb: "Connection to the AI behind coaching & blueprints" },
  gmail_smtp: { title: "Email delivery", blurb: "Can sign in to the mailbox that sends emails" },
  db_writable: { title: "Database", blurb: "App database accepts reads & writes" },
  disk_space: { title: "Storage", blurb: "Free space on the data volume" },
  scheduler_notifications: { title: "Reminder scheduler", blurb: "The 15-min job that sends fueling reminders" },
  scheduler_calendar_sync: { title: "Calendar sync job", blurb: "The 6-hour job that refreshes connected calendars" },
  calendar_sync_systemic: { title: "Calendar feeds", blurb: "BYGA / PlayMetrics feeds importing successfully" },
  expo_push: { title: "Push notifications", blurb: "Recent push sends to phones are landing" },
  bedrock_inference: { title: "AI responses", blurb: "The AI can generate a reply · checked once a day" },
};

// Human-readable detail — reassuring copy for the not-yet-run (pending) states,
// which otherwise read like failures. Green/red details from the backend are
// already clear, so they pass through.
const PENDING_COPY = {
  scheduler_notifications: "Waiting for first run — within 15 min of a deploy",
  scheduler_calendar_sync: "Waiting for first run — within 6 hours",
  calendar_sync_systemic: "No connected calendars to check yet",
  expo_push: "No push notifications sent recently",
  bedrock_inference: "Runs automatically once a day (09:00 UTC)",
};

function humanDetail(c) {
  if (c.status === "unknown") return PENDING_COPY[c.check_name] || "Waiting for first check";
  return c.detail || "—";
}

// Status → chip. Disk gets an amber "Watch" at ≥70% even while technically green.
function statusChip(c) {
  if (c.status === "red") return { label: "Down", fg: C.danger, bg: C.dangerBg, border: C.dangerBorder, dot: C.danger };
  if (c.check_name === "disk_space" && c.status === "green" && (c.metric_value ?? 0) >= 70)
    return { label: "Watch", fg: "#9a6a1e", bg: C.warmLight, border: "#f0d9a8", dot: C.warm };
  if (c.status === "green") return { label: "Healthy", fg: C.brand, bg: C.brandGhost, border: C.brandLight, dot: C.brandMid };
  return { label: "Pending", fg: C.text3, bg: C.surface2, border: C.border, dot: C.text3 };
}

// Card tone by chip label: a 4px status-color top strip + ultra-light surface
// ("Infrastructure Pulse" look). Pending stays neutral so it never reads alarming.
function cardTone(label) {
  if (label === "Down") return { accent: C.danger, bg: C.dangerBg };
  if (label === "Watch") return { accent: C.warm, bg: C.warmLight };
  if (label === "Healthy") return { accent: C.brandMid, bg: C.brandGhost };
  return { accent: C.border2, bg: C.surface };
}

// Severity pill for a log row's resulting status (spec's pill-style badges).
function severityPill(toStatus) {
  if (toStatus === "red") return { label: "Critical", fg: "#991b1b", bg: C.dangerBg, border: C.dangerBorder };
  if (toStatus === "green") return { label: "Resolved", fg: C.brand, bg: C.brandGhost, border: C.brandLight };
  return { label: "Pending", fg: C.text3, bg: C.surface2, border: C.border };
}

function parseUtc(iso) {
  if (!iso) return null;
  let s = iso.replace(" ", "T");
  if (!/[zZ]|[+-]\d\d:?\d\d$/.test(s)) s += "Z";
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

// Overall reads from the founder's POV: is anything actually broken? Pending
// checks are informational, not a problem — they never turn the banner red.
function overallMeta(checks) {
  const red = checks.filter((c) => c.status === "red").length;
  const pending = checks.filter((c) => c.status === "unknown").length;
  if (red > 0) return { color: C.danger, label: `${red} ${red === 1 ? "issue needs" : "issues need"} attention` };
  if (pending > 0) return { color: C.brandMid, label: `All healthy · ${pending} still checking in` };
  return { color: C.brandMid, label: "All systems healthy" };
}

function Dot({ color, size = 11 }) {
  return <span style={{ display: "inline-block", width: size, height: size, borderRadius: "50%", background: color, flexShrink: 0 }} />;
}

export default function AdminHealth({ onLoggedOut }) {
  const [data, setData] = useState(null);
  const [incidents, setIncidents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [running, setRunning] = useState(false);
  const [cooldown, setCooldown] = useState(0);
  const [showAllLogs, setShowAllLogs] = useState(false);
  const timerRef = useRef(null);

  useEffect(() => {
    load();
    return () => clearInterval(timerRef.current);
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
      setCooldown(60);
      timerRef.current = setInterval(() => {
        setCooldown((n) => { if (n <= 1) { clearInterval(timerRef.current); return 0; } return n - 1; });
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
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(240px,1fr))", gap: 12 }}>
        {Array.from({ length: 8 }).map((_, i) => <Skeleton key={i} height={110} />)}
      </div>
    </div>
  );
  if (error) return <ErrorRetry message={error} onRetry={load} />;
  if (!data) return null;

  const om = overallMeta(data.checks);

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6, flexWrap: "wrap", gap: 12 }}>
        <h1 style={{ font: `800 24px ${FONT_DISPLAY}`, color: C.text1, margin: 0 }}>System Health</h1>
        <div style={{ display: "flex", gap: 14, alignItems: "center" }}>
          <span style={{ display: "inline-flex", gap: 8, alignItems: "center", font: `700 14px ${FONT_DISPLAY}`, color: om.color }}>
            <Dot color={om.color} /> {om.label}
          </span>
          <Button variant="ghost" onClick={checkNow} disabled={running || cooldown > 0}>
            {running ? "Checking…" : cooldown > 0 ? `Check now (${cooldown}s)` : "Check now"}
          </Button>
        </div>
      </div>
      <p style={{ font: `400 13px ${FONT_DISPLAY}`, color: C.text3, margin: "0 0 18px" }}>
        Live status of the services FuelUp depends on. “Pending” checks simply haven’t run since the last deploy — not a problem.
      </p>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(240px,1fr))", gap: 14, marginBottom: 24 }}>
        {data.checks.map((c) => {
          const meta = META[c.check_name] || { title: c.check_name, blurb: "" };
          const chip = statusChip(c);
          const tone = cardTone(chip.label);
          const showLatency = LATENCY_CHECKS.has(c.check_name) && c.status === "green" && c.metric_value != null;
          return (
            <Card key={c.check_name} style={{
              padding: 16, borderColor: C.border, background: tone.bg,
              borderTop: `4px solid ${tone.accent}`,
            }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8 }}>
                <span style={{ font: `800 15px ${FONT_DISPLAY}`, color: C.text1 }}>{meta.title}</span>
                <span style={{
                  display: "inline-flex", gap: 5, alignItems: "center", flexShrink: 0,
                  font: `700 11px ${FONT_DISPLAY}`, color: chip.fg, background: chip.bg,
                  border: `1px solid ${chip.border}`, borderRadius: 999, padding: "2px 9px",
                }}>
                  <Dot color={chip.dot} size={7} /> {chip.label}
                </span>
              </div>
              <div style={{ font: `400 12px ${FONT_DISPLAY}`, color: C.text3, marginTop: 4, minHeight: 30 }}>
                {meta.blurb}
              </div>
              {showLatency && (
                <div style={{
                  display: "inline-flex", gap: 5, alignItems: "center", marginTop: 8,
                  font: `700 11px ${FONT_DISPLAY}`, color: C.text2, background: C.surface,
                  border: `1px solid ${C.border}`, borderRadius: 8, padding: "3px 8px",
                }}>
                  ⚡ {Math.round(c.metric_value)} ms
                  <span style={{ color: C.text3, fontWeight: 500 }}>response</span>
                </div>
              )}
              <div style={{ font: `600 13px ${FONT_DISPLAY}`, color: C.text2, marginTop: 8, minHeight: 18 }}>
                {humanDetail(c)}
              </div>
              <div style={{ font: `500 11px ${FONT_DISPLAY}`, color: C.text3, marginTop: 6 }}>
                Last checked {c.last_checked_at ? timeAgo(c.last_checked_at) : "—"}
              </div>
            </Card>
          );
        })}
      </div>

      <h2 style={{ font: `800 18px ${FONT_DISPLAY}`, color: C.text1, margin: "0 0 4px" }}>Recent changes</h2>
      <p style={{ font: `400 13px ${FONT_DISPLAY}`, color: C.text3, margin: "0 0 12px" }}>
        Every time a sensor changes state it’s logged here.
      </p>
      <Card style={{ padding: 0 }}>
        {incidents.length === 0 ? (
          <EmptyState title="Nothing to report" subtitle="Status changes will show up here." />
        ) : (
          (showAllLogs ? incidents : incidents.slice(0, 15)).map((i) => {
            const meta = META[i.check_name] || { title: i.check_name };
            const label = (s) => s === "red" ? "Down" : s === "green" ? "Healthy" : "Pending";
            const col = (s) => s === "red" ? C.danger : s === "green" ? C.brandMid : C.text3;
            const sev = severityPill(i.to_status);
            return (
              <div key={i.id} style={{
                display: "flex", gap: 12, alignItems: "center", padding: "11px 16px",
                borderBottom: `1px solid ${C.border}`, font: `500 13px ${FONT_DISPLAY}`, color: C.text1, flexWrap: "wrap",
              }}>
                <span style={{ color: C.text3, minWidth: 92, fontSize: 12 }}>
                  {(i.created_at || "").slice(5, 16).replace("T", " ")}
                </span>
                <span style={{ minWidth: 150, fontWeight: 700 }}>{meta.title}</span>
                <span style={{ display: "inline-flex", gap: 6, alignItems: "center", color: C.text2, fontSize: 12 }}>
                  <Dot color={col(i.from_status)} size={8} /> {label(i.from_status)}
                  <span style={{ color: C.text3 }}>→</span>
                  <Dot color={col(i.to_status)} size={8} /> {label(i.to_status)}
                </span>
                <span style={{ color: C.text3, flex: 1, minWidth: 140, fontSize: 12 }}>{i.detail}</span>
                <span style={{
                  flexShrink: 0, font: `700 10px ${FONT_DISPLAY}`, letterSpacing: "0.04em", textTransform: "uppercase",
                  color: sev.fg, background: sev.bg, border: `1px solid ${sev.border}`, borderRadius: 999, padding: "2px 9px",
                }}>{sev.label}</span>
              </div>
            );
          })
        )}
        {incidents.length > 15 && (
          <button onClick={() => setShowAllLogs((v) => !v)} style={{
            display: "block", width: "100%", cursor: "pointer", background: "transparent",
            border: "none", borderTop: `1px solid ${C.border}`, padding: "12px",
            font: `700 13px ${FONT_DISPLAY}`, color: C.brand,
          }}>
            {showAllLogs ? "Show less" : `Load more logs (${incidents.length - 15} more)`}
          </button>
        )}
      </Card>
    </div>
  );
}
