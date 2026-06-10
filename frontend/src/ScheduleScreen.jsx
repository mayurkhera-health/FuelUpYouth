import { useState, useEffect, useCallback, useRef } from "react";

const API = import.meta.env.VITE_API_URL ?? "";

const EVENT_COLORS = {
  game:       { bg: "#c05a4a", text: "#fff" },
  tournament: { bg: "#7e6ab5", text: "#fff" },
  practice:   { bg: "#c8903a", text: "#fff" },
  rest:       { bg: "#2d6a4f", text: "#fff" },
};

const DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const blank = { event_name: "", event_type: "practice", event_date: "", start_time: "", duration_hours: "1.5", city: "" };

// ── ICS Parser ───────────────────────────────────────────────────────────────
function parseICS(text) {
  const events = [];
  const blocks = text.split("BEGIN:VEVENT").slice(1);
  for (const block of blocks) {
    const get = (key) => {
      const match = block.match(new RegExp(`${key}[^:]*:([^\\r\\n]+)`));
      return match ? match[1].trim() : "";
    };
    const dtstart = get("DTSTART");
    if (!dtstart) continue;
    const dateStr = dtstart.replace(/T.*/, "");
    const event_date = `${dateStr.slice(0,4)}-${dateStr.slice(4,6)}-${dateStr.slice(6,8)}`;
    let start_time = "";
    if (dtstart.includes("T")) {
      const t = dtstart.replace(/.*T/, "").replace("Z", "");
      start_time = `${t.slice(0,2)}:${t.slice(2,4)}`;
    }
    const status = get("STATUS").toUpperCase();
    if (status === "CANCELLED") continue;
    const summary = get("SUMMARY") || "Untitled Event";
    if (/^cancelled[:\s]/i.test(summary)) continue;
    const location = get("LOCATION") || "";
    const lower = summary.toLowerCase();
    let event_type = "practice";
    if (lower.includes("game") || lower.includes("match") || lower.includes(" vs ")) event_type = "game";
    else if (lower.includes("tournament") || lower.includes("tourney")) event_type = "tournament";
    else if (lower.includes("rest") || lower.includes("recovery") || lower.includes("off")) event_type = "rest";
    let duration_hours = 1.5;
    const dtend = get("DTEND");
    if (dtend?.includes("T") && dtstart.includes("T")) {
      const sm = parseInt(dtstart.slice(9,11))*60 + parseInt(dtstart.slice(11,13));
      const em = parseInt(dtend.slice(9,11))*60   + parseInt(dtend.slice(11,13));
      const diff = (em - sm + 1440) % 1440;
      if (diff > 0) duration_hours = Math.round((diff/60)*2)/2;
    }
    events.push({ event_name: summary, event_type, event_date, start_time, duration_hours: String(duration_hours), city: location.split(",")[0] || "" });
  }
  return events;
}

// ── Calendar Grid ─────────────────────────────────────────────────────────────
function CalendarGrid({ events, onDeleteEvent, onDayClick, selectedDate }) {
  const today = new Date();
  const [viewYear, setViewYear]   = useState(today.getFullYear());
  const [viewMonth, setViewMonth] = useState(today.getMonth());

  const byDate = events.reduce((acc, ev) => {
    if (!acc[ev.event_date]) acc[ev.event_date] = [];
    acc[ev.event_date].push(ev);
    return acc;
  }, {});

  const firstDay = new Date(viewYear, viewMonth, 1).getDay();
  const daysInMonth = new Date(viewYear, viewMonth + 1, 0).getDate();
  const cells = [];
  for (let i = 0; i < firstDay; i++) cells.push(null);
  for (let d = 1; d <= daysInMonth; d++) cells.push(d);

  const monthLabel = new Date(viewYear, viewMonth).toLocaleDateString("en-US", { month: "long", year: "numeric" });

  function prevMonth() {
    if (viewMonth === 0) { setViewMonth(11); setViewYear(y => y - 1); }
    else setViewMonth(m => m - 1);
  }
  function nextMonth() {
    if (viewMonth === 11) { setViewMonth(0); setViewYear(y => y + 1); }
    else setViewMonth(m => m + 1);
  }

  const todayStr = `${today.getFullYear()}-${String(today.getMonth()+1).padStart(2,"0")}-${String(today.getDate()).padStart(2,"0")}`;

  return (
    <div>
      {/* Month nav */}
      <div style={c.nav}>
        <button style={c.navBtn} onClick={prevMonth}>‹</button>
        <span style={c.monthTitle}>{monthLabel}</span>
        <button style={c.navBtn} onClick={nextMonth}>›</button>
      </div>

      {/* Day headers */}
      <div style={c.grid}>
        {DAYS.map(d => <div key={d} style={c.dayHeader}>{d}</div>)}

        {/* Cells */}
        {cells.map((day, i) => {
          if (!day) return <div key={`e-${i}`} />;
          const dateStr = `${viewYear}-${String(viewMonth+1).padStart(2,"0")}-${String(day).padStart(2,"0")}`;
          const dayEvents = byDate[dateStr] || [];
          const isToday = dateStr === todayStr;
          const isSelected = dateStr === selectedDate;
          return (
            <div
              key={dateStr}
              style={{ ...c.cell, ...(isToday ? c.cellToday : {}), ...(isSelected ? c.cellSelected : {}) }}
              onClick={() => onDayClick(dateStr)}
            >
              <div style={{ ...c.dayNum, ...(isToday ? c.dayNumToday : {}) }}>{day}</div>
              <div style={c.eventPills}>
                {dayEvents.slice(0, 3).map((ev, j) => {
                  const col = EVENT_COLORS[ev.event_type] || EVENT_COLORS.practice;
                  return (
                    <div key={j} style={{ ...c.pill, background: col.bg, color: col.text }}>
                      {ev.event_name.length > 12 ? ev.event_name.slice(0, 11) + "…" : ev.event_name}
                    </div>
                  );
                })}
                {dayEvents.length > 3 && <div style={c.more}>+{dayEvents.length - 3}</div>}
              </div>
            </div>
          );
        })}
      </div>

      {/* Legend */}
      <div style={c.legend}>
        {Object.entries(EVENT_COLORS).map(([type, col]) => (
          <div key={type} style={c.legendItem}>
            <div style={{ ...c.legendDot, background: col.bg }} />
            <span style={c.legendLabel}>{type}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

const c = {
  nav: { display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "12px" },
  navBtn: { background: "none", border: "1.5px solid #e5e7eb", borderRadius: "8px", width: "32px", height: "32px", fontSize: "18px", cursor: "pointer", color: "#4a6358", display: "flex", alignItems: "center", justifyContent: "center" },
  monthTitle: { fontSize: "16px", fontWeight: "700", color: "#1b3a2a" },
  grid: { display: "grid", gridTemplateColumns: "repeat(7, 1fr)", gap: "2px", marginBottom: "12px" },
  dayHeader: { textAlign: "center", fontSize: "11px", fontWeight: "700", color: "#8aa898", paddingBottom: "8px", textTransform: "uppercase" },
  cell: { minHeight: "72px", borderRadius: "8px", padding: "4px", cursor: "pointer", border: "1.5px solid transparent", background: "#f4f8f5" },
  cellToday: { background: "#f0fdf4", border: "1.5px solid #bbf7d0" },
  cellSelected: { border: "1.5px solid #0f4c35" },
  dayNum: { fontSize: "12px", fontWeight: "600", color: "#8aa898", marginBottom: "3px", textAlign: "right", paddingRight: "2px" },
  dayNumToday: { color: "#2d6a4f", fontWeight: "800" },
  eventPills: { display: "flex", flexDirection: "column", gap: "2px" },
  pill: { fontSize: "10px", fontWeight: "600", padding: "1px 4px", borderRadius: "4px", lineHeight: "1.4", overflow: "hidden", whiteSpace: "nowrap" },
  more: { fontSize: "10px", color: "#8aa898", fontWeight: "600", paddingLeft: "4px" },
  legend: { display: "flex", gap: "12px", flexWrap: "wrap", marginTop: "4px" },
  legendItem: { display: "flex", alignItems: "center", gap: "5px" },
  legendDot: { width: "10px", height: "10px", borderRadius: "3px" },
  legendLabel: { fontSize: "11px", color: "#8aa898", textTransform: "capitalize" },
};

// ── Day detail panel ──────────────────────────────────────────────────────────
function DayPanel({ date, events, onDelete, onClose }) {
  const label = new Date(date + "T12:00:00").toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" });
  const dayEvents = events.filter(ev => ev.event_date === date);
  return (
    <div style={dp.wrap}>
      <div style={dp.header}>
        <span style={dp.label}>{label}</span>
        <button style={dp.close} onClick={onClose}>✕</button>
      </div>
      {dayEvents.length === 0
        ? <p style={dp.empty}>No events on this day.</p>
        : dayEvents.map(ev => {
            const col = EVENT_COLORS[ev.event_type] || EVENT_COLORS.practice;
            return (
              <div key={ev.id} style={dp.row}>
                <div style={{ ...dp.typeBadge, background: col.bg, color: col.text }}>{ev.event_type}</div>
                <div style={dp.body}>
                  <div style={dp.name}>{ev.event_name}</div>
                  <div style={dp.meta}>
                    {ev.start_time && `${ev.start_time} · `}{ev.duration_hours && `${ev.duration_hours}h`}{ev.city && ` · ${ev.city}`}
                  </div>
                </div>
                <button style={dp.del} onClick={() => onDelete(ev.id)}>✕</button>
              </div>
            );
          })
      }
    </div>
  );
}
const dp = {
  wrap: { background: "#fff", border: "1.5px solid #e5e7eb", borderRadius: "12px", padding: "14px 16px", marginTop: "16px" },
  header: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" },
  label: { fontSize: "14px", fontWeight: "700", color: "#1b3a2a" },
  close: { background: "none", border: "none", color: "#8aa898", cursor: "pointer", fontSize: "16px" },
  empty: { fontSize: "13px", color: "#8aa898", textAlign: "center", padding: "12px 0" },
  row: { display: "flex", alignItems: "center", gap: "10px", padding: "10px 0", borderTop: "1px solid #f3f4f6" },
  typeBadge: { fontSize: "10px", fontWeight: "700", padding: "2px 8px", borderRadius: "99px", textTransform: "uppercase", whiteSpace: "nowrap" },
  body: { flex: 1 },
  name: { fontSize: "14px", fontWeight: "600", color: "#1b3a2a" },
  meta: { fontSize: "12px", color: "#8aa898", marginTop: "2px" },
  del: { background: "none", border: "none", color: "#8aa898", cursor: "pointer", fontSize: "14px" },
};

// ── Main screen ───────────────────────────────────────────────────────────────
export default function ScheduleScreen({ athlete, onScheduleImported }) {
  const [events, setEvents]       = useState([]);
  const [loading, setLoading]     = useState(true);
  const [mode, setMode]           = useState(null);
  const [selectedDate, setSelectedDate] = useState(null);

  // Manual form
  const [form, setForm]           = useState(blank);
  const [saving, setSaving]       = useState(false);
  const [formError, setFormError] = useState("");

  // Upload
  const fileRef                   = useRef();
  const [icsText, setIcsText]     = useState("");
  const [dragOver, setDragOver]   = useState(false);
  const [parsed, setParsed]       = useState([]);
  const [parseError, setParseError] = useState("");
  const [fetching, setFetching]   = useState(false);
  const [importing, setImporting] = useState(false);
  const [importDone, setImportDone] = useState(false);
  const [typeOverrides, setTypeOverrides] = useState({});

  const fetchEvents = useCallback(async () => {
    setLoading(true);
    const res = await fetch(`${API}/api/events/athlete/${athlete.id}`);
    setEvents(res.ok ? await res.json() : []);
    setLoading(false);
  }, [athlete.id]);

  useEffect(() => { fetchEvents(); }, [fetchEvents]);

  async function handleAdd(e) {
    e.preventDefault();
    if (!form.event_name.trim() || !form.event_date) return setFormError("Name and date are required.");
    setSaving(true); setFormError("");
    const res = await fetch(`${API}/api/events/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...form, athlete_id: athlete.id, duration_hours: parseFloat(form.duration_hours) || 1.5 }),
    });
    if (!res.ok) { setFormError("Failed to save event."); setSaving(false); return; }
    setForm(blank); setMode(null);
    await fetchEvents();
    setSaving(false);
  }

  async function handleDeleteEvent(id) {
    await fetch(`${API}/api/events/${id}`, { method: "DELETE" });
    await fetchEvents();
  }

  function handleFile(file) {
    if (!file) return;
    if (!file.name.endsWith(".ics")) { setParseError("Please select a .ics file."); return; }
    setParseError(""); setParsed([]); setImportDone(false);
    const reader = new FileReader();
    reader.onload = (ev) => {
      const evts = parseICS(ev.target.result);
      if (!evts.length) { setParseError("No events found in this file."); return; }
      setParsed(evts); setTypeOverrides({});
    };
    reader.readAsText(file);
  }

  function handleDrop(e) {
    e.preventDefault(); setDragOver(false);
    handleFile(e.dataTransfer.files[0]);
  }

  async function handleParse() {
    setParseError(""); setParsed([]); setImportDone(false);
    const text = icsText.trim();
    if (!text) { setParseError("Please paste a calendar URL."); return; }
    let icsContent = text;
    if (text.startsWith("http")) {
      setFetching(true);
      try {
        const res = await fetch(`${API}/api/events/fetch-ics?url=${encodeURIComponent(text)}`);
        if (!res.ok) { const d = await res.json().catch(()=>{}); setParseError(d?.detail || "Could not fetch calendar."); return; }
        icsContent = (await res.json()).content;
      } catch { setParseError("Network error. Please try again."); return; }
      finally { setFetching(false); }
    }
    if (!icsContent.includes("BEGIN:VEVENT")) { setParseError("No valid calendar events found."); return; }
    const evts = parseICS(icsContent);
    if (!evts.length) { setParseError("No events found."); return; }
    setParsed(evts); setTypeOverrides({});
  }

  async function handleImport() {
    setImporting(true);
    const toImport = parsed.map((ev, i) => ({ ...ev, event_type: typeOverrides[i] || ev.event_type }));
    await Promise.all(toImport.map(ev =>
      fetch(`${API}/api/events/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...ev, athlete_id: athlete.id, duration_hours: parseFloat(ev.duration_hours) || 1.5 }),
      })
    ));
    setParsed([]); setIcsText(""); setImportDone(true); setMode(null);
    await fetchEvents();
    setImporting(false);
    onScheduleImported?.();
  }

  return (
    <div>
      <div style={s.headerRow}>
        <h2 style={s.title}>Training Schedule</h2>
        {mode
          ? <button style={s.cancelBtn} onClick={() => { setMode(null); setParsed([]); setParseError(""); setIcsText(""); }}>✕ Cancel</button>
          : <div style={s.addBtns}>
              <button style={s.addBtn} onClick={() => setMode("manual")}>✏️ Add Event</button>
              <button style={s.addBtn} onClick={() => setMode("upload")}>📲 Sync Calendar</button>
            </div>
        }
      </div>

      {importDone && <div style={s.importSuccess}>✅ Schedule imported successfully!</div>}

      {/* Manual form */}
      {mode === "manual" && (
        <form onSubmit={handleAdd} style={s.form}>
          <div style={s.formTitle}>Add Event</div>
          <div style={s.row2}>
            <div style={s.field}>
              <label style={s.label}>Event Name</label>
              <input style={s.input} placeholder="e.g. ECNL Game vs FC Dallas" value={form.event_name} onChange={e => setForm(f => ({ ...f, event_name: e.target.value }))} />
            </div>
            <div style={s.field}>
              <label style={s.label}>Type</label>
              <select style={s.input} value={form.event_type} onChange={e => setForm(f => ({ ...f, event_type: e.target.value }))}>
                <option value="practice">Practice</option>
                <option value="game">Game</option>
                <option value="tournament">Tournament</option>
                <option value="rest">Rest</option>
              </select>
            </div>
          </div>
          <div style={s.row3}>
            <div style={s.field}>
              <label style={s.label}>Date</label>
              <input style={s.input} type="date" value={form.event_date} onChange={e => setForm(f => ({ ...f, event_date: e.target.value }))} />
            </div>
            <div style={s.field}>
              <label style={s.label}>Start Time</label>
              <input style={s.input} type="time" value={form.start_time} onChange={e => setForm(f => ({ ...f, start_time: e.target.value }))} />
            </div>
            <div style={s.field}>
              <label style={s.label}>Duration (hrs)</label>
              <input style={s.input} type="number" step="0.5" value={form.duration_hours} onChange={e => setForm(f => ({ ...f, duration_hours: e.target.value }))} />
            </div>
          </div>
          <div style={s.field}>
            <label style={s.label}>City (for hydration calculator)</label>
            <input style={s.input} placeholder="e.g. Dallas, TX" value={form.city} onChange={e => setForm(f => ({ ...f, city: e.target.value }))} />
          </div>
          {formError && <p style={s.error}>{formError}</p>}
          <button style={s.saveBtn} type="submit" disabled={saving}>{saving ? "Saving…" : "Save Event"}</button>
        </form>
      )}

      {/* Sync calendar */}
      {mode === "upload" && (
        <div style={s.uploadBox}>
          <div style={s.formTitle}>Sync Calendar</div>
          <div style={s.appLogos}>
            {["PlayMetrics", "TeamSnap", "Google Calendar", "Apple Calendar", "Any .ics"].map(a => (
              <span key={a} style={s.appChip}>{a}</span>
            ))}
          </div>
          <p style={s.uploadInstructions}>Paste your calendar URL and click Sync, or drop a .ics file below.</p>

          <div style={s.urlRow}>
            <input
              style={s.urlInput}
              placeholder="https://calendar.playmetrics.com/calendars/…/calendar.ics"
              value={icsText}
              onChange={e => { setIcsText(e.target.value); setParsed([]); setParseError(""); }}
              spellCheck={false}
            />
            <button style={s.parseBtn} onClick={handleParse} disabled={!icsText.trim() || fetching}>
              {fetching ? "Fetching…" : "Sync →"}
            </button>
          </div>

          <div
            style={{ ...s.dropZone, ...(dragOver ? s.dropZoneActive : {}) }}
            onDragOver={e => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            onClick={() => fileRef.current.click()}
          >
            <input ref={fileRef} type="file" accept=".ics" style={{ display: "none" }} onChange={e => handleFile(e.target.files[0])} />
            <div style={s.dropText}>📁 Drop .ics file here or click to browse</div>
          </div>

          {parseError && <p style={s.error}>{parseError}</p>}

          {parsed.length > 0 && (
            <div style={s.preview}>
              <div style={s.previewTitle}>{parsed.length} event{parsed.length !== 1 ? "s" : ""} found — review types before importing</div>
              <div style={s.previewNote}>Adjust the type if auto-detected incorrectly.</div>
              {parsed.map((ev, i) => {
                const type = typeOverrides[i] || ev.event_type;
                const col = EVENT_COLORS[type] || EVENT_COLORS.practice;
                return (
                  <div key={i} style={s.previewRow}>
                    <div style={{ ...s.previewDot, background: col.bg }} />
                    <div style={s.previewBody}>
                      <div style={s.previewName}>{ev.event_name}</div>
                      <div style={s.previewMeta}>{ev.event_date}{ev.start_time ? ` · ${ev.start_time}` : ""}{ev.city ? ` · ${ev.city}` : ""}</div>
                    </div>
                    <select style={s.typeSelect} value={type} onChange={e => setTypeOverrides(o => ({ ...o, [i]: e.target.value }))}>
                      <option value="practice">Practice</option>
                      <option value="game">Game</option>
                      <option value="tournament">Tournament</option>
                      <option value="rest">Rest</option>
                    </select>
                  </div>
                );
              })}
              <button style={s.importBtn} onClick={handleImport} disabled={importing}>
                {importing ? `Importing…` : `Import ${parsed.length} Events →`}
              </button>
            </div>
          )}
        </div>
      )}

      {/* Calendar */}
      {!mode && (
        loading
          ? <p style={s.empty}>Loading schedule…</p>
          : events.length === 0
            ? <div style={s.emptyState}>
                <div style={s.emptyIcon}>📅</div>
                <p style={s.emptyText}>No events yet. Add your first game or practice to unlock personalized nutrition targets.</p>
              </div>
            : <>
                <CalendarGrid
                  events={events}
                  selectedDate={selectedDate}
                  onDayClick={d => setSelectedDate(prev => prev === d ? null : d)}
                  onDeleteEvent={handleDeleteEvent}
                />
                {selectedDate && (
                  <DayPanel
                    date={selectedDate}
                    events={events}
                    onDelete={async (id) => { await handleDeleteEvent(id); }}
                    onClose={() => setSelectedDate(null)}
                  />
                )}
              </>
      )}
    </div>
  );
}

const s = {
  headerRow: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" },
  title: { fontSize: "18px", fontWeight: "700", color: "#1b3a2a", margin: 0 },
  addBtns: { display: "flex", gap: "8px" },
  addBtn: { background: "linear-gradient(135deg, #2d6a4f, #52b788)", color: "#fff", border: "none", borderRadius: "8px", padding: "7px 14px", fontSize: "13px", fontWeight: "600", cursor: "pointer" },
  cancelBtn: { background: "none", border: "1.5px solid #d1d5db", color: "#8aa898", borderRadius: "8px", padding: "6px 14px", fontSize: "13px", fontWeight: "600", cursor: "pointer" },
  importSuccess: { background: "#f0fdf4", border: "1.5px solid #bbf7d0", borderRadius: "10px", padding: "12px 16px", fontSize: "14px", fontWeight: "600", color: "#2d6a4f", marginBottom: "16px" },

  form: { background: "#f4f8f5", border: "1.5px solid #e5e7eb", borderRadius: "12px", padding: "20px", marginBottom: "24px" },
  formTitle: { fontSize: "15px", fontWeight: "700", color: "#1b3a2a", marginBottom: "16px" },
  row2: { display: "flex", gap: "12px", marginBottom: "12px" },
  row3: { display: "flex", gap: "12px", marginBottom: "12px" },
  field: { flex: 1 },
  label: { display: "block", fontSize: "12px", fontWeight: "600", color: "#8aa898", marginBottom: "4px" },
  input: { width: "100%", padding: "8px 10px", border: "1.5px solid #d1d5db", borderRadius: "8px", fontSize: "14px", boxSizing: "border-box", outline: "none", background: "#fff" },
  saveBtn: { width: "100%", padding: "10px", background: "linear-gradient(135deg, #2d6a4f, #52b788)", color: "#fff", border: "none", borderRadius: "8px", fontSize: "14px", fontWeight: "700", cursor: "pointer", marginTop: "4px" },
  error: { color: "#dc2626", fontSize: "13px", margin: "8px 0" },

  uploadBox: { background: "#f4f8f5", border: "1.5px solid #e5e7eb", borderRadius: "12px", padding: "20px", marginBottom: "24px" },
  appLogos: { display: "flex", flexWrap: "wrap", gap: "6px", marginBottom: "12px" },
  appChip: { fontSize: "11px", fontWeight: "600", padding: "3px 10px", background: "#e0f2fe", color: "#0369a1", borderRadius: "99px" },
  uploadInstructions: { fontSize: "13px", color: "#4a6358", marginBottom: "12px" },
  urlRow: { display: "flex", gap: "8px", marginBottom: "10px" },
  urlInput: { flex: 1, padding: "9px 12px", border: "1.5px solid #d1d5db", borderRadius: "8px", fontSize: "13px", outline: "none", fontFamily: "monospace" },
  parseBtn: { padding: "9px 16px", background: "linear-gradient(135deg, #2d6a4f, #52b788)", color: "#fff", border: "none", borderRadius: "8px", fontSize: "13px", fontWeight: "700", cursor: "pointer", whiteSpace: "nowrap" },
  dropZone: { border: "2px dashed #d1d5db", borderRadius: "10px", padding: "14px", textAlign: "center", cursor: "pointer", background: "#fff", marginBottom: "12px" },
  dropZoneActive: { borderColor: "#2d6a4f", background: "#f0fdf4" },
  dropText: { fontSize: "13px", color: "#8aa898", fontWeight: "600" },

  preview: { background: "#fff", border: "1.5px solid #e5e7eb", borderRadius: "10px", padding: "14px", marginTop: "12px" },
  previewTitle: { fontSize: "14px", fontWeight: "700", color: "#1b3a2a", marginBottom: "4px" },
  previewNote: { fontSize: "12px", color: "#8aa898", marginBottom: "10px" },
  previewRow: { display: "flex", alignItems: "center", gap: "10px", padding: "8px 0", borderTop: "1px solid #f3f4f6" },
  previewDot: { width: "10px", height: "10px", borderRadius: "50%", flexShrink: 0 },
  previewBody: { flex: 1 },
  previewName: { fontSize: "13px", fontWeight: "700", color: "#1b3a2a" },
  previewMeta: { fontSize: "11px", color: "#8aa898", marginTop: "2px" },
  typeSelect: { padding: "4px 8px", border: "1.5px solid #d1d5db", borderRadius: "6px", fontSize: "12px", outline: "none", background: "#fff" },
  importBtn: { width: "100%", padding: "10px", background: "linear-gradient(135deg, #2d6a4f, #52b788)", color: "#fff", border: "none", borderRadius: "8px", fontSize: "14px", fontWeight: "700", cursor: "pointer", marginTop: "12px" },

  emptyState: { textAlign: "center", padding: "48px 20px" },
  emptyIcon: { fontSize: "40px", marginBottom: "12px" },
  emptyText: { fontSize: "14px", color: "#8aa898", maxWidth: "320px", margin: "0 auto" },
  empty: { textAlign: "center", color: "#8aa898", padding: "40px 0" },
};
