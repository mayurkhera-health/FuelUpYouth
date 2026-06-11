import { useState, useEffect } from "react";
import { FILTER_CHIPS } from "../components/library/categories";

const API = import.meta.env.VITE_API_URL ?? "";
const ADMIN_KEY = "fuelup-admin";

const BLANK = {
  title: "",
  summary: "",
  body_markdown: "",
  category: "iron",
  audience: "both",
  read_time_min: 3,
  author: "Purvi Shah MS RDN",
  science_source: "",
  published_date: new Date().toISOString().split("T")[0],
  is_active: 1,
};

const CATEGORY_OPTIONS = FILTER_CHIPS.filter((c) => c.key !== "all");

export default function LibraryAdmin() {
  const [authed, setAuthed] = useState(false);
  const [keyInput, setKeyInput] = useState("");
  const [articles, setArticles] = useState([]);
  const [form, setForm] = useState(BLANK);
  const [editId, setEditId] = useState(null);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState("");
  const [tab, setTab] = useState("list"); // 'list' | 'new'

  function tryAuth() {
    if (keyInput === ADMIN_KEY) {
      setAuthed(true);
    } else {
      setMsg("Wrong key.");
    }
  }

  async function loadArticles() {
    const res = await fetch(`${API}/api/library/admin/articles`, {
      headers: { "x-admin-key": ADMIN_KEY },
    });
    if (res.ok) setArticles(await res.json());
  }

  useEffect(() => {
    if (authed) loadArticles();
  }, [authed]);

  async function handleSave(isDraft) {
    setSaving(true);
    setMsg("");
    const payload = { ...form, is_active: isDraft ? 0 : 1 };
    try {
      const url = editId
        ? `${API}/api/library/articles/${editId}`
        : `${API}/api/library/articles`;
      const method = editId ? "PUT" : "POST";
      const res = await fetch(url, {
        method,
        headers: {
          "Content-Type": "application/json",
          "x-admin-key": ADMIN_KEY,
        },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (res.ok) {
        setMsg(editId ? "Updated." : `Created (id: ${data.id}).`);
        setForm(BLANK);
        setEditId(null);
        setTab("list");
        loadArticles();
      } else {
        setMsg(data.detail ?? "Error saving.");
      }
    } catch (e) {
      setMsg(e.message);
    } finally {
      setSaving(false);
    }
  }

  function startEdit(article) {
    setForm({
      title: article.title,
      summary: article.summary,
      body_markdown: article.body_markdown,
      category: article.category,
      audience: article.audience,
      read_time_min: article.read_time_min,
      author: article.author,
      science_source: article.science_source ?? "",
      published_date: article.published_date,
      is_active: article.is_active,
    });
    setEditId(article.id);
    setTab("new");
    window.scrollTo({ top: 0 });
  }

  if (!authed) {
    return (
      <div style={p.outer}>
        <div style={p.authCard}>
          <div style={p.logo}>📚 Library Admin</div>
          <input
            style={p.input}
            type="password"
            placeholder="Admin key"
            value={keyInput}
            onChange={(e) => setKeyInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && tryAuth()}
          />
          <button style={p.btn} onClick={tryAuth}>Enter</button>
          {msg && <p style={p.errMsg}>{msg}</p>}
        </div>
      </div>
    );
  }

  return (
    <div style={p.outer}>
      <div style={p.card}>
        <div style={p.header}>
          <div style={p.logo}>📚 Library Admin</div>
          <div style={p.tabs}>
            <button
              style={{ ...p.tabBtn, ...(tab === "list" ? p.tabActive : {}) }}
              onClick={() => { setTab("list"); setEditId(null); setForm(BLANK); }}
            >
              Articles ({articles.length})
            </button>
            <button
              style={{ ...p.tabBtn, ...(tab === "new" ? p.tabActive : {}) }}
              onClick={() => { setTab("new"); setEditId(null); setForm(BLANK); }}
            >
              {editId ? "Edit Article" : "+ New Article"}
            </button>
          </div>
        </div>

        {msg && <div style={p.msgBar}>{msg}</div>}

        {tab === "list" && (
          <div>
            {articles.length === 0 && (
              <p style={p.empty}>No articles yet. Add the first one →</p>
            )}
            {articles.map((a) => (
              <div key={a.id} style={p.row}>
                <div style={p.rowLeft}>
                  <div style={p.rowTitle}>{a.title}</div>
                  <div style={p.rowMeta}>
                    {a.category} · {a.read_time_min}min ·{" "}
                    {a.is_active ? "✅ Published" : "⬜ Draft"} ·{" "}
                    {a.published_date}
                  </div>
                </div>
                <button style={p.editBtn} onClick={() => startEdit(a)}>
                  Edit
                </button>
              </div>
            ))}
          </div>
        )}

        {tab === "new" && (
          <div style={p.form}>
            <label style={p.label}>
              Title *
              <input
                style={p.input}
                value={form.title}
                onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
                placeholder="Article title"
              />
            </label>

            <label style={p.label}>
              Summary * (shown on card, max 200 chars)
              <textarea
                style={{ ...p.input, height: "60px", resize: "vertical" }}
                value={form.summary}
                onChange={(e) => setForm((f) => ({ ...f, summary: e.target.value }))}
                placeholder="1-2 sentence preview shown on the card"
                maxLength={200}
              />
              <span style={p.charCount}>{form.summary.length}/200</span>
            </label>

            <label style={p.label}>
              Body (Markdown) *
              <textarea
                style={{ ...p.input, height: "220px", resize: "vertical", fontFamily: "monospace", fontSize: "12px" }}
                value={form.body_markdown}
                onChange={(e) => setForm((f) => ({ ...f, body_markdown: e.target.value }))}
                placeholder="## Heading&#10;&#10;Paragraph text..."
              />
            </label>

            <div style={p.row2}>
              <label style={{ ...p.label, flex: 1 }}>
                Category *
                <select
                  style={p.select}
                  value={form.category}
                  onChange={(e) => setForm((f) => ({ ...f, category: e.target.value }))}
                >
                  {CATEGORY_OPTIONS.map((c) => (
                    <option key={c.key} value={c.key}>
                      {c.label}
                    </option>
                  ))}
                </select>
              </label>

              <label style={{ ...p.label, flex: 1 }}>
                Audience *
                <select
                  style={p.select}
                  value={form.audience}
                  onChange={(e) => setForm((f) => ({ ...f, audience: e.target.value }))}
                >
                  <option value="both">Both</option>
                  <option value="athlete">Athlete</option>
                  <option value="parent">Parent</option>
                </select>
              </label>

              <label style={{ ...p.label, width: "80px" }}>
                Read time (min) *
                <input
                  style={p.input}
                  type="number"
                  min={1}
                  max={30}
                  value={form.read_time_min}
                  onChange={(e) => setForm((f) => ({ ...f, read_time_min: +e.target.value }))}
                />
              </label>
            </div>

            <div style={p.row2}>
              <label style={{ ...p.label, flex: 1 }}>
                Author
                <input
                  style={p.input}
                  value={form.author}
                  onChange={(e) => setForm((f) => ({ ...f, author: e.target.value }))}
                />
              </label>

              <label style={{ ...p.label, flex: 1 }}>
                Science source (optional)
                <input
                  style={p.input}
                  value={form.science_source}
                  onChange={(e) => setForm((f) => ({ ...f, science_source: e.target.value }))}
                  placeholder="e.g. Everett MD 2025"
                />
              </label>

              <label style={{ ...p.label, width: "140px" }}>
                Published date *
                <input
                  style={p.input}
                  type="date"
                  value={form.published_date}
                  onChange={(e) => setForm((f) => ({ ...f, published_date: e.target.value }))}
                />
              </label>
            </div>

            <div style={p.guidelines}>
              <strong>Content guidelines:</strong> Write for the athlete first,
              parent second. Lead with performance consequence, then the science.
              Cite at least one source. Read time ≈ word count ÷ 200.
            </div>

            <div style={p.actions}>
              <button
                style={{ ...p.btn, background: "#fff", color: "#2d6a4f", border: "1.5px solid #2d6a4f" }}
                onClick={() => handleSave(true)}
                disabled={saving}
              >
                Save Draft
              </button>
              <button
                style={p.btn}
                onClick={() => handleSave(false)}
                disabled={saving || !form.title || !form.summary || !form.body_markdown}
              >
                {saving ? "Saving…" : editId ? "Update & Publish" : "Publish"}
              </button>
              {editId && (
                <button
                  style={{ ...p.btn, background: "#fff", color: "#8aa898", border: "1px solid #dce8e0" }}
                  onClick={() => { setEditId(null); setForm(BLANK); setTab("list"); }}
                >
                  Cancel
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

const p = {
  outer: {
    minHeight: "100vh",
    background: "#f4f8f5",
    padding: "24px 16px",
    fontFamily: "'Nunito', 'DM Sans', sans-serif",
  },
  card: {
    background: "#fff",
    borderRadius: "16px",
    border: "1px solid #dce8e0",
    maxWidth: "780px",
    margin: "0 auto",
    overflow: "hidden",
  },
  authCard: {
    background: "#fff",
    borderRadius: "16px",
    padding: "40px 32px",
    maxWidth: "360px",
    margin: "0 auto",
    display: "flex",
    flexDirection: "column",
    gap: "12px",
    border: "1px solid #dce8e0",
  },
  header: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "16px 20px",
    borderBottom: "1px solid #dce8e0",
  },
  logo: { fontSize: "18px", fontWeight: "800", color: "#2d6a4f" },
  tabs: { display: "flex", gap: "8px" },
  tabBtn: {
    padding: "6px 14px",
    borderRadius: "8px",
    border: "1px solid #dce8e0",
    background: "#fff",
    color: "#4a6358",
    fontSize: "12px",
    fontWeight: "600",
    cursor: "pointer",
  },
  tabActive: { background: "#2d6a4f", color: "#fff", borderColor: "#2d6a4f" },
  msgBar: {
    padding: "10px 20px",
    background: "#f0faf4",
    borderBottom: "1px solid #dce8e0",
    fontSize: "13px",
    color: "#2d6a4f",
    fontWeight: "600",
  },
  empty: { textAlign: "center", color: "#8aa898", padding: "32px", fontSize: "14px" },
  row: {
    display: "flex",
    alignItems: "center",
    padding: "12px 20px",
    borderBottom: "1px solid #f4f8f5",
    gap: "12px",
  },
  rowLeft: { flex: 1, minWidth: 0 },
  rowTitle: { fontSize: "14px", fontWeight: "700", color: "#1b3a2a", marginBottom: "2px" },
  rowMeta: { fontSize: "11px", color: "#8aa898" },
  editBtn: {
    padding: "5px 14px",
    borderRadius: "6px",
    border: "1px solid #dce8e0",
    background: "#fff",
    color: "#2d6a4f",
    fontSize: "12px",
    fontWeight: "600",
    cursor: "pointer",
    flexShrink: 0,
  },
  form: { padding: "20px", display: "flex", flexDirection: "column", gap: "14px" },
  label: {
    display: "flex",
    flexDirection: "column",
    gap: "4px",
    fontSize: "12px",
    fontWeight: "600",
    color: "#4a6358",
  },
  input: {
    border: "1px solid #dce8e0",
    borderRadius: "8px",
    padding: "8px 10px",
    fontSize: "13px",
    color: "#1b3a2a",
    fontFamily: "'DM Sans', sans-serif",
    outline: "none",
    width: "100%",
    boxSizing: "border-box",
  },
  select: {
    border: "1px solid #dce8e0",
    borderRadius: "8px",
    padding: "8px 10px",
    fontSize: "13px",
    color: "#1b3a2a",
    background: "#fff",
    width: "100%",
    boxSizing: "border-box",
  },
  charCount: { fontSize: "10px", color: "#8aa898", alignSelf: "flex-end" },
  row2: { display: "flex", gap: "12px", flexWrap: "wrap" },
  guidelines: {
    fontSize: "11px",
    color: "#4a6358",
    background: "#f4f8f5",
    borderRadius: "8px",
    padding: "10px 12px",
    lineHeight: "1.5",
  },
  actions: { display: "flex", gap: "8px", flexWrap: "wrap", paddingTop: "4px" },
  btn: {
    padding: "10px 22px",
    borderRadius: "8px",
    border: "none",
    background: "#2d6a4f",
    color: "#fff",
    fontSize: "13px",
    fontWeight: "700",
    cursor: "pointer",
    fontFamily: "'Nunito', sans-serif",
  },
  errMsg: { color: "#c84040", fontSize: "12px", margin: "0" },
};
