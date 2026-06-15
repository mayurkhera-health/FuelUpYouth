import { useState, useRef, useEffect } from "react";
import MissionItem  from "./MissionItem";
import VoiceCapture from "./VoiceCapture";
import TextCapture  from "./TextCapture";

const API = import.meta.env.VITE_API_URL ?? "";

function getMissionStatus(item, now = new Date()) {
  if (item.logged) return "done";
  const cleanTime = (item.time || "").replace("~", "").trim();
  if (!cleanTime || cleanTime === "All day") return "upcoming";
  try {
    const parts = cleanTime.split(" ");
    const timePart = parts[0];
    const meridiem = parts[1];
    const [hoursStr, minsStr] = timePart.split(":");
    let hours = parseInt(hoursStr, 10);
    const mins = parseInt(minsStr || "0", 10);
    if (meridiem === "PM" && hours !== 12) hours += 12;
    if (meridiem === "AM" && hours === 12) hours = 0;
    const mealTime = new Date(now);
    mealTime.setHours(hours, mins, 0, 0);
    const diffMins = (mealTime - now) / 60000;
    if (diffMins >= -30 && diffMins <= 90) return "active";
    if (diffMins < -30) return "done";
    return "upcoming";
  } catch {
    return "upcoming";
  }
}

const TAG_MAP = { done: "DONE", active: "NOW", upcoming: "UPCOMING" };

export default function DailyMission({ missionItems, eventType, eventLabel, date, athleteId, onToast }) {
  const [doneSet, setDoneSet] = useState(
    () => new Set((missionItems || []).filter((i) => i.logged).map((i) => i.meal_type))
  );

  // Phase machine: 'closed' | 'voice' | 'text'
  const [phase, setPhase]               = useState("closed");
  const [activeWindow, setActiveWindow] = useState(null);
  const [cameraAvailable, setCameraAvailable] = useState(true);

  const photoInputRef = useRef(null);

  // Check camera once on mount
  useEffect(() => {
    async function checkCamera() {
      try {
        if (!navigator.mediaDevices?.enumerateDevices) {
          setCameraAvailable(false);
          return;
        }
        const devices = await navigator.mediaDevices.enumerateDevices();
        const hasCamera = devices.some((d) => d.kind === "videoinput");
        if (!hasCamera) { setCameraAvailable(false); return; }
        // Permission state check (where supported)
        if (navigator.permissions?.query) {
          const perm = await navigator.permissions.query({ name: "camera" });
          if (perm.state === "denied") setCameraAvailable(false);
        }
      } catch {
        // enumerateDevices failed — assume camera present, let the input handle it
      }
    }
    void checkCamera();
  }, []);

  const items     = missionItems ?? [];
  const doneCount = items.filter((i) => doneSet.has(i.meal_type)).length;
  const pct       = items.length > 0 ? Math.round((doneCount / items.length) * 100) : 0;

  const dayLabel = eventLabel
    || (eventType ? eventType.charAt(0).toUpperCase() + eventType.slice(1) + " Day" : "Today");
  const dateStr = date
    ? new Date(date + "T12:00:00").toLocaleDateString("en-US", { month: "short", day: "numeric" })
    : "";

  function pickDirect(method, item) {
    setActiveWindow(item);
    if (method === "photo") {
      setTimeout(() => photoInputRef.current?.click(), 60);
    } else if (method === "voice") {
      setPhase("voice");
    } else if (method === "text") {
      setPhase("text");
    }
  }

  function handlePhotoSelected(e) {
    const file = e.target.files?.[0];
    if (!file || !activeWindow) return;
    handleLogged(activeWindow, { method: "photo", file });
    e.target.value = "";
  }

  async function handleLogged(item, result) {
    setDoneSet((prev) => new Set([...prev, item.meal_type]));
    onToast?.("Logged ✓ — nice work");
    setPhase("closed");

    try {
      const form = new FormData();
      form.append("method", result.method);
      if (result.text)                            form.append("text",  result.text);
      if (result.method === "photo" && result.file) form.append("photo", result.file, "meal.jpg");
      if (result.method === "voice" && result.blob) form.append("audio", result.blob, "meal.webm");
      await fetch(
        `${API}/api/athletes/${athleteId}/windows/${item.meal_type}/capture`,
        { method: "POST", body: form }
      );
    } catch (_) {
      // Offline — done state is already set; server will sync on next load
    }
  }

  if (!items.length) {
    return (
      <div style={s.card}>
        <div style={s.header}>
          <div>
            <div style={s.eyebrow}>{dayLabel} · {dateStr}</div>
            <div style={s.title}>Today's Mission</div>
          </div>
        </div>
        <div style={s.empty}>
          <div style={s.emptyIcon}>📋</div>
          <div style={s.emptyText}>Add today's schedule to unlock your fuel mission</div>
        </div>
      </div>
    );
  }

  return (
    <>
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

        {items.map((item, idx) => {
          const isDone   = doneSet.has(item.meal_type) || item.logged;
          const status   = isDone ? "done" : getMissionStatus(item);
          const enriched = { ...item, state: status, tag: TAG_MAP[status] || "UPCOMING", sub: item.macro_focus };
          return (
            <div key={item.meal_type} style={idx === items.length - 1 ? { borderBottom: "none" } : {}}>
              <MissionItem
                item={enriched}
                isDone={isDone}
                cameraAvailable={cameraAvailable}
                onPhoto={() => pickDirect("photo", item)}
                onVoice={() => pickDirect("voice", item)}
                onText={() => pickDirect("text", item)}
              />
            </div>
          );
        })}
      </div>

      {/* Hidden photo file input */}
      <input
        ref={photoInputRef}
        type="file"
        accept="image/*"
        capture="environment"
        style={{ display: "none" }}
        onChange={handlePhotoSelected}
      />

      {phase === "voice" && activeWindow && (
        <VoiceCapture
          window={activeWindow}
          onLogged={(result) => handleLogged(activeWindow, result)}
          onClose={() => setPhase("closed")}
          onPermissionDenied={() => setPhase("closed")}
        />
      )}
      {phase === "text" && activeWindow && (
        <TextCapture
          window={activeWindow}
          onLogged={(result) => handleLogged(activeWindow, result)}
          onClose={() => setPhase("closed")}
        />
      )}
    </>
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
  empty:         { padding: "32px 16px", textAlign: "center" },
  emptyIcon:     { fontSize: "32px", marginBottom: "10px" },
  emptyText:     { fontSize: "16px", color: "#4a6358", lineHeight: 1.5 },
};
