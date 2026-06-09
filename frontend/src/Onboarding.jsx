import { useState } from "react";

const API = "http://localhost:8000";

const CONSENT_TEXT = `I confirm my athlete is between 9 and 17 years of age.

I understand FuelUp is an educational food guidance tool — NOT medical nutrition therapy.

All recommendations are based on published pediatric sports nutrition research, including Everett MD 2025, AAP guidelines, and Boston Children's Hospital RDN recommendations.

FuelUp collects the athlete's name, age, gender, height, weight, food allergies, dietary restrictions, and game schedule for the sole purpose of generating personalized nutrition guidance.

This data is never sold or shared with third parties. It is used only to deliver FuelUp's nutrition guidance service.

I can request complete data deletion at any time by emailing purvi@dietsandlife.com.

I will consult my child's physician or a licensed Registered Dietitian Nutritionist for any medical nutrition concerns.`;

const SUPPLEMENT_WARNINGS = {
  "protein powder": "⚠️ Protein powder is not recommended for adolescent athletes. Whole food protein sources are superior. (Boston Children's Hospital RDN)",
  creatine: "⚠️ Creatine is NOT approved for athletes under 18. (Boston Children's Hospital RDN)",
  "energy drink": "⚠️ Energy drinks contain caffeine levels dangerous for adolescents and are linked to cardiac events in youth. (Boston Children's Hospital RDN, AAP)",
};

const STEPS = ["Age Check", "Parent Consent", "Athlete Profile", "All Set!"];

const initialParent = { full_name: "", email: "", consent_confirmed: false };
const initialAthlete = {
  first_name: "", age: "", gender: "", weight_lbs: "",
  height_ft: "", height_in: "", position: "", competition_level: "",
  sweat_profile: "", allergies: [], dietary_restrictions: "", supplement_use: [],
};

export default function Onboarding({ onComplete }) {
  const [step, setStep] = useState(0);
  const [athleteAge, setAthleteAge] = useState("");
  const [ageError, setAgeError] = useState("");
  const [parent, setParent] = useState(initialParent);
  const [athlete, setAthlete] = useState(initialAthlete);
  const [parentId, setParentId] = useState(null);
  const [athleteId, setAthleteId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // ── Step 0: Age Gate ────────────────────────────────────────────────────────
  function handleAgeCheck() {
    const age = parseInt(athleteAge);
    if (!age) return setAgeError("Please enter the athlete's age.");
    if (age < 9) return setAgeError("FuelUp is designed for youth athletes ages 9–17. Please consult your child's physician for nutrition guidance.");
    if (age > 17) return setAgeError("FuelUp is designed for youth athletes ages 9–17. For athletes 18+, we recommend consulting a CSSD-credentialed sports dietitian.");
    setAgeError("");
    setAthlete((a) => ({ ...a, age }));
    setStep(1);
  }

  // ── Step 1: Parent Consent ──────────────────────────────────────────────────
  async function handleParentSubmit(e) {
    e.preventDefault();
    if (!parent.consent_confirmed) return setError("You must read and accept the consent agreement to continue.");
    setLoading(true);
    setError("");
    try {
      const isTest = parent.email?.trim().toLowerCase() === "test@gmail.com";
      if (isTest) {
        await fetch(`${API}/api/parents/test-reset?email=test@gmail.com`, { method: "DELETE" });
      }
      const res = await fetch(`${API}/api/parents/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(parent),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to create account.");
      setParentId(data.id);
      setStep(2);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  // ── Step 2: Athlete Profile ─────────────────────────────────────────────────
  async function handleAthleteSubmit(e) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const payload = {
        ...athlete,
        parent_id: parentId,
        age: parseInt(athlete.age),
        weight_lbs: parseFloat(athlete.weight_lbs),
        height_ft: parseInt(athlete.height_ft),
        height_in: parseFloat(athlete.height_in),
        allergies: athlete.allergies.join(", ") || "None",
        supplement_use: athlete.supplement_use.join(", ") || "None",
      };
      const res = await fetch(`${API}/api/athletes/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to create athlete profile.");
      setAthleteId(data.id);
      setStep(3);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  function toggleCheckbox(field, value) {
    setAthlete((a) => ({
      ...a,
      [field]: a[field].includes(value)
        ? a[field].filter((v) => v !== value)
        : [...a[field], value],
    }));
  }

  const supplementWarnings = athlete.supplement_use
    .map((s) => SUPPLEMENT_WARNINGS[s.toLowerCase()])
    .filter(Boolean);

  return (
    <div style={styles.wrapper}>
      <div style={styles.card}>
        {/* Header */}
        <div style={styles.header}>
          <div style={styles.logo}>⚽ FuelUp</div>
          <div style={styles.subtitle}>Youth Soccer Nutrition Platform</div>
        </div>

        {/* Progress bar */}
        <div style={styles.progressBar}>
          {STEPS.map((label, i) => (
            <div key={i} style={styles.stepItem}>
              <div style={{ ...styles.stepDot, ...(i <= step ? styles.stepDotActive : {}) }}>
                {i < step ? "✓" : i + 1}
              </div>
              <div style={{ ...styles.stepLabel, ...(i <= step ? styles.stepLabelActive : {}) }}>
                {label}
              </div>
            </div>
          ))}
        </div>

        {error && <div style={styles.errorBanner}>{error}</div>}

        {/* ── Step 0: Age Gate ── */}
        {step === 0 && (
          <div style={styles.section}>
            <h2 style={styles.sectionTitle}>Welcome to FuelUp!</h2>
            <p style={styles.sectionDesc}>
              Before we begin, please confirm your athlete's age. FuelUp is built exclusively for youth athletes ages 9–17.
            </p>
            <label style={styles.label}>Athlete's Age</label>
            <input
              style={styles.input}
              type="number"
              min="1"
              max="25"
              placeholder="Enter athlete's age"
              value={athleteAge}
              onChange={(e) => setAthleteAge(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleAgeCheck()}
            />
            {ageError && <div style={styles.fieldError}>{ageError}</div>}
            <button style={styles.btn} onClick={handleAgeCheck}>
              Continue →
            </button>
            <p style={styles.disclaimer}>
              FuelUp provides educational food guidance — not medical nutrition therapy.
            </p>
          </div>
        )}

        {/* ── Step 1: Parent Consent ── */}
        {step === 1 && (
          <form onSubmit={handleParentSubmit} style={styles.section}>
            <h2 style={styles.sectionTitle}>Parent Account + Consent</h2>
            <p style={styles.sectionDesc}>
              Parents create an account first. This protects your family legally and ensures we follow COPPA and California privacy law.
            </p>

            <label style={styles.label}>Parent Full Name <span style={styles.req}>*</span></label>
            <input
              style={styles.input}
              type="text"
              placeholder="Your full name (acts as digital signature)"
              value={parent.full_name}
              onChange={(e) => setParent({ ...parent, full_name: e.target.value })}
              required
            />

            <label style={styles.label}>Parent Email <span style={styles.req}>*</span></label>
            <input
              style={styles.input}
              type="email"
              placeholder="your@email.com"
              value={parent.email}
              onChange={(e) => setParent({ ...parent, email: e.target.value })}
              required
            />

            <label style={styles.label}>Parental Consent Agreement <span style={styles.req}>*</span></label>
            <div style={styles.consentBox}>
              {CONSENT_TEXT.split("\n\n").map((para, i) => (
                <p key={i} style={styles.consentPara}>{para}</p>
              ))}
            </div>

            <label style={styles.checkboxRow}>
              <input
                type="checkbox"
                checked={parent.consent_confirmed}
                onChange={(e) => setParent({ ...parent, consent_confirmed: e.target.checked })}
                style={styles.checkbox}
              />
              <span>I have read and agree to all of the above consent terms.</span>
            </label>

            <button style={styles.btn} type="submit" disabled={loading}>
              {loading ? "Creating Account…" : "Create Account →"}
            </button>
          </form>
        )}

        {/* ── Step 2: Athlete Profile ── */}
        {step === 2 && (
          <form onSubmit={handleAthleteSubmit} style={styles.section}>
            <h2 style={styles.sectionTitle}>Athlete Profile</h2>
            <p style={styles.sectionDesc}>
              We collect only what's scientifically necessary to calculate personalized pediatric nutrition targets.
            </p>

            <div style={styles.row}>
              <div style={styles.col}>
                <label style={styles.label}>First Name <span style={styles.req}>*</span></label>
                <input style={styles.input} type="text" placeholder="Athlete's first name" value={athlete.first_name}
                  onChange={(e) => setAthlete({ ...athlete, first_name: e.target.value })} required />
              </div>
              <div style={styles.col}>
                <label style={styles.label}>Age <span style={styles.req}>*</span></label>
                <input style={styles.input} type="number" value={athlete.age} readOnly />
              </div>
            </div>

            <label style={styles.label}>Gender <span style={styles.req}>*</span></label>
            <select style={styles.select} value={athlete.gender}
              onChange={(e) => setAthlete({ ...athlete, gender: e.target.value })} required>
              <option value="">Select gender</option>
              <option value="Girl">Girl</option>
              <option value="Boy">Boy</option>
              <option value="Prefer not to say">Prefer not to say</option>
            </select>
            {athlete.gender === "Girl" && (
              <div style={styles.infoNote}>Iron target: 15mg/day — 52% of female adolescent athletes are iron deficient (Everett MD 2025)</div>
            )}

            <div style={styles.row}>
              <div style={styles.col}>
                <label style={styles.label}>Weight (lbs) <span style={styles.req}>*</span></label>
                <input style={styles.input} type="number" step="0.1" placeholder="e.g. 130" value={athlete.weight_lbs}
                  onChange={(e) => setAthlete({ ...athlete, weight_lbs: e.target.value })} required />
              </div>
              <div style={styles.col}>
                <label style={styles.label}>Height (ft) <span style={styles.req}>*</span></label>
                <input style={styles.input} type="number" placeholder="5" value={athlete.height_ft}
                  onChange={(e) => setAthlete({ ...athlete, height_ft: e.target.value })} required />
              </div>
              <div style={styles.col}>
                <label style={styles.label}>Height (in) <span style={styles.req}>*</span></label>
                <input style={styles.input} type="number" step="0.5" placeholder="4" value={athlete.height_in}
                  onChange={(e) => setAthlete({ ...athlete, height_in: e.target.value })} required />
              </div>
            </div>

            <div style={styles.row}>
              <div style={styles.col}>
                <label style={styles.label}>Soccer Position</label>
                <select style={styles.select} value={athlete.position}
                  onChange={(e) => setAthlete({ ...athlete, position: e.target.value })}>
                  <option value="">Select position</option>
                  <option>Goalkeeper</option>
                  <option>Defender</option>
                  <option>Midfielder</option>
                  <option>Forward</option>
                </select>
              </div>
              <div style={styles.col}>
                <label style={styles.label}>Competition Level</label>
                <select style={styles.select} value={athlete.competition_level}
                  onChange={(e) => setAthlete({ ...athlete, competition_level: e.target.value })}>
                  <option value="">Select level</option>
                  <option>Recreational</option>
                  <option>Club</option>
                  <option>Competitive</option>
                  <option>Elite</option>
                </select>
              </div>
            </div>

            <label style={styles.label}>Sweat Profile</label>
            <select style={styles.select} value={athlete.sweat_profile}
              onChange={(e) => setAthlete({ ...athlete, sweat_profile: e.target.value })}>
              <option value="">How much does your athlete sweat?</option>
              <option value="Light">Light — barely visible</option>
              <option value="Moderate">Moderate — noticeable</option>
              <option value="Heavy">Heavy — drips during activity</option>
              <option value="Very Heavy">Very Heavy — drenched every session</option>
            </select>

            <label style={styles.label}>Food Allergies (select all that apply)</label>
            <div style={styles.checkGroup}>
              {["None", "Peanuts", "Tree nuts", "Dairy", "Eggs", "Gluten", "Soy", "Shellfish"].map((a) => (
                <label key={a} style={styles.checkboxRow}>
                  <input type="checkbox" checked={athlete.allergies.includes(a)}
                    onChange={() => toggleCheckbox("allergies", a)} style={styles.checkbox} />
                  <span>{a}</span>
                </label>
              ))}
            </div>

            <label style={styles.label}>Dietary Restrictions</label>
            <select style={styles.select} value={athlete.dietary_restrictions}
              onChange={(e) => setAthlete({ ...athlete, dietary_restrictions: e.target.value })}>
              <option value="">Select restriction</option>
              <option>No restrictions</option>
              <option>Vegetarian</option>
              <option>Vegan</option>
              <option>Halal</option>
              <option>Gluten-free</option>
            </select>

            <label style={styles.label}>Supplement Use (select all that apply)</label>
            <div style={styles.checkGroup}>
              {["None", "Protein powder", "Creatine", "Iron", "Vitamin D", "Energy drink"].map((s) => (
                <label key={s} style={styles.checkboxRow}>
                  <input type="checkbox" checked={athlete.supplement_use.includes(s)}
                    onChange={() => toggleCheckbox("supplement_use", s)} style={styles.checkbox} />
                  <span>{s}</span>
                </label>
              ))}
            </div>
            {supplementWarnings.length > 0 && (
              <div style={styles.warningBox}>
                <strong>Safety Notice from Boston Children's Hospital RDN:</strong>
                {supplementWarnings.map((w, i) => <p key={i} style={{ margin: "4px 0" }}>{w}</p>)}
              </div>
            )}

            <button style={styles.btn} type="submit" disabled={loading}>
              {loading ? "Saving Profile…" : "Complete Setup →"}
            </button>
          </form>
        )}

        {/* ── Step 3: Success ── */}
        {step === 3 && (
          <div style={{ ...styles.section, textAlign: "center" }}>
            <div style={styles.successIcon}>🏆</div>
            <h2 style={styles.sectionTitle}>Welcome to FuelUp!</h2>
            <p style={styles.sectionDesc}>
              Your athlete's profile is set up. FuelUp will now generate science-backed, personalized nutrition targets based on their training schedule every single day.
            </p>
            <div style={styles.summaryBox}>
              <div style={styles.summaryRow}><span>Parent ID</span><strong>#{parentId}</strong></div>
              <div style={styles.summaryRow}><span>Athlete ID</span><strong>#{athleteId}</strong></div>
              <div style={styles.summaryRow}><span>Next step</span><strong>Add your schedule →</strong></div>
            </div>
            <p style={styles.scienceNote}>
              Targets calculated using Everett MD 2025 · Boston Children's Hospital RDN · AAP guidelines
            </p>
            {onComplete && (
              <button style={styles.btn} onClick={() => onComplete({ parentId, athleteId })}>
                Add Training Schedule →
              </button>
            )}
            <p style={styles.disclaimer}>
              FuelUp provides educational food guidance — not medical nutrition therapy. Consult your child's physician for medical concerns.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

const styles = {
  wrapper: { minHeight: "100vh", background: "linear-gradient(135deg, #0f4c35 0%, #1a7a54 100%)", display: "flex", alignItems: "center", justifyContent: "center", padding: "20px", fontFamily: "'Inter', -apple-system, sans-serif" },
  card: { background: "#fff", borderRadius: "20px", padding: "40px", width: "100%", maxWidth: "600px", boxShadow: "0 24px 60px rgba(0,0,0,0.25)" },
  header: { textAlign: "center", marginBottom: "28px" },
  logo: { fontSize: "28px", fontWeight: "800", color: "#0f4c35" },
  subtitle: { fontSize: "14px", color: "#6b7280", marginTop: "4px" },
  progressBar: { display: "flex", justifyContent: "space-between", marginBottom: "32px", position: "relative" },
  stepItem: { display: "flex", flexDirection: "column", alignItems: "center", flex: 1 },
  stepDot: { width: "32px", height: "32px", borderRadius: "50%", background: "#e5e7eb", color: "#9ca3af", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "13px", fontWeight: "700", marginBottom: "6px" },
  stepDotActive: { background: "#0f4c35", color: "#fff" },
  stepLabel: { fontSize: "11px", color: "#9ca3af", textAlign: "center" },
  stepLabelActive: { color: "#0f4c35", fontWeight: "600" },
  section: { display: "flex", flexDirection: "column", gap: "16px" },
  sectionTitle: { fontSize: "22px", fontWeight: "700", color: "#111827", margin: 0 },
  sectionDesc: { fontSize: "14px", color: "#6b7280", lineHeight: "1.5", margin: 0 },
  label: { fontSize: "13px", fontWeight: "600", color: "#374151" },
  req: { color: "#ef4444" },
  input: { padding: "10px 14px", border: "1.5px solid #d1d5db", borderRadius: "8px", fontSize: "15px", outline: "none", width: "100%", boxSizing: "border-box" },
  select: { padding: "10px 14px", border: "1.5px solid #d1d5db", borderRadius: "8px", fontSize: "15px", background: "#fff", width: "100%", boxSizing: "border-box" },
  row: { display: "flex", gap: "12px" },
  col: { display: "flex", flexDirection: "column", flex: 1, gap: "6px" },
  consentBox: { background: "#f9fafb", border: "1.5px solid #e5e7eb", borderRadius: "8px", padding: "16px", maxHeight: "200px", overflowY: "auto", fontSize: "13px", lineHeight: "1.6", color: "#374151" },
  consentPara: { margin: "0 0 10px 0" },
  checkboxRow: { display: "flex", alignItems: "flex-start", gap: "10px", fontSize: "14px", color: "#374151", cursor: "pointer" },
  checkbox: { marginTop: "2px", accentColor: "#0f4c35", width: "16px", height: "16px", flexShrink: 0 },
  checkGroup: { display: "flex", flexDirection: "column", gap: "8px", padding: "12px", background: "#f9fafb", borderRadius: "8px", border: "1.5px solid #e5e7eb" },
  btn: { background: "#0f4c35", color: "#fff", border: "none", borderRadius: "10px", padding: "14px 24px", fontSize: "16px", fontWeight: "700", cursor: "pointer", marginTop: "8px" },
  errorBanner: { background: "#fef2f2", border: "1.5px solid #fecaca", borderRadius: "8px", padding: "12px 16px", color: "#dc2626", fontSize: "14px", marginBottom: "8px" },
  fieldError: { color: "#dc2626", fontSize: "13px", marginTop: "-8px" },
  infoNote: { background: "#f0fdf4", border: "1.5px solid #bbf7d0", borderRadius: "8px", padding: "10px 14px", fontSize: "13px", color: "#166534" },
  warningBox: { background: "#fffbeb", border: "1.5px solid #fde68a", borderRadius: "8px", padding: "14px 16px", fontSize: "13px", color: "#92400e", lineHeight: "1.5" },
  successIcon: { fontSize: "56px", marginBottom: "8px" },
  summaryBox: { background: "#f0fdf4", border: "1.5px solid #bbf7d0", borderRadius: "12px", padding: "20px", display: "flex", flexDirection: "column", gap: "10px" },
  summaryRow: { display: "flex", justifyContent: "space-between", fontSize: "14px", color: "#374151" },
  scienceNote: { fontSize: "12px", color: "#9ca3af" },
  disclaimer: { fontSize: "12px", color: "#9ca3af", textAlign: "center", lineHeight: "1.5" },
};
