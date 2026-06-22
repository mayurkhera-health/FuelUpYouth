import { useState, useEffect } from "react";
import LoadingState from "./components/LoadingState";

const API = import.meta.env.VITE_API_URL ?? "";

const CATEGORY_LABELS = {
  "pre-game":           "Pre-Game Meal",
  "pre-game-snack":     "Pre-Game Snack",
  "halftime":           "Halftime Fuel",
  "post-game-recovery": "Post-Game Recovery",
  "practice":           "Practice Day",
  "strength":           "Strength Training",
  "tournament":         "Tournament",
  "meal-prep":          "Meal Prep",
};

export default function RecipesScreen({ athlete }) {
  const [recipes, setRecipes]     = useState([]);
  const [categories, setCategories] = useState([]);
  const [activeCategory, setActiveCategory] = useState(null);
  const [loading, setLoading]     = useState(true);
  const [expanded, setExpanded]   = useState(null);
  const [swapping, setSwapping]   = useState(null);
  const [swapResult, setSwapResult] = useState({});

  useEffect(() => {
    Promise.all([
      fetch(`${API}/api/recipes/categories`).then(r => r.json()),
      fetch(`${API}/api/recipes/`).then(r => r.json()),
    ]).then(([cats, recs]) => {
      setCategories(cats.categories || []);
      setRecipes(recs.recipes || []);
      setLoading(false);
    });
  }, []);

  const filtered = activeCategory
    ? recipes.filter(r => r.category === activeCategory)
    : recipes;

  async function handleSwap(recipe) {
    setSwapping(recipe.id);
    const res = await fetch(`${API}/api/recipes/swap`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        athlete_id: athlete.id,
        disliked_recipe: recipe.name,
        meal_timing_category: recipe.category,
      }),
    });
    const data = res.ok ? await res.json() : { error: "Swap failed." };
    setSwapResult(prev => ({ ...prev, [recipe.id]: data }));
    setSwapping(null);
  }

  if (loading) return <LoadingState message="Loading recipes…" />;

  return (
    <div>
      <h2 style={s.title}>Recipe Library</h2>
      <p style={s.subtitle}>Science-backed fueling options for every moment of training.</p>

      {/* Category filters */}
      <div style={s.filterRow}>
        <button style={{ ...s.chip, ...(activeCategory === null ? s.chipActive : {}) }} onClick={() => setActiveCategory(null)}>All</button>
        {categories.map(c => (
          <button key={c} style={{ ...s.chip, ...(activeCategory === c ? s.chipActive : {}) }} onClick={() => setActiveCategory(c)}>
            {CATEGORY_LABELS[c] || c}
          </button>
        ))}
      </div>

      {/* Recipe cards */}
      {filtered.map(recipe => (
        <div key={recipe.id} style={s.card}>
          <div style={s.cardHeader} onClick={() => setExpanded(expanded === recipe.id ? null : recipe.id)}>
            <div style={s.cardLeft}>
              <div style={s.recipeName}>{recipe.name}</div>
              <div style={s.recipeTiming}>{recipe.timing}</div>
              <div style={s.macroRow}>
                <span style={s.macro}>{recipe.macros.calories} kcal</span>
                <span style={s.macro}>{recipe.macros.carbs_g}g carbs</span>
                <span style={s.macro}>{recipe.macros.protein_g}g protein</span>
                <span style={s.macro}>{recipe.macros.fat_g}g fat</span>
              </div>
            </div>
            <span style={s.chevron}>{expanded === recipe.id ? "▲" : "▼"}</span>
          </div>

          {expanded === recipe.id && (
            <div style={s.detail}>
              <div style={s.detailSection}>
                <div style={s.detailLabel}>Ingredients</div>
                <div style={s.detailText}>{recipe.ingredients}</div>
              </div>
              {recipe.dietary?.length > 0 && (
                <div style={s.detailSection}>
                  <div style={s.detailLabel}>Dietary</div>
                  <div style={s.tagRow}>
                    {recipe.dietary.map(d => <span key={d} style={s.tag}>{d}</span>)}
                  </div>
                </div>
              )}
              {recipe.allergens?.length > 0 && (
                <div style={s.detailSection}>
                  <div style={s.detailLabel}>Contains</div>
                  <div style={s.tagRow}>
                    {recipe.allergens.map(a => <span key={a} style={s.allergenTag}>{a}</span>)}
                  </div>
                </div>
              )}

              {swapResult[recipe.id] ? (
                <div style={s.swapResult}>
                  <div style={s.swapTitle}>AI Swap Suggestion</div>
                  {swapResult[recipe.id].swap_recipe && <div style={s.swapName}>{swapResult[recipe.id].swap_recipe}</div>}
                  {swapResult[recipe.id].reason && <div style={s.swapReason}>{swapResult[recipe.id].reason}</div>}
                  {swapResult[recipe.id].instructions && <div style={s.swapReason}>{swapResult[recipe.id].instructions}</div>}
                  {!swapResult[recipe.id].swap_recipe && !swapResult[recipe.id].reason && (
                    <div style={{ fontSize: "17px", color: "#4a6358", whiteSpace: "pre-wrap" }}>{JSON.stringify(swapResult[recipe.id], null, 2)}</div>
                  )}
                </div>
              ) : (
                <button style={s.swapBtn} onClick={() => handleSwap(recipe)} disabled={swapping === recipe.id}>
                  {swapping === recipe.id ? "Finding swap…" : "🔄 Don't like this? Get a swap"}
                </button>
              )}
            </div>
          )}
        </div>
      ))}
      <p style={s.attribution}>Nutrition data powered by Edamam · developer.edamam.com</p>
    </div>
  );
}

const s = {
  title: { fontSize: "23px", fontWeight: "700", fontFamily: "'Nunito', sans-serif", color: "#1b3a2a", margin: "0 0 4px" },
  subtitle: { fontSize: "18px", color: "#8aa898", marginBottom: "20px" },
  filterRow: { display: "flex", flexWrap: "wrap", gap: "8px", marginBottom: "20px" },
  chip: { padding: "6px 12px", border: "1.5px solid #d1d5db", borderRadius: "99px", background: "#fff", fontSize: "17px", fontWeight: "600", color: "#8aa898", cursor: "pointer" },
  chipActive: { background: "#2d6a4f", borderColor: "#2d6a4f", color: "#fff" },
  card: { border: "1.5px solid #e5e7eb", borderRadius: "12px", marginBottom: "10px", overflow: "hidden" },
  cardHeader: { display: "flex", justifyContent: "space-between", alignItems: "center", padding: "14px 16px", cursor: "pointer", background: "#fff" },
  cardLeft: { flex: 1 },
  recipeName: { fontSize: "20px", fontWeight: "700", fontFamily: "'Nunito', sans-serif", color: "#1b3a2a", marginBottom: "2px" },
  recipeTiming: { fontSize: "17px", color: "#8aa898", marginBottom: "6px" },
  macroRow: { display: "flex", gap: "10px", flexWrap: "wrap" },
  macro: { fontSize: "17px", fontWeight: "600", color: "#2d6a4f", background: "#f0fdf4", padding: "2px 8px", borderRadius: "99px" },
  chevron: { fontSize: "17px", color: "#8aa898", marginLeft: "12px" },
  detail: { padding: "0 16px 16px", background: "#fafafa", borderTop: "1px solid #e5e7eb" },
  detailSection: { marginTop: "12px" },
  detailLabel: { fontSize: "16px", fontWeight: "700", color: "#8aa898", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "4px" },
  detailText: { fontSize: "18px", color: "#4a6358" },
  tagRow: { display: "flex", flexWrap: "wrap", gap: "6px" },
  tag: { fontSize: "16px", padding: "3px 8px", background: "#f0fdf4", color: "#2d6a4f", borderRadius: "99px", fontWeight: "600" },
  allergenTag: { fontSize: "16px", padding: "3px 8px", background: "#fef2f2", color: "#dc2626", borderRadius: "99px", fontWeight: "600" },
  swapBtn: { marginTop: "14px", padding: "8px 16px", background: "#fff", border: "1.5px solid #0f4c35", color: "#2d6a4f", borderRadius: "8px", fontSize: "18px", fontWeight: "600", cursor: "pointer", width: "100%" },
  swapResult: { marginTop: "14px", background: "#f0fdf4", border: "1.5px solid #bbf7d0", borderRadius: "8px", padding: "12px" },
  swapTitle: { fontSize: "17px", fontWeight: "700", color: "#2d6a4f", marginBottom: "6px" },
  swapName: { fontSize: "19px", fontWeight: "700", color: "#2d6a4f", marginBottom: "4px" },
  swapReason: { fontSize: "18px", color: "#4a6358", marginBottom: "4px" },
  empty: { textAlign: "center", color: "#8aa898", padding: "40px 0" },
  attribution: { fontSize: "16px", color: "#8aa898", textAlign: "center", marginTop: "20px" },
};
