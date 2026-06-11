import { useState } from "react";
import MissionItem from "./MissionItem";

const API = import.meta.env.VITE_API_URL ?? "";

export default function DailyMission({ missionItems, eventType, date, athleteId, onToast }) {
  const [doneSet, setDoneSet] = useState(
    () => new Set(missionItems.filter(i => i.state === "done").map(i => i.item_type))
  );

  const items = missionItems ?? [];
  const doneCount = items.filter(i => doneSet.has(i.item_type)).length;
  const pct = items.length > 0 ? Math.round((doneCount / items.length) * 100) : 0;

  async function handleToggle(item) {
    const wasDone = doneSet.has(item.item_type);
    setDoneSet(prev => {
      const next = new Set(prev);
      wasDone ? next.delete(item.item_type) : next.add(item.item_type);
      return next;
    });
    if (!wasDone) {
      onToast?.("✓ Logged — fuel score updating");
      try {
        await fetch(`${API}/api/meal-logs/`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            athlete_id: athleteId,
            meal_type: item.item_type,
            description: item.label,
            logged_at: new Date().toISOString(),
          }),
        });
      } catch (_) {}
    }
  }

  const dayLabel = eventType
    ? eventType.charAt(0).toUpperCase() + eventType.slice(1) + " Day"
    : "Today";
  const dateStr = date
    ? new Date(date + "T12:00:00").toLocaleDateString("en-US", { month: "short", day: "numeric" })
    : "";

  return (
    <div style={s.card}>
      <div style={s.header}>
        <div>
          <div style={s.eyebrow}>{dayLabel} · {dateStr}</div>
          <div style={s.title}>Today's Mission</div>
        </div>
        <div style={s.progress}>
          <div style={s.count}>
            {doneCount}<span style={s.denom}>/{items.length}</span>
          </div>
          <span style={s.completeLabel}>complete</span>
          <div style={s.bar}><div style={{ ...s.barFill, width: `${pct}%` }} /></div>
        </div>
      </div>
      {items.map((item, idx) => (
        <div key={item.item_type} style={idx === items.length - 1 ? { borderBottom: "none" } : {}}>
          <MissionItem
            item={item}
            isDone={doneSet.has(item.item_type)}
            onToggle={() => handleToggle(item)}
          />
        </div>
      ))}
    </div>
  );
}

const s = {
  card:          { background: "#fff", borderRadius: "14px", border: "1px solid #dce8e0", overflow: "hidden", marginTop: "10px" },
  header:        { padding: "13px 14px 11px", borderBottom: "1px solid #dce8e0", display: "flex", alignItems: "flex-start", justifyContent: "space-between" },
  eyebrow:       { fontSize: "12px", textTransform: "uppercase", letterSpacing: ".1em", color: "#4a6358", marginBottom: "2px" },
  title:         { fontFamily: "'Nunito', sans-serif", fontSize: "19px", fontWeight: "800", letterSpacing: "-.02em", color: "#1b3a2a" },
  progress:      { textAlign: "right" },
  count:         { fontFamily: "'Nunito', sans-serif", fontSize: "25px", fontWeight: "800", letterSpacing: "-.04em", color: "#2d6a4f", lineHeight: "1" },
  denom:         { fontSize: "17px", color: "#4a6358", fontWeight: "400" },
  completeLabel: { fontSize: "14px", color: "#4a6358", fontWeight: "400", display: "block", marginBottom: "4px" },
  bar:           { width: "64px", height: "2px", background: "#f4f8f5", borderRadius: "2px", overflow: "hidden", marginLeft: "auto" },
  barFill:       { height: "100%", background: "#2d6a4f", borderRadius: "2px", transition: "width 0.4s ease" },
};
