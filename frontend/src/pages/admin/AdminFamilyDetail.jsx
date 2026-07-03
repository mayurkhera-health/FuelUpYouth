import { useEffect, useState } from "react";
import { adminFetch, AuthError } from "./adminApi";
import { C, FONT_DISPLAY } from "./theme";
import { Card, Button, TextInput, CalendarBadge, Skeleton, ErrorRetry } from "./ui";

const label = { font: `600 12px ${FONT_DISPLAY}`, color: C.text3, textTransform: "uppercase", letterSpacing: "0.03em" };
const val = { font: `600 15px ${FONT_DISPLAY}`, color: C.text1 };

export default function AdminFamilyDetail({ parentId, onBack, onLoggedOut }) {
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [deleteTarget, setDeleteTarget] = useState(null); // {type,id,name,counts}

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [parentId]);

  async function load() {
    setLoading(true); setError("");
    try {
      setDetail(await adminFetch(`/users/${parentId}`));
    } catch (err) {
      if (err instanceof AuthError) return onLoggedOut();
      setError(err.message);
    } finally { setLoading(false); }
  }

  async function guarded(fn) {
    try { return await fn(); }
    catch (err) {
      if (err instanceof AuthError) return onLoggedOut();
      throw err;
    }
  }

  if (loading) return <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
    <Skeleton height={28} width={180} /><Skeleton height={120} /><Skeleton height={160} />
  </div>;
  if (error) return <ErrorRetry message={error} onRetry={load} />;
  if (!detail) return null;

  const { parent, athletes, activity } = detail;

  return (
    <div>
      <button onClick={onBack} style={{
        font: `600 13px ${FONT_DISPLAY}`, color: C.brand, background: "transparent",
        border: "none", cursor: "pointer", padding: 0, marginBottom: 14,
      }}>← Back to Users</button>

      <ParentSection parent={parent} guarded={guarded} onSaved={load}
        onDelete={() => openDelete("parent", parent.id, parent.full_name, guarded, setDeleteTarget)} />

      <h2 style={{ font: `800 18px ${FONT_DISPLAY}`, color: C.text1, margin: "26px 0 12px" }}>
        Athletes ({athletes.length})
      </h2>
      {athletes.length === 0 && <Card><span style={{ color: C.text3 }}>No athletes on this account.</span></Card>}
      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        {athletes.map((a) => (
          <AthleteCard key={a.id} athlete={a} guarded={guarded} onSaved={load}
            onDelete={() => openDelete("athlete", a.id, a.first_name, guarded, setDeleteTarget)} />
        ))}
      </div>

      <ActivitySection activity={activity} />

      {deleteTarget && (
        <DeleteModal target={deleteTarget} guarded={guarded}
          onClose={() => setDeleteTarget(null)}
          onDone={() => { setDeleteTarget(null); deleteTarget.type === "parent" ? onBack() : load(); }} />
      )}
    </div>
  );
}

async function openDelete(type, id, name, guarded, setDeleteTarget) {
  const path = type === "parent" ? `/parents/${id}/delete-preview` : `/athletes/${id}/delete-preview`;
  try {
    const preview = await guarded(() => adminFetch(path));
    setDeleteTarget({ type, id, name, counts: preview.counts || {} });
  } catch (err) {
    alert(err.message);
  }
}

function ParentSection({ parent, guarded, onSaved, onDelete }) {
  const [editing, setEditing] = useState(false);
  const [fullName, setFullName] = useState(parent.full_name);
  const [email, setEmail] = useState(parent.email);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  async function save() {
    setBusy(true); setErr("");
    try {
      await guarded(() => adminFetch(`/parents/${parent.id}`, {
        method: "PUT", body: JSON.stringify({ full_name: fullName, email }),
      }));
      setEditing(false); onSaved();
    } catch (e) { setErr(e.message); } finally { setBusy(false); }
  }

  return (
    <Card>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div style={{ font: `800 20px ${FONT_DISPLAY}`, color: C.text1 }}>Parent</div>
        {!editing && <Button variant="ghost" onClick={() => setEditing(true)}>Edit</Button>}
      </div>
      {!editing ? (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(180px,1fr))", gap: 14, marginTop: 12 }}>
          <div><div style={label}>Name</div><div style={val}>{parent.full_name}</div></div>
          <div><div style={label}>Email</div><div style={val}>{parent.email}</div></div>
          <div><div style={label}>Joined</div><div style={val}>{(parent.created_at || "").slice(0, 10)}</div></div>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 10, marginTop: 12, maxWidth: 420 }}>
          <div><div style={label}>Name</div><TextInput value={fullName} onChange={(e) => setFullName(e.target.value)} /></div>
          <div><div style={label}>Email</div><TextInput value={email} onChange={(e) => setEmail(e.target.value)} /></div>
          {err && <div style={{ color: C.danger, font: `500 13px ${FONT_DISPLAY}` }}>{err}</div>}
          <div style={{ display: "flex", gap: 8 }}>
            <Button onClick={save} disabled={busy}>{busy ? "Saving…" : "Save"}</Button>
            <Button variant="ghost" onClick={() => { setEditing(false); setFullName(parent.full_name); setEmail(parent.email); setErr(""); }}>Cancel</Button>
          </div>
        </div>
      )}
      <div style={{ marginTop: 18, paddingTop: 14, borderTop: `1px solid ${C.border}` }}>
        <Button variant="danger" onClick={onDelete}>Delete family…</Button>
      </div>
    </Card>
  );
}

const ATHLETE_FIELDS = [
  ["first_name", "Name", "text"], ["age", "Age", "number"], ["gender", "Gender", "text"],
  ["position", "Position", "text"], ["competition_level", "Level", "text"],
  ["weight_lbs", "Weight (lbs)", "number"],
];

function AthleteCard({ athlete, guarded, onSaved, onDelete }) {
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState(athlete);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [showUrls, setShowUrls] = useState(false);
  const stats = athlete.event_stats || { total: 0, upcoming: 0, by_source: {} };

  async function save() {
    setBusy(true); setErr("");
    try {
      const body = {};
      ATHLETE_FIELDS.forEach(([k, , t]) => {
        let v = form[k];
        if (t === "number" && v !== null && v !== "" && v !== undefined) v = Number(v);
        body[k] = v;
      });
      await guarded(() => adminFetch(`/athletes/${athlete.id}`, { method: "PUT", body: JSON.stringify(body) }));
      setEditing(false); onSaved();
    } catch (e) { setErr(e.message); } finally { setBusy(false); }
  }

  return (
    <Card>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12, flexWrap: "wrap" }}>
        <div style={{ font: `800 17px ${FONT_DISPLAY}`, color: C.text1 }}>
          {athlete.first_name}
          <span style={{ font: `500 13px ${FONT_DISPLAY}`, color: C.text3, marginLeft: 8 }}>
            {athlete.position || "—"}{athlete.age ? ` · ${athlete.age}y` : ""}
          </span>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <CalendarBadge kind={athlete.byga_ics_url ? "byga" : athlete.playmetrics_ics_url ? "playmetrics" : "none"} />
        </div>
      </div>

      {!editing ? (
        <>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(140px,1fr))", gap: 12, marginTop: 12 }}>
            <div><div style={label}>Total events</div><div style={val}>{stats.total}</div></div>
            <div><div style={label}>Upcoming</div><div style={val}>{stats.upcoming}</div></div>
            <div><div style={label}>By source</div><div style={{ ...val, fontSize: 13 }}>
              {Object.entries(stats.by_source).map(([k, v]) => `${k}:${v}`).join("  ") || "—"}</div></div>
            <div><div style={label}>Last synced</div><div style={{ ...val, fontSize: 13 }}>
              {athlete.last_synced_at ? athlete.last_synced_at.slice(0, 16).replace("T", " ") : "—"}</div></div>
          </div>
          {(athlete.byga_ics_url || athlete.playmetrics_ics_url) && (
            <div style={{ marginTop: 10 }}>
              <button onClick={() => setShowUrls((s) => !s)} style={{
                font: `600 12px ${FONT_DISPLAY}`, color: C.brand, background: "transparent",
                border: "none", cursor: "pointer", padding: 0,
              }}>{showUrls ? "Hide" : "View"} sync URLs</button>
              {showUrls && (
                <div style={{ marginTop: 6, font: `400 12px ${FONT_DISPLAY}`, color: C.text2, wordBreak: "break-all" }}>
                  {athlete.byga_ics_url && <div>BYGA: {athlete.byga_ics_url}</div>}
                  {athlete.playmetrics_ics_url && <div>PlayMetrics: {athlete.playmetrics_ics_url}</div>}
                </div>
              )}
            </div>
          )}
          <div style={{ display: "flex", gap: 8, marginTop: 14 }}>
            <Button variant="ghost" onClick={() => { setForm(athlete); setEditing(true); }}>Edit</Button>
            <Button variant="danger" onClick={onDelete}>Delete athlete…</Button>
          </div>
        </>
      ) : (
        <div style={{ marginTop: 12 }}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(150px,1fr))", gap: 10 }}>
            {ATHLETE_FIELDS.map(([k, lbl, t]) => (
              <div key={k}>
                <div style={label}>{lbl}</div>
                <TextInput type={t} value={form[k] ?? ""} onChange={(e) => setForm((f) => ({ ...f, [k]: e.target.value }))} />
              </div>
            ))}
          </div>
          {err && <div style={{ color: C.danger, font: `500 13px ${FONT_DISPLAY}`, marginTop: 8 }}>{err}</div>}
          <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
            <Button onClick={save} disabled={busy}>{busy ? "Saving…" : "Save"}</Button>
            <Button variant="ghost" onClick={() => { setEditing(false); setErr(""); }}>Cancel</Button>
          </div>
        </div>
      )}
    </Card>
  );
}

function ActivitySection({ activity }) {
  const ideas = activity.feature_ideas || [];
  const upcoming = activity.upcoming_events || [];
  return (
    <>
      <h2 style={{ font: `800 18px ${FONT_DISPLAY}`, color: C.text1, margin: "26px 0 12px" }}>Activity</h2>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(280px,1fr))", gap: 14 }}>
        <Card>
          <div style={{ font: `700 14px ${FONT_DISPLAY}`, color: C.text2, marginBottom: 10 }}>Upcoming events</div>
          {upcoming.length === 0 ? <span style={{ color: C.text3, fontSize: 13 }}>None scheduled.</span> : (
            upcoming.map((e) => (
              <div key={e.id} style={{ font: `500 13px ${FONT_DISPLAY}`, color: C.text1, padding: "4px 0", borderBottom: `1px solid ${C.border}` }}>
                {e.event_date} · {e.event_name || e.event_type} <span style={{ color: C.text3 }}>({e.source || "manual"})</span>
              </div>
            ))
          )}
        </Card>
        <Card>
          <div style={{ font: `700 14px ${FONT_DISPLAY}`, color: C.text2, marginBottom: 10 }}>Feature ideas submitted</div>
          {ideas.length === 0 ? <span style={{ color: C.text3, fontSize: 13 }}>None.</span> : (
            ideas.map((f) => (
              <div key={f.id} style={{ font: `500 13px ${FONT_DISPLAY}`, color: C.text1, padding: "6px 0", borderBottom: `1px solid ${C.border}` }}>
                {f.suggestion}
                <div style={{ color: C.text3, fontSize: 12 }}>{(f.submitted_at || "").slice(0, 10)}</div>
              </div>
            ))
          )}
        </Card>
      </div>
    </>
  );
}

function DeleteModal({ target, guarded, onClose, onDone }) {
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const isParent = target.type === "parent";
  const entries = Object.entries(target.counts).filter(([, v]) => v > 0);

  async function doDelete() {
    setBusy(true); setErr("");
    try {
      const path = isParent ? `/parents/${target.id}` : `/athletes/${target.id}`;
      await guarded(() => adminFetch(path, {
        method: "DELETE",
        body: isParent ? JSON.stringify({ confirm }) : undefined,
      }));
      onDone();
    } catch (e) { setErr(e.message); setBusy(false); }
  }

  return (
    <div style={{
      position: "fixed", inset: 0, background: "rgba(27,58,42,0.4)", display: "flex",
      alignItems: "center", justifyContent: "center", padding: 20, zIndex: 50,
    }} onClick={onClose}>
      <div onClick={(e) => e.stopPropagation()} style={{
        background: C.surface, borderRadius: 16, padding: 26, width: 440, maxWidth: "100%", boxShadow: C.shadowMd,
      }}>
        <div style={{ font: `800 19px ${FONT_DISPLAY}`, color: C.danger }}>
          Delete {isParent ? "family" : "athlete"}: {target.name}
        </div>
        <div style={{ font: `500 14px ${FONT_DISPLAY}`, color: C.text2, marginTop: 10 }}>
          This permanently deletes:
        </div>
        <div style={{ background: C.dangerBg, border: `1px solid ${C.dangerBorder}`, borderRadius: 10, padding: "10px 14px", marginTop: 8 }}>
          {entries.length === 0
            ? <span style={{ font: `500 13px ${FONT_DISPLAY}`, color: C.text2 }}>Just the {isParent ? "parent" : "athlete"} record (no related data).</span>
            : <ul style={{ margin: 0, paddingLeft: 18, font: `500 13px ${FONT_DISPLAY}`, color: C.text1 }}>
                {entries.map(([k, v]) => <li key={k}>{v} {k.replace(/_/g, " ").replace(":", " · ")}</li>)}
              </ul>}
        </div>
        {isParent && (
          <div style={{ marginTop: 14 }}>
            <div style={{ font: `500 13px ${FONT_DISPLAY}`, color: C.text2, marginBottom: 6 }}>
              Type <b>DELETE</b> to confirm:
            </div>
            <TextInput value={confirm} onChange={(e) => setConfirm(e.target.value)} placeholder="DELETE" />
          </div>
        )}
        {err && <div style={{ color: C.danger, font: `500 13px ${FONT_DISPLAY}`, marginTop: 10 }}>{err}</div>}
        <div style={{ display: "flex", gap: 8, marginTop: 18, justifyContent: "flex-end" }}>
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button variant="danger" disabled={busy || (isParent && confirm !== "DELETE")} onClick={doDelete}>
            {busy ? "Deleting…" : "Delete permanently"}
          </Button>
        </div>
      </div>
    </div>
  );
}
