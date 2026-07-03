import { useEffect, useState } from "react";
import { adminFetch, AuthError } from "./adminApi";
import { C, FONT_DISPLAY } from "./theme";
import { Card, Chip, CalendarBadge, Select, TextInput, Skeleton, EmptyState, ErrorRetry } from "./ui";

const LIMIT = 25;

function timeAgo(iso) {
  if (!iso) return "—";
  const then = new Date(iso.replace(" ", "T"));
  if (isNaN(then)) return "—";
  const days = Math.floor((Date.now() - then.getTime()) / 86400000);
  if (days <= 0) return "today";
  if (days === 1) return "1d ago";
  if (days < 30) return `${days}d ago`;
  return `${Math.floor(days / 30)}mo ago`;
}

export default function AdminUsers({ onOpenFamily, onLoggedOut }) {
  const [search, setSearch] = useState("");
  const [calendar, setCalendar] = useState("any");
  const [hasAthletes, setHasAthletes] = useState("any");
  const [sort, setSort] = useState("newest");
  const [page, setPage] = useState(1);

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const t = setTimeout(() => load(), 250); // debounce search + filter changes
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search, calendar, hasAthletes, sort, page]);

  async function load() {
    setLoading(true);
    setError("");
    try {
      const q = new URLSearchParams({
        page, limit: LIMIT, search, calendar, has_athletes: hasAthletes, sort,
      });
      setData(await adminFetch(`/users?${q}`));
    } catch (err) {
      if (err instanceof AuthError) return onLoggedOut();
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  const total = data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / LIMIT));

  return (
    <div>
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: 18 }}>
        <h1 style={{ font: `800 24px ${FONT_DISPLAY}`, color: C.text1, margin: 0 }}>Users</h1>
        <span style={{ font: `600 14px ${FONT_DISPLAY}`, color: C.text3 }}>
          {total} {total === 1 ? "family" : "families"}
        </span>
      </div>

      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 16 }}>
        <TextInput
          value={search} placeholder="Search parent or athlete name / email…"
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          style={{ flex: 1, minWidth: 220 }}
        />
        <Select value={calendar} onChange={(e) => { setCalendar(e.target.value); setPage(1); }}
          options={[
            { value: "any", label: "Calendar: Any" },
            { value: "none", label: "Not connected" },
          ]} />
        <Select value={hasAthletes} onChange={(e) => { setHasAthletes(e.target.value); setPage(1); }}
          options={[
            { value: "any", label: "Athletes: Any" },
            { value: "yes", label: "Has athletes" },
            { value: "no", label: "No athletes" },
          ]} />
        <Select value={sort} onChange={(e) => { setSort(e.target.value); setPage(1); }}
          options={[
            { value: "newest", label: "Newest" },
            { value: "name", label: "Name" },
            { value: "last_active", label: "Last active" },
          ]} />
      </div>

      {error && <ErrorRetry message={error} onRetry={load} />}

      {loading && !data && (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} height={72} />)}
        </div>
      )}

      {!error && data && data.items.length === 0 && (
        <EmptyState title="No families match these filters" subtitle="Try clearing the search or filters." />
      )}

      {!error && data && data.items.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: 6, opacity: loading ? 0.5 : 1 }}>
          {data.items.map((f) => (
            <Card key={f.id} style={{ padding: "10px 14px", borderRadius: 12, cursor: "pointer" }}>
              <div onClick={() => onOpenFamily(f.id)}>
                <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
                  <div style={{ minWidth: 0 }}>
                    <div style={{ font: `800 16px ${FONT_DISPLAY}`, color: C.text1 }}>{f.full_name}</div>
                    <div style={{ font: `400 13px ${FONT_DISPLAY}`, color: C.text3 }}>{f.email}</div>
                  </div>
                  <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap", justifyContent: "flex-end" }}>
                    {f.chips.map((c) => <Chip key={c} kind={c} />)}
                    <span style={{ font: `600 13px ${FONT_DISPLAY}`, color: C.text2 }}>
                      {f.athlete_count} {f.athlete_count === 1 ? "athlete" : "athletes"}
                    </span>
                    <span style={{ font: `500 12px ${FONT_DISPLAY}`, color: C.text3 }}>
                      active {timeAgo(f.last_active)}
                    </span>
                  </div>
                </div>
                {f.athletes.length > 0 && (
                  <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 7 }}>
                    {f.athletes.map((a) => (
                      <span key={a.id} style={{
                        font: `500 12px ${FONT_DISPLAY}`, color: C.text2, background: C.surface2,
                        border: `1px solid ${C.border}`, borderRadius: 8, padding: "2px 8px",
                        display: "inline-flex", gap: 6, alignItems: "center",
                      }}>
                        {a.first_name}{a.position ? ` · ${a.position}` : ""}{a.age ? ` · ${a.age}` : ""}
                        <CalendarBadge kind={a.calendar} />
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}

      {data && totalPages > 1 && (
        <div style={{ display: "flex", gap: 12, alignItems: "center", justifyContent: "center", marginTop: 20 }}>
          <button disabled={page <= 1} onClick={() => setPage((p) => p - 1)}
            style={pagerStyle(page <= 1)}>← Prev</button>
          <span style={{ font: `600 13px ${FONT_DISPLAY}`, color: C.text3 }}>
            Page {page} of {totalPages}
          </span>
          <button disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}
            style={pagerStyle(page >= totalPages)}>Next →</button>
        </div>
      )}
    </div>
  );
}

function pagerStyle(disabled) {
  return {
    font: `600 13px ${FONT_DISPLAY}`, color: disabled ? C.text3 : C.brand,
    background: C.surface, border: `1px solid ${C.border2}`, borderRadius: 8,
    padding: "7px 14px", cursor: disabled ? "not-allowed" : "pointer", opacity: disabled ? 0.5 : 1,
  };
}
