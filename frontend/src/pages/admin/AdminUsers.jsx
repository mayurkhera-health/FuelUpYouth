import { useEffect, useState } from "react";
import { adminFetch, AuthError } from "./adminApi";
import { C, FONT_DISPLAY } from "./theme";
import { Avatar, Chip, Select, TextInput, Skeleton, EmptyState, ErrorRetry } from "./ui";

const LIMIT = 25;

// Master list for the split-pane Users view. Selecting a family highlights the
// row and loads it in the detail pane (via onSelect).
export default function AdminUsers({ selectedId, onSelect, onLoggedOut }) {
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
      const q = new URLSearchParams({ page, limit: LIMIT, search, calendar, has_athletes: hasAthletes, sort });
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
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: 14 }}>
        <h1 style={{ font: `800 22px ${FONT_DISPLAY}`, color: C.text1, margin: 0 }}>Users</h1>
        <span style={{ font: `600 13px ${FONT_DISPLAY}`, color: C.text3 }}>
          {total} {total === 1 ? "family" : "families"}
        </span>
      </div>

      <TextInput
        value={search} placeholder="Search name or email…"
        onChange={(e) => { setSearch(e.target.value); setPage(1); }}
        style={{ marginBottom: 8 }}
      />
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 14 }}>
        <Select value={calendar} onChange={(e) => { setCalendar(e.target.value); setPage(1); }}
          options={[{ value: "any", label: "Calendar: Any" }, { value: "none", label: "Not connected" }]} />
        <Select value={hasAthletes} onChange={(e) => { setHasAthletes(e.target.value); setPage(1); }}
          options={[{ value: "any", label: "Athletes: Any" }, { value: "yes", label: "Has athletes" }, { value: "no", label: "No athletes" }]} />
        <Select value={sort} onChange={(e) => { setSort(e.target.value); setPage(1); }}
          options={[{ value: "newest", label: "Newest" }, { value: "name", label: "Name" }, { value: "last_active", label: "Last active" }]} />
      </div>

      {error && <ErrorRetry message={error} onRetry={load} />}

      {loading && !data && (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {Array.from({ length: 8 }).map((_, i) => <Skeleton key={i} height={62} />)}
        </div>
      )}

      {!error && data && data.items.length === 0 && (
        <EmptyState title="No families match" subtitle="Try clearing the search or filters." />
      )}

      {!error && data && data.items.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: 6, opacity: loading ? 0.5 : 1 }}>
          {data.items.map((f) => {
            const sel = f.id === selectedId;
            return (
              <button key={f.id} onClick={() => onSelect(f.id)} style={{
                display: "flex", gap: 11, alignItems: "center", width: "100%", textAlign: "left", cursor: "pointer",
                padding: "10px 12px", borderRadius: 12,
                border: `1px solid ${sel ? C.brandMid : C.border}`,
                borderLeft: `4px solid ${sel ? C.brand : "transparent"}`,
                background: sel ? C.brandPale : C.surface,
                transition: "background .12s",
              }}>
                <Avatar name={f.full_name} size={38} />
                <div style={{ minWidth: 0, flex: 1 }}>
                  <div style={{ font: `700 15px ${FONT_DISPLAY}`, color: C.text1, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                    {f.full_name}
                  </div>
                  <div style={{ font: `400 12px ${FONT_DISPLAY}`, color: C.text3, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                    {f.email}
                  </div>
                  <div style={{ display: "flex", gap: 6, alignItems: "center", marginTop: 6, flexWrap: "wrap" }}>
                    {f.chips.map((c) => <Chip key={c} kind={c} />)}
                    <span style={{ font: `600 12px ${FONT_DISPLAY}`, color: C.text2 }}>
                      {f.athlete_count} {f.athlete_count === 1 ? "athlete" : "athletes"}
                    </span>
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      )}

      {data && totalPages > 1 && (
        <div style={{ display: "flex", gap: 10, alignItems: "center", justifyContent: "center", marginTop: 16 }}>
          <button disabled={page <= 1} onClick={() => setPage((p) => p - 1)} style={pagerStyle(page <= 1)}>← Prev</button>
          <span style={{ font: `600 12px ${FONT_DISPLAY}`, color: C.text3 }}>Page {page} of {totalPages}</span>
          <button disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)} style={pagerStyle(page >= totalPages)}>Next →</button>
        </div>
      )}
    </div>
  );
}

function pagerStyle(disabled) {
  return {
    font: `600 12px ${FONT_DISPLAY}`, color: disabled ? C.text3 : C.brand,
    background: C.surface, border: `1px solid ${C.border2}`, borderRadius: 8,
    padding: "6px 12px", cursor: disabled ? "not-allowed" : "pointer", opacity: disabled ? 0.5 : 1,
  };
}
