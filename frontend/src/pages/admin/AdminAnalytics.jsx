import { useEffect, useState } from "react";
import { adminFetch, AuthError } from "./adminApi";
import { C, FONT_DISPLAY } from "./theme";
import { Card, Button, StatCard, LineChart, FunnelBars, PieChart, Skeleton, ErrorRetry } from "./ui";

export default function AdminAnalytics({ onLoggedOut }) {
  const [overview, setOverview] = useState(null);
  const [funnel, setFunnel] = useState(null);
  const [events, setEvents] = useState(null);
  const [retention, setRetention] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    load(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function load(force) {
    force ? setRefreshing(true) : setLoading(true);
    setError("");
    try {
      const f = force ? "?force=true" : "";
      const [ov, fn, ev, rt] = await Promise.all([
        adminFetch(`/analytics/overview${force ? "?force=true" : ""}`),
        adminFetch(`/analytics/funnel`),
        adminFetch(`/analytics/events${f}`),
        adminFetch(`/analytics/retention${f}`),
      ]);
      setOverview(ov); setFunnel(fn); setEvents(ev); setRetention(rt);
    } catch (err) {
      if (err instanceof AuthError) return onLoggedOut();
      setError(err.message);
    } finally { setLoading(false); setRefreshing(false); }
  }

  if (loading) return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      <Skeleton height={28} width={160} />
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(180px,1fr))", gap: 12 }}>
        {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} height={96} />)}
      </div>
      <Skeleton height={220} /><Skeleton height={200} />
    </div>
  );
  if (error) return <ErrorRetry message={error} onRetry={() => load(false)} />;

  const c = overview.cards;
  const asOf = (overview.as_of || "").slice(11, 16);
  const mp = overview.mixpanel_status || { configured: overview.mixpanel_available };
  // Show an info note whenever the Mixpanel Query API isn't usable.
  const mpNote = !mp.available;
  const mpNoteText = mp.plan_gated
    ? "Mixpanel is on the free plan — event-level analytics (top events, retention cohorts) need a paid plan. All database metrics below are live."
    : mp.configured
      ? "Mixpanel Query API is unavailable right now — showing database-backed metrics."
      : "Mixpanel not connected — showing database-backed metrics. Signup, funnel, and health cards are fully available.";

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 18 }}>
        <h1 style={{ font: `800 24px ${FONT_DISPLAY}`, color: C.text1, margin: 0 }}>Analytics</h1>
        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <span style={{ font: `500 13px ${FONT_DISPLAY}`, color: C.text3 }}>as of {asOf} UTC</span>
          <Button variant="ghost" onClick={() => load(true)} disabled={refreshing}>
            {refreshing ? "Refreshing…" : "Refresh"}
          </Button>
        </div>
      </div>

      {mpNote && (
        <div style={{
          font: `500 13px ${FONT_DISPLAY}`, color: C.text2, background: C.warmLight,
          border: `1px solid #f0d9a8`, borderRadius: 10, padding: "8px 14px", marginBottom: 16,
        }}>{mpNoteText}</div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(180px,1fr))", gap: 12, marginBottom: 16 }}>
        <StatCard label={`Signups (${c.signups.window_days}d)`} value={c.signups.value} sub="new families" />
        <StatCard label="Active users (7d)" value={c.active_users_7d.value} sub="athletes with activity" />
        <StatCard label="Families" value={c.families_total.value} sub="total" />
        <StatCard label="Sync adoption" value={`${c.sync_adoption.percent}%`}
          sub={`${c.sync_adoption.connected}/${c.sync_adoption.total} athletes`} />
      </div>

      <Card style={{ marginBottom: 16 }}>
        <SectionTitle>Signups over time ({c.signups.window_days}d)</SectionTitle>
        <LineChart points={overview.signups_over_time.points} />
      </Card>

      <Card style={{ marginBottom: 16 }}>
        <SectionTitle>Activation funnel <Src>DB</Src></SectionTitle>
        <FunnelBars steps={funnel.steps} />
        <div style={{ font: `400 12px ${FONT_DISPLAY}`, color: C.text3, marginTop: 10 }}>{funnel.note}</div>
      </Card>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(300px,1fr))", gap: 16 }}>
        <Card>
          <SectionTitle>Top events (30d) <Src>Mixpanel</Src></SectionTitle>
          <TopEvents events={events} />
        </Card>
        <Card>
          <SectionTitle>App health <Src>DB</Src></SectionTitle>
          <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 14 }}>
            <HealthRow label="Problem reports (7d)" value={overview.app_health.problem_reports_7d} />
            <HealthRow label="Feature ideas (7d)" value={overview.app_health.feature_ideas_7d} />
          </div>
          <div style={{ font: `600 13px ${FONT_DISPLAY}`, color: C.text2, marginBottom: 8 }}>Events: synced vs manual</div>
          <PieChart data={overview.app_health.event_sources} />
        </Card>
      </div>

      <Card style={{ marginTop: 16 }}>
        <SectionTitle>Retention <Src>{retention.source === "mixpanel" ? "Mixpanel" : "DB (WAU)"}</Src></SectionTitle>
        <Retention retention={retention} />
      </Card>
    </div>
  );
}

function SectionTitle({ children }) {
  return <div style={{ font: `700 15px ${FONT_DISPLAY}`, color: C.text1, marginBottom: 12, display: "flex", gap: 8, alignItems: "center" }}>{children}</div>;
}
function Src({ children }) {
  return <span style={{ font: `700 10px ${FONT_DISPLAY}`, color: C.text3, background: C.surface2, border: `1px solid ${C.border}`, borderRadius: 6, padding: "1px 7px", letterSpacing: "0.03em" }}>{children}</span>;
}
function HealthRow({ label, value }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", font: `500 14px ${FONT_DISPLAY}`, color: C.text2 }}>
      <span>{label}</span><span style={{ font: `800 15px ${FONT_DISPLAY}`, color: C.text1 }}>{value}</span>
    </div>
  );
}

function MixpanelUnavailable({ info, subtitle }) {
  const gated = info?.plan_gated;
  return (
    <div style={{
      font: `600 13px ${FONT_DISPLAY}`, color: C.text2, background: C.surface2,
      border: `1px dashed ${C.border2}`, borderRadius: 10, padding: "16px", textAlign: "center",
    }}>
      {gated ? "Requires a Mixpanel paid plan" : (info?.reason || "Mixpanel not connected")}
      <div style={{ font: `400 12px ${FONT_DISPLAY}`, color: C.text3, marginTop: 4 }}>{subtitle}</div>
    </div>
  );
}

function TopEvents({ events }) {
  if (!events || !events.available) {
    return <MixpanelUnavailable info={events}
      subtitle="Top events by volume come from the Mixpanel Query API." />;
  }
  // Mixpanel events endpoint returns { data: { values: { EventName: {date:count} } } }.
  const values = events.data?.data?.values || events.data?.values || {};
  const rows = Object.entries(values).map(([name, series]) => [
    name, Object.values(series).reduce((a, b) => a + b, 0),
  ]).sort((a, b) => b[1] - a[1]).slice(0, 10);
  if (rows.length === 0) return <div style={{ color: C.text3, fontSize: 13 }}>No events in range.</div>;
  return (
    <div>
      {rows.map(([name, count]) => (
        <div key={name} style={{ display: "flex", justifyContent: "space-between", padding: "5px 0", borderBottom: `1px solid ${C.border}`, font: `500 13px ${FONT_DISPLAY}`, color: C.text1 }}>
          <span>{name}</span><span style={{ color: C.text2 }}>{count}</span>
        </div>
      ))}
    </div>
  );
}

function Retention({ retention }) {
  if (retention.source === "mixpanel") {
    return <div style={{ font: `500 13px ${FONT_DISPLAY}`, color: C.text2 }}>
      Mixpanel retention loaded. (Cohort grid rendering uses the raw Mixpanel shape — see network payload.)
    </div>;
  }
  const points = (retention.points || []).map((p) => ({ date: p.week_start, count: p.active }));
  return (
    <>
      {retention.note && <div style={{ font: `400 12px ${FONT_DISPLAY}`, color: C.text3, marginBottom: 8 }}>{retention.note}</div>}
      <LineChart points={points} height={150} />
    </>
  );
}
