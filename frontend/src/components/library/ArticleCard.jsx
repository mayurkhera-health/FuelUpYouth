import { ARTICLE_CATEGORIES } from "./categories";

export default function ArticleCard({
  article,
  showReason = false,
  athleteName = "",
  isSaved,
  onSave,
  onClick,
}) {
  const cat = ARTICLE_CATEGORIES[article.category] ?? {
    label: article.category,
    accentColor: "#8aa898",
  };

  const dateStr = article.published_date
    ? new Date(article.published_date + "T12:00:00").toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
      })
    : "";

  return (
    <div
      style={s.card}
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === "Enter" && onClick?.()}
    >
      {/* Left accent bar */}
      <div style={{ ...s.bar, background: cat.accentColor }} />

      {/* Card body */}
      <div style={s.body}>
        {/* Meta row */}
        <div style={s.metaRow}>
          <span style={{ ...s.catLabel, color: cat.accentColor }}>{cat.label}</span>
          <span style={s.dot} />
          <span style={s.readTime}>{article.read_time_min} min read</span>
          {showReason && (
            <span style={s.forBadge}>For {athleteName}</span>
          )}
        </div>

        {/* Title */}
        <div style={s.title}>{article.title}</div>

        {/* Summary */}
        <div style={s.summary}>{article.summary}</div>

        {/* Reason line — personalized only */}
        {showReason && article.alex_reason && (
          <div style={{ ...s.reason, color: cat.accentColor }}>
            "{article.alex_reason}"
          </div>
        )}

        {/* Footer */}
        <div style={s.footer}>
          <span style={s.author}>
            {article.author} · {dateStr}
          </span>
          <button
            style={{ ...s.saveBtn, opacity: isSaved ? 1 : 0.45 }}
            onClick={(e) => {
              e.stopPropagation();
              onSave?.(article.id);
            }}
            aria-label={isSaved ? "Remove from saved" : "Save article"}
          >
            🔖
          </button>
        </div>
      </div>
    </div>
  );
}

const s = {
  card: {
    display: "flex",
    flexDirection: "row",
    background: "#fff",
    border: "1px solid #dce8e0",
    borderRadius: "14px",
    overflow: "hidden",
    cursor: "pointer",
    marginBottom: "9px",
    transition: "border-color 0.15s",
  },
  bar: {
    width: "3px",
    flexShrink: 0,
  },
  body: {
    flex: 1,
    padding: "13px 13px 11px",
    display: "flex",
    flexDirection: "column",
    gap: "5px",
    minWidth: 0,
  },
  metaRow: {
    display: "flex",
    alignItems: "center",
    gap: "6px",
    flexWrap: "wrap",
  },
  catLabel: {
    fontSize: "9px",
    fontWeight: "700",
    textTransform: "uppercase",
    letterSpacing: ".08em",
  },
  dot: {
    width: "3px",
    height: "3px",
    borderRadius: "50%",
    background: "#8aa898",
    flexShrink: 0,
  },
  readTime: {
    fontSize: "10px",
    fontWeight: "300",
    color: "#8aa898",
  },
  forBadge: {
    fontSize: "9px",
    fontWeight: "700",
    textTransform: "uppercase",
    letterSpacing: ".06em",
    background: "#2d6a4f",
    color: "#fff",
    padding: "2px 6px",
    borderRadius: "3px",
  },
  title: {
    fontFamily: "'Nunito', sans-serif",
    fontSize: "14px",
    fontWeight: "700",
    letterSpacing: "-.01em",
    color: "#1b3a2a",
    lineHeight: "1.3",
  },
  summary: {
    fontSize: "11px",
    fontWeight: "300",
    color: "#4a6358",
    lineHeight: "1.5",
  },
  reason: {
    fontSize: "10px",
    fontWeight: "400",
    fontStyle: "italic",
    lineHeight: "1.3",
  },
  footer: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    paddingTop: "6px",
    borderTop: "1px solid #dce8e0",
    marginTop: "2px",
  },
  author: {
    fontSize: "10px",
    fontWeight: "300",
    color: "#8aa898",
  },
  saveBtn: {
    background: "none",
    border: "none",
    cursor: "pointer",
    fontSize: "14px",
    padding: "0",
    lineHeight: "1",
    transition: "opacity 0.15s",
  },
};
