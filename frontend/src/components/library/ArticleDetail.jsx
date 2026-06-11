import { ARTICLE_CATEGORIES } from "./categories";

function renderMarkdown(md) {
  if (!md) return "";
  const escaped = md
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
  const html = escaped
    .replace(/^### (.+)$/gm, "<h3>$1</h3>")
    .replace(/^## (.+)$/gm, "<h2>$1</h2>")
    .replace(/^# (.+)$/gm, "<h1>$1</h1>")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/_(.+?)_/g, "<em>$1</em>")
    .replace(/\n\n/g, "<br/><br/>")
    .replace(/\n/g, "<br/>");
  return html;
}

export default function ArticleDetail({ article, isSaved, onSave, onBack }) {
  const cat = ARTICLE_CATEGORIES[article.category] ?? {
    label: article.category,
    accentColor: "#8aa898",
  };

  const dateStr = article.published_date
    ? new Date(article.published_date + "T12:00:00").toLocaleDateString("en-US", {
        month: "long",
        day: "numeric",
        year: "numeric",
      })
    : "";

  return (
    <div style={s.page}>
      {/* Back bar */}
      <div style={s.backBar}>
        <button style={s.backBtn} onClick={onBack}>
          ← Library
        </button>
        <button
          style={{ ...s.saveBtn, opacity: isSaved ? 1 : 0.45 }}
          onClick={() => onSave?.(article.id)}
          aria-label={isSaved ? "Remove from saved" : "Save article"}
        >
          🔖
        </button>
      </div>

      {/* Article header */}
      <div style={s.header}>
        <div style={s.metaRow}>
          <span style={{ ...s.catLabel, color: cat.accentColor }}>{cat.label}</span>
          <span style={s.dot} />
          <span style={s.readTime}>{article.read_time_min} min read</span>
        </div>
        <h1 style={s.title}>{article.title}</h1>
        <div style={s.byline}>
          {article.author} · {dateStr}
          {article.science_source && (
            <span style={s.scienceBadge}>📖 {article.science_source}</span>
          )}
        </div>
      </div>

      <div style={s.divider} />

      {/* Article body */}
      <div
        style={s.body}
        dangerouslySetInnerHTML={{ __html: renderMarkdown(article.body_markdown) }}
      />

      {/* Footer */}
      <div style={s.footer}>
        <p style={s.disclaimer}>
          Content written by Purvi Shah MS RDN. Not a substitute for medical
          advice or nutrition therapy.
        </p>
        {article.science_source && (
          <p style={s.source}>Science: {article.science_source}</p>
        )}
      </div>
    </div>
  );
}

const s = {
  page: {
    background: "#fff",
    borderRadius: "14px",
    border: "1px solid #dce8e0",
    overflow: "hidden",
  },
  backBar: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "10px 14px 8px",
    borderBottom: "1px solid #dce8e0",
    background: "#fafcfb",
  },
  backBtn: {
    background: "none",
    border: "none",
    cursor: "pointer",
    fontSize: "13px",
    fontWeight: "600",
    color: "#2d6a4f",
    padding: "0",
    fontFamily: "'Nunito', sans-serif",
  },
  saveBtn: {
    background: "none",
    border: "none",
    cursor: "pointer",
    fontSize: "16px",
    padding: "0",
    transition: "opacity 0.15s",
  },
  header: { padding: "16px 16px 12px" },
  metaRow: { display: "flex", alignItems: "center", gap: "6px", marginBottom: "8px" },
  catLabel: {
    fontSize: "9px",
    fontWeight: "700",
    textTransform: "uppercase",
    letterSpacing: ".08em",
  },
  dot: { width: "3px", height: "3px", borderRadius: "50%", background: "#8aa898" },
  readTime: { fontSize: "10px", fontWeight: "300", color: "#8aa898" },
  title: {
    fontFamily: "'Nunito', sans-serif",
    fontSize: "22px",
    fontWeight: "900",
    color: "#1b3a2a",
    letterSpacing: "-.02em",
    lineHeight: "1.2",
    margin: "0 0 8px",
  },
  byline: {
    fontSize: "11px",
    fontWeight: "300",
    color: "#8aa898",
    display: "flex",
    alignItems: "center",
    gap: "8px",
    flexWrap: "wrap",
  },
  scienceBadge: {
    fontSize: "10px",
    background: "#f0f8f4",
    color: "#2d6a4f",
    padding: "2px 7px",
    borderRadius: "4px",
    border: "1px solid #dce8e0",
  },
  divider: { height: "1px", background: "#dce8e0" },
  body: {
    padding: "16px",
    fontSize: "13px",
    fontWeight: "400",
    color: "#1b3a2a",
    lineHeight: "1.7",
    fontFamily: "'DM Sans', sans-serif",
  },
  footer: {
    borderTop: "1px solid #dce8e0",
    padding: "12px 16px",
    background: "#fafcfb",
  },
  disclaimer: {
    fontSize: "10px",
    color: "#8aa898",
    lineHeight: "1.5",
    margin: "0 0 4px",
    fontStyle: "italic",
  },
  source: {
    fontSize: "10px",
    color: "#8aa898",
    margin: "0",
  },
};
