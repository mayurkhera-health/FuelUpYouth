import ArticleCard from "./ArticleCard";
import EmptyState from "./EmptyState";

export default function ArticleSection({
  title,
  subLabel,
  articles,
  showReason = false,
  athleteName = "",
  savedIds,
  onSave,
  onOpen,
  emptyCase = "no_articles",
}) {
  return (
    <div style={s.section}>
      <div style={s.header}>
        <div style={s.title}>{title}</div>
        {subLabel && <div style={s.sub}>{subLabel}</div>}
      </div>

      {articles.length === 0 ? (
        <EmptyState case={emptyCase} />
      ) : (
        articles.map((article, i) => (
          <ArticleCard
            key={article.id}
            article={article}
            showReason={showReason}
            athleteName={athleteName}
            isSaved={savedIds.has(article.id)}
            onSave={onSave}
            onClick={() => onOpen(article)}
            style={i === articles.length - 1 ? { marginBottom: 0 } : {}}
          />
        ))
      )}
    </div>
  );
}

const s = {
  section: { marginBottom: "24px" },
  header: {
    display: "flex",
    alignItems: "baseline",
    justifyContent: "space-between",
    marginBottom: "12px",
  },
  title: {
    fontFamily: "'Nunito', sans-serif",
    fontSize: "15px",
    fontWeight: "800",
    letterSpacing: "-.01em",
    color: "#1b3a2a",
  },
  sub: { fontSize: "11px", fontWeight: "300", color: "#8aa898" },
};
