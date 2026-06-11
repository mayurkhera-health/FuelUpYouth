const STATES = {
  no_filter_results: {
    icon: "📭",
    title: "Nothing here yet",
    sub: "More articles in this category coming soon.",
  },
  no_search_results: {
    icon: "🔍",
    title: "No articles found",
    sub: "Try a different search term or browse by category.",
  },
  no_articles: {
    icon: "📚",
    title: "Articles coming soon",
    sub: "Purvi Shah MS RDN is preparing nutrition guides for the season.",
  },
};

export default function EmptyState({ case: variant = "no_articles" }) {
  const { icon, title, sub } = STATES[variant] ?? STATES.no_articles;
  return (
    <div style={s.card}>
      <div style={s.icon}>{icon}</div>
      <div style={s.title}>{title}</div>
      <div style={s.sub}>{sub}</div>
    </div>
  );
}

const s = {
  card: {
    background: "#fff",
    border: "1px solid #dce8e0",
    borderRadius: "14px",
    padding: "32px 16px",
    textAlign: "center",
  },
  icon: { fontSize: "28px", marginBottom: "8px" },
  title: {
    fontFamily: "'Nunito', sans-serif",
    fontSize: "14px",
    fontWeight: "700",
    color: "#1b3a2a",
    marginBottom: "4px",
  },
  sub: {
    fontSize: "12px",
    fontWeight: "300",
    color: "#4a6358",
    lineHeight: "1.5",
  },
};
