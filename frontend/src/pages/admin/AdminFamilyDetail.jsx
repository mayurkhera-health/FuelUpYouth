import { useEffect, useState } from "react";
import { adminFetch, AuthError } from "./adminApi";
import { C, FONT_DISPLAY } from "./theme";
import { Card, Button, TextInput, CalendarBadge, Avatar, Skeleton, ErrorRetry } from "./ui";

const label = { font: `600 12px ${FONT_DISPLAY}`, color: C.text3, textTransform: "uppercase", letterSpacing: "0.03em" };
const val = { font: `600 15px ${FONT_DISPLAY}`, color: C.text1 };

const NONE_VALUES = new Set(["", "none", "n/a", "na", "no", "not specified"]);
const isSet = (v) => v != null && !NONE_VALUES.has(String(v).trim().toLowerCase());
const dash = (v) => (isSet(v) ? v : "—");

function parseUtc(iso) {
  if (!iso) return null;
  let s = String(iso).replace(" ", "T");
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
function heightStr(a) {
  if (a.height_ft == null && a.height_in == null) return "—";
  return `${a.height_ft ?? 0}' ${Math.round(a.height_in ?? 0)}"`;
}

// Nutrition-safety values get an amber highlight when set — these are exactly
// the fields worth a second look before answering a support email.
function SafetyVal({ children }) {
  const set = isSet(children);
  if (!set) return <div style={{ ...val, fontSize: 13 }}>—</div>;
  return (
    <div style={{
      display: "inline-block", font: `700 13px ${FONT_DISPLAY}`, color: "#92400e",
      background: C.warmLight, border: "1px solid #fde68a", borderRadius: 8, padding: "2px 8px",
    }}>{children}</div>
  );
}

export default function AdminFamilyDetail({ parentId, onBack, onLoggedOut, hideBack }) {
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
      {!hideBack && (
        <button onClick={onBack} style={{
          font: `600 13px ${FONT_DISPLAY}`, color: C.brand, background: "transparent",
          border: "none", cursor: "pointer", padding: 0, marginBottom: 14,
        }}>← Back to Users</button>
      )}

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
      {!editing ? (
        <div style={{ display: "flex", gap: 16, alignItems: "center", justifyContent: "space-between", flexWrap: "wrap" }}>
          <div style={{ display: "flex", gap: 16, alignItems: "center", minWidth: 0 }}>
            <Avatar name={parent.full_name} size={56} />
            <div style={{ minWidth: 0 }}>
              <div style={{ font: `800 22px ${FONT_DISPLAY}`, color: C.text1 }}>{parent.full_name}</div>
              <div style={{ font: `400 14px ${FONT_DISPLAY}`, color: C.text3 }}>{parent.email}</div>
              <div style={{ font: `500 12px ${FONT_DISPLAY}`, color: C.text3, marginTop: 2 }}>
                Joined {(parent.created_at || "").slice(0, 10)}
              </div>
            </div>
          </div>
          <Button variant="ghost" onClick={() => setEditing(true)}>Edit profile</Button>
        </div>
      ) : null}
      {!editing && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(150px,1fr))", gap: 12, marginTop: 16, paddingTop: 14, borderTop: `1px solid ${C.border}` }}>
          <div><div style={label}>Phone</div><div style={{ ...val, fontSize: 13 }}>{dash(parent.phone)}</div></div>
          <div><div style={label}>Consent</div><div style={{ ...val, fontSize: 13 }}>
            {parent.consent_confirmed ? `Confirmed · ${(parent.consent_timestamp || "").slice(0, 10) || "—"}` : "Not confirmed"}</div></div>
          <div><div style={label}>Last login</div><div style={{ ...val, fontSize: 13 }}>
            {parent.last_login_at ? timeAgo(parent.last_login_at) : "never"}</div></div>
          <div><div style={label}>Blueprint viewed</div><div style={{ ...val, fontSize: 13 }}>
            {parent.blueprint_first_viewed_at ? `Yes · ${(parent.blueprint_first_viewed_at || "").slice(0, 10)}` : "not yet"}</div></div>
          <div><div style={label}>Push devices</div><div style={{ ...val, fontSize: 13 }}>
            {parent.push_tokens > 0 ? `${parent.push_tokens} registered` : "none — unreachable"}</div></div>
          {isSet(parent.account_status) && parent.account_status !== "active" && (
            <div><div style={label}>Account status</div><SafetyVal>{parent.account_status}</SafetyVal></div>
          )}
        </div>
      )}
      {editing && (
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
          <CalendarBadge kind={athlete.calendar}
            count={athlete.calendar === "imported" ? stats.imported : stats.total} />
        </div>
      </div>

      {!editing ? (
        <>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(140px,1fr))", gap: 12, marginTop: 12 }}>
            <div><div style={label}>Total events</div><div style={val}>{stats.total}</div></div>
            <div><div style={label}>Upcoming</div><div style={val}>{stats.upcoming}</div></div>
            <div><div style={label}>Schedule source</div><div style={{ ...val, fontSize: 13 }}>
              {stats.total === 0 ? "—"
                : `${stats.imported || 0} from file · ${stats.manual ?? (stats.total - (stats.imported || 0))} manual`}</div></div>
            <div><div style={label}>Last synced</div><div style={{ ...val, fontSize: 13 }}>
              {athlete.last_synced_at ? athlete.last_synced_at.slice(0, 16).replace("T", " ") : "—"}</div></div>
          </div>
          <ProfileSection athlete={athlete} />
          <EngagementSection engagement={athlete.engagement} />
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

function SubHeader({ children }) {
  return <div style={{ font: `800 12px ${FONT_DISPLAY}`, color: C.text3, letterSpacing: "0.06em", textTransform: "uppercase", margin: "16px 0 8px", paddingTop: 12, borderTop: `1px solid ${C.border}` }}>{children}</div>;
}

// Tier 1 — the full profile the app already captures. Nutrition-safety fields
// (allergies / restrictions / preferences) are highlighted when set.
function ProfileSection({ athlete: a }) {
  return (
    <>
      <SubHeader>Nutrition profile</SubHeader>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(150px,1fr))", gap: 12 }}>
        <div><div style={label}>Allergies</div><SafetyVal>{a.allergies}</SafetyVal></div>
        <div><div style={label}>Dietary restrictions</div><SafetyVal>{a.dietary_restrictions}</SafetyVal></div>
        <div><div style={label}>Diet</div><div style={{ ...val, fontSize: 13 }}>{dash(a.diet_pref)}</div></div>
        <div><div style={label}>Supplements</div><div style={{ ...val, fontSize: 13 }}>{dash(a.supplement_use)}</div></div>
      </div>
      {isSet(a.food_preferences) && (
        <div style={{ marginTop: 10 }}>
          <div style={label}>Food likes / notes</div>
          <div style={{ font: `500 13px ${FONT_DISPLAY}`, color: C.text2, marginTop: 2 }}>{a.food_preferences}</div>
        </div>
      )}
      <SubHeader>Physical & sport</SubHeader>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(130px,1fr))", gap: 12 }}>
        <div><div style={label}>Date of birth</div><div style={{ ...val, fontSize: 13 }}>{dash(a.date_of_birth)}</div></div>
        <div><div style={label}>Height</div><div style={{ ...val, fontSize: 13 }}>{heightStr(a)}</div></div>
        <div><div style={label}>Weight</div><div style={{ ...val, fontSize: 13 }}>{a.weight_lbs ? `${a.weight_lbs} lbs` : "—"}</div></div>
        <div><div style={label}>Gender</div><div style={{ ...val, fontSize: 13 }}>{dash(a.gender)}</div></div>
        <div><div style={label}>Level</div><div style={{ ...val, fontSize: 13 }}>{dash(a.competition_level)}</div></div>
        <div><div style={label}>Season</div><div style={{ ...val, fontSize: 13 }}>{dash(a.season_phase)}</div></div>
        <div><div style={label}>Sweat profile</div><div style={{ ...val, fontSize: 13 }}>{dash(a.sweat_profile)}</div></div>
        <div><div style={label}>Lifestyle activity</div><div style={{ ...val, fontSize: 13 }}>{dash(a.lifestyle_activity)}</div></div>
      </div>
    </>
  );
}

// Tier 2 — is the family actually using (and reachable by) the app?
function EngagementSection({ engagement: e }) {
  if (!e) return null;
  const pantry = e.pantry || {};
  return (
    <>
      <SubHeader>Engagement</SubHeader>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(150px,1fr))", gap: 12 }}>
        <div><div style={label}>Meals logged</div><div style={{ ...val, fontSize: 13 }}>
          {e.meal_logs.total > 0 ? `${e.meal_logs.total} · last ${timeAgo(e.meal_logs.last_at)}` : "never"}</div></div>
        <div><div style={label}>Water logged</div><div style={{ ...val, fontSize: 13 }}>
          {e.water_logs.total > 0 ? `${e.water_logs.total} days · last ${e.water_logs.last_date}` : "never"}</div></div>
        <div><div style={label}>Fuel streak</div><div style={{ ...val, fontSize: 13 }}>
          {e.streak != null ? `${e.streak} day${e.streak === 1 ? "" : "s"}` : "—"}</div></div>
        <div><div style={label}>Grocery list</div><div style={{ ...val, fontSize: 13 }}>
          {pantry.latest_week_start
            ? `wk ${pantry.latest_week_start} · ${pantry.checked_count}/${pantry.item_count} checked`
            : "never generated"}</div></div>
        <div><div style={label}>Blueprint</div><div style={{ ...val, fontSize: 13 }}>
          {e.blueprint_generated ? "generated" : "not generated"}</div></div>
        <div><div style={label}>Athlete login</div><div style={{ ...val, fontSize: 13 }}>
          {e.athlete_login.exists ? `claimed · ${e.athlete_login.email}` : "not claimed"}</div></div>
        <div><div style={label}>Push (athlete)</div><div style={{ ...val, fontSize: 13 }}>
          {e.push.tokens > 0
            ? `${e.push.tokens} device${e.push.tokens === 1 ? "" : "s"}${e.push.last_push_at ? ` · last push ${timeAgo(e.push.last_push_at)}` : ""}`
            : "no device registered"}</div></div>
      </div>
    </>
  );
}

function ActivitySection({ activity }) {
  const items = [
    ...(activity.upcoming_events || []).map((e) => ({
      key: "e" + e.id, date: e.event_date, dot: C.brandMid,
      title: e.event_name || e.event_type, meta: `Upcoming event · ${e.source || "manual"}`,
    })),
    ...(activity.feature_ideas || []).map((f) => ({
      key: "i" + f.id, date: (f.submitted_at || "").slice(0, 10), dot: C.warm,
      title: f.suggestion, meta: "Idea submitted",
    })),
  ].sort((a, b) => (a.date < b.date ? 1 : -1));

  return (
    <>
      <h2 style={{ font: `800 18px ${FONT_DISPLAY}`, color: C.text1, margin: "26px 0 12px" }}>Activity</h2>
      {items.length === 0 ? (
        <Card><span style={{ color: C.text3, fontSize: 13 }}>No recent activity yet.</span></Card>
      ) : (
        <div style={{ position: "relative", paddingLeft: 26 }}>
          <div style={{ position: "absolute", left: 9, top: 10, bottom: 10, width: 2, background: C.border }} />
          {items.map((it) => (
            <div key={it.key} style={{ position: "relative", marginBottom: 12 }}>
              <span style={{
                position: "absolute", left: -21, top: 12, width: 11, height: 11, borderRadius: "50%",
                background: it.dot, border: `2px solid ${C.surface}`,
              }} />
              <Card style={{ padding: "10px 14px" }}>
                <div style={{ font: `600 14px ${FONT_DISPLAY}`, color: C.text1 }}>{it.title}</div>
                <div style={{ font: `500 12px ${FONT_DISPLAY}`, color: C.text3, marginTop: 2 }}>
                  {it.meta}{it.date ? ` · ${it.date}` : ""}
                </div>
              </Card>
            </div>
          ))}
        </div>
      )}
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
