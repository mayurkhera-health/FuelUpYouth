import { useState, useEffect } from "react";

const scoreColor = s => s >= 75 ? "#2d6a4f" : s >= 50 ? "#d97706" : "#dc2626";

function getCountdown(events) {
  const now = new Date();
  const upcoming = events
    .filter(e => e.start_time)
    .map(e => {
      const [h, m] = e.start_time.split(":").map(Number);
      const t = new Date(now); t.setHours(h, m, 0, 0);
      return { ...e, eventTime: t, diff: t - now };
    })
    .filter(e => e.diff > 0)
    .sort((a, b) => a.diff - b.diff)[0];

  if (!upcoming) return null;
  const totalMins = Math.floor(upcoming.diff / 60000);
  return {
    hrs: Math.floor(totalMins / 60),
    mins: totalMins % 60,
    totalMins,
    event: upcoming,
  };
}

function getEventLabel(events) {
  if (!events?.length) return "Rest Day";
  const e = events.find(ev => ev.start_time) || events[0];
  const parts = [e.event_name || "Event"];
  if (e.city) parts.push(e.city.replace(/\\/g, "").trim());
  return parts.join(" · ");
}

export default function CountdownHero({ events = [], fuelScore, urgentAction }) {
  const [cd, setCd] = useState(() => getCountdown(events));
  const [pulse, setPulse] = useState(false);

  useEffect(() => {
    const update = () => {
      const next = getCountdown(events);
      setCd(next);
      setPulse(next?.totalMins < 30);
    };
    update();
    const t = setInterval(update, 30000);
    return () => clearInterval(t);
  }, [events]);

  // Blink pulse when < 30 min
  const [visible, setVisible] = useState(true);
  useEffect(() => {
    if (!pulse) { setVisible(true); return; }
    const t = setInterval(() => setVisible(v => !v), 750);
    return () => clearInterval(t);
  }, [pulse]);

  const timerColor = pulse ? "#d97706" : "#2d6a4f";
  const score = fuelScore;
  const scoreClr = score != null ? scoreColor(score) : "#8aa898";
  const eventLabel = getEventLabel(events);
  const hasEvent = !!cd;

  // Shrink bar width for urgent action window
  const windowSecs = urgentAction?.window_duration_secs;

  return (
    <>
      {/* CSS for shrink animation and blink */}
      <style>{`
        @keyframes shrinkBar { from { width: 100%; } to { width: 0%; } }
        @keyframes blinkTxt { 0%,100% { opacity:1; } 50% { opacity:0.5; } }
      `}</style>

      <div style={s.card}>
        {/* Green accent line — only when upcoming event */}
        {hasEvent && <div style={s.accentLine} />}

        <div style={s.top}>
          {/* Left — timer */}
          <div style={s.timerSide}>
            <div style={s.eventLabel}>{eventLabel}</div>
            {hasEvent ? (
              <div style={{ ...s.timerRow, opacity: visible ? 1 : 0.55 }}>
                <span style={{ ...s.timerNum, color: timerColor }}>{cd.hrs}</span>
                <span style={s.timerUnit}>hr</span>
                <span style={{ ...s.timerNum, color: timerColor }}>{String(cd.mins).padStart(2, "0")}</span>
                <span style={s.timerUnit}>min</span>
              </div>
            ) : (
              <div style={s.timerRow}>
                <span style={{ ...s.timerNum, color: "#4a6358" }}>0</span>
                <span style={s.timerUnit}>hr</span>
                <span style={{ ...s.timerNum, color: "#4a6358" }}>00</span>
                <span style={s.timerUnit}>min</span>
              </div>
            )}
            {!hasEvent && events.length > 0 && (
              <div style={{ fontSize: "12px", color: "#4a6358", fontFamily: "'DM Sans', sans-serif", marginTop: "2px" }}>In progress or complete</div>
            )}
          </div>

          {/* Right — mini fuel score */}
          <div style={s.scoreSide}>
            <div style={s.scoreLabel}>Fuel score</div>
            <div style={{ ...s.scoreNum, color: scoreClr }}>{score ?? "—"}</div>
            <div style={s.scoreDenom}>/ 100</div>
            <div style={s.scoreBar}>
              <div style={{ ...s.scoreBarFill, width: `${Math.min(100, score ?? 0)}%`, background: scoreClr }} />
            </div>
          </div>
        </div>

        {/* Urgent action block */}
        {urgentAction && (
          <div style={s.actionWrap}>
            <div style={s.action}>
              <div style={s.actionIcon}>{urgentAction.icon}</div>
              <div style={s.actionCenter}>
                <div style={s.actionTitle}>{urgentAction.title}</div>
                <div style={s.actionSub}>{urgentAction.sub}</div>
                <div style={s.actionWindow}>{urgentAction.window}</div>
                <div style={s.shrinkTrack}>
                  <div
                    key={urgentAction.title}
                    style={{
                      ...s.shrinkFill,
                      animation: windowSecs ? `shrinkBar ${windowSecs}s linear forwards` : "none",
                    }}
                  />
                </div>
              </div>
              <div style={s.actionArrow}>→</div>
            </div>
          </div>
        )}
      </div>
    </>
  );
}

const s = {
  card:         { background: "#ffffff", border: "1.5px solid #dce8e0", borderRadius: "14px", overflow: "hidden", marginBottom: "0" },
  accentLine:   { height: "2px", background: "#2d6a4f" },
  top:          { display: "flex", justifyContent: "space-between", alignItems: "flex-start", padding: "14px 16px 10px" },

  timerSide:    { flex: 1 },
  eventLabel:   { fontSize: "13px", fontFamily: "'DM Sans', sans-serif", fontWeight: "500", letterSpacing: "0.04em", textTransform: "uppercase", color: "#4a6358", marginBottom: "6px" },
  timerRow:     { display: "flex", alignItems: "baseline", gap: "3px", transition: "opacity 0.3s" },
  timerNum:     { fontSize: "42px", fontWeight: "800", fontFamily: "'Nunito', sans-serif", letterSpacing: "-0.05em", lineHeight: 1 },
  timerUnit:    { fontSize: "15px", fontFamily: "'DM Sans', sans-serif", fontWeight: "500", color: "#4a6358", marginRight: "6px" },

  scoreSide:    { flexShrink: 0, textAlign: "right", paddingLeft: "12px" },
  scoreLabel:   { fontSize: "13px", fontFamily: "'DM Sans', sans-serif", fontWeight: "700", textTransform: "uppercase", letterSpacing: "0.08em", color: "#1b3a2a", marginBottom: "3px" },
  scoreNum:     { fontSize: "22px", fontWeight: "800", fontFamily: "'Nunito', sans-serif", lineHeight: 1 },
  scoreDenom:   { fontSize: "12px", fontFamily: "'DM Sans', sans-serif", fontWeight: "500", color: "#4a6358" },
  scoreBar:     { width: "64px", height: "2px", background: "#dce8e0", borderRadius: "2px", overflow: "hidden", marginTop: "4px", marginLeft: "auto" },
  scoreBarFill: { height: "100%", borderRadius: "2px", transition: "width 0.5s ease" },

  actionWrap:   { padding: "0 14px 14px" },
  action:       { background: "linear-gradient(135deg, #2d6a4f, #52b788)", borderRadius: "10px", padding: "13px 14px", display: "flex", alignItems: "center", gap: "12px", cursor: "pointer" },
  actionIcon:   { fontSize: "22px", flexShrink: 0 },
  actionCenter: { flex: 1, minWidth: 0 },
  actionTitle:  { fontSize: "16px", fontWeight: "800", fontFamily: "'Nunito', sans-serif", color: "#ffffff", letterSpacing: "-0.01em", marginBottom: "2px" },
  actionSub:    { fontSize: "13px", fontFamily: "'DM Sans', sans-serif", fontWeight: "400", color: "rgba(255,255,255,0.95)", lineHeight: 1.6, marginBottom: "2px" },
  actionWindow: { fontSize: "12px", fontFamily: "'DM Sans', sans-serif", fontWeight: "500", color: "rgba(255,255,255,0.82)", letterSpacing: "0.02em", marginBottom: "6px" },
  shrinkTrack:  { height: "3px", background: "rgba(255,255,255,0.2)", borderRadius: "2px", overflow: "hidden" },
  shrinkFill:   { height: "100%", width: "100%", background: "rgba(255,255,255,0.6)", borderRadius: "2px" },
  actionArrow:  { fontSize: "20px", color: "rgba(255,255,255,0.6)", flexShrink: 0 },
};
