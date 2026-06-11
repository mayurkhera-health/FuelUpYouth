import { useState, useEffect, useMemo, useRef, useCallback } from "react";
import FilterStrip from "../components/library/FilterStrip";
import ArticleSection from "../components/library/ArticleSection";
import ArticleDetail from "../components/library/ArticleDetail";
import { ARTICLE_CATEGORIES } from "../components/library/categories";
import Toast, { useToast } from "../components/today/Toast";

const API = import.meta.env.VITE_API_URL ?? "";

const SAVED_KEY = "fuelup_saved_articles";

function loadSaved() {
  try {
    return new Set(JSON.parse(localStorage.getItem(SAVED_KEY) || "[]"));
  } catch {
    return new Set();
  }
}

function persistSaved(set) {
  localStorage.setItem(SAVED_KEY, JSON.stringify([...set]));
}

export default function Library({ athlete }) {
  const [activeFilter, setActiveFilter] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [searchOpen, setSearchOpen] = useState(false);
  const [savedIds, setSavedIds] = useState(loadSaved);
  const [allArticles, setAllArticles] = useState([]);
  const [picks, setPicks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedArticle, setSelectedArticle] = useState(null);
  const { message: toastMsg, showToast } = useToast();
  const searchRef = useRef(null);
  const debounceRef = useRef(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [articlesRes, picksRes] = await Promise.all([
        fetch(`${API}/api/library/articles`),
        fetch(`${API}/api/library/picks/${athlete.id}`),
      ]);
      const [articles, picksData] = await Promise.all([
        articlesRes.ok ? articlesRes.json() : [],
        picksRes.ok ? picksRes.json() : [],
      ]);
      setAllArticles(articles);
      setPicks(picksData);
    } catch {
      // Silent on error — empty state handles it
    } finally {
      setLoading(false);
    }
  }, [athlete.id]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    if (searchOpen && searchRef.current) {
      searchRef.current.focus();
    }
  }, [searchOpen]);

  function handleFilterChange(key) {
    setActiveFilter(key);
    setSearchQuery("");
    setSearchOpen(false);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function handleSearchInput(e) {
    const val = e.target.value;
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => setSearchQuery(val), 200);
  }

  function handleToggleSave(articleId) {
    setSavedIds((prev) => {
      const next = new Set(prev);
      if (next.has(articleId)) {
        next.delete(articleId);
        showToast("Removed from saved");
      } else {
        next.add(articleId);
        showToast("Saved →");
      }
      persistSaved(next);
      return next;
    });
  }

  const pickIds = useMemo(() => new Set(picks.map((p) => p.id)), [picks]);

  const filteredArticles = useMemo(() => {
    let articles = allArticles;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return articles.filter(
        (a) =>
          a.title.toLowerCase().includes(q) ||
          a.summary.toLowerCase().includes(q) ||
          (ARTICLE_CATEGORIES[a.category]?.label ?? a.category)
            .toLowerCase()
            .includes(q) ||
          a.author.toLowerCase().includes(q)
      );
    }
    if (activeFilter !== "all") {
      return articles.filter((a) => a.category === activeFilter);
    }
    return articles.filter((a) => !pickIds.has(a.id));
  }, [allArticles, activeFilter, searchQuery, pickIds]);

  const showPicksSection = !searchQuery && activeFilter === "all";

  const section2Title = searchQuery
    ? "Search results"
    : activeFilter === "all"
    ? "All articles"
    : `${ARTICLE_CATEGORIES[activeFilter]?.label ?? activeFilter} articles`;

  const section2Sub =
    filteredArticles.length === 1
      ? "1 article"
      : `${filteredArticles.length} articles`;

  const section2Empty = searchQuery
    ? "no_search_results"
    : activeFilter !== "all"
    ? "no_filter_results"
    : "no_articles";

  const genderPronoun =
    athlete.gender?.toLowerCase() === "girl" ||
    athlete.gender?.toLowerCase() === "female"
      ? "her"
      : "his";

  if (selectedArticle) {
    return (
      <div>
        <ArticleDetail
          article={selectedArticle}
          isSaved={savedIds.has(selectedArticle.id)}
          onSave={handleToggleSave}
          onBack={() => setSelectedArticle(null)}
        />
        <Toast message={toastMsg} />
      </div>
    );
  }

  return (
    <div>
      {/* Search bar (inline, opens on button tap) */}
      {searchOpen && (
        <div style={s.searchRow}>
          <input
            ref={searchRef}
            style={s.searchInput}
            placeholder="Search articles…"
            defaultValue={searchQuery}
            onChange={handleSearchInput}
          />
          <button
            style={s.searchClose}
            onClick={() => {
              setSearchQuery("");
              setSearchOpen(false);
            }}
          >
            ✕
          </button>
        </div>
      )}

      {!searchOpen && (
        <div style={s.topRow}>
          <div style={s.pageTitle}>📚 Library</div>
          <button style={s.searchBtn} onClick={() => setSearchOpen(true)} aria-label="Search">
            🔍
          </button>
        </div>
      )}

      {/* Filter strip — hidden while search is active */}
      {!searchQuery && (
        <FilterStrip active={activeFilter} onChange={handleFilterChange} />
      )}

      {loading && <p style={s.loadingText}>Loading articles…</p>}

      {!loading && (
        <>
          {/* Section 1 — personalized picks */}
          {showPicksSection && picks.length > 0 && (
            <ArticleSection
              title={`For ${athlete.first_name} this week`}
              subLabel={`Selected for ${genderPronoun} gaps`}
              articles={picks}
              showReason
              athleteName={athlete.first_name}
              savedIds={savedIds}
              onSave={handleToggleSave}
              onOpen={setSelectedArticle}
            />
          )}

          {/* Section 2 — all / filtered */}
          <ArticleSection
            title={section2Title}
            subLabel={section2Sub}
            articles={filteredArticles}
            savedIds={savedIds}
            onSave={handleToggleSave}
            onOpen={setSelectedArticle}
            emptyCase={section2Empty}
          />
        </>
      )}

      <p style={s.disclaimer}>
        Written by Purvi Shah MS RDN · Not a substitute for medical advice ·
        Science: Everett MD 2025 · AAP · Boston Children's Hospital RDN
      </p>

      <Toast message={toastMsg} />
    </div>
  );
}

const s = {
  topRow: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: "4px",
  },
  pageTitle: {
    fontFamily: "'Nunito', sans-serif",
    fontSize: "18px",
    fontWeight: "800",
    color: "#1b3a2a",
  },
  searchBtn: {
    background: "none",
    border: "1px solid #dce8e0",
    borderRadius: "8px",
    width: "30px",
    height: "30px",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: "14px",
    cursor: "pointer",
  },
  searchRow: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    marginBottom: "4px",
  },
  searchInput: {
    flex: 1,
    height: "34px",
    border: "1px solid #2d6a4f",
    borderRadius: "8px",
    padding: "0 10px",
    fontSize: "13px",
    fontFamily: "'DM Sans', sans-serif",
    color: "#1b3a2a",
    outline: "none",
  },
  searchClose: {
    background: "none",
    border: "1px solid #dce8e0",
    borderRadius: "6px",
    width: "30px",
    height: "30px",
    cursor: "pointer",
    fontSize: "13px",
    color: "#8aa898",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  },
  loadingText: {
    textAlign: "center",
    color: "#8aa898",
    fontSize: "14px",
    padding: "32px 0",
  },
  disclaimer: {
    textAlign: "center",
    fontSize: "10px",
    fontWeight: "300",
    color: "#8aa898",
    lineHeight: "1.5",
    marginTop: "8px",
    paddingBottom: "8px",
  },
};
