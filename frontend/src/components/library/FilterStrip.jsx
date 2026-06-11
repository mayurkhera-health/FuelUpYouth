import { useRef, useEffect } from "react";
import { FILTER_CHIPS } from "./categories";

export default function FilterStrip({ active, onChange }) {
  const stripRef = useRef(null);

  useEffect(() => {
    const strip = stripRef.current;
    if (!strip) return;
    const chip = strip.querySelector(`[data-key="${active}"]`);
    if (chip) {
      const { offsetLeft, offsetWidth } = chip;
      const { scrollLeft, clientWidth } = strip;
      if (offsetLeft < scrollLeft) {
        strip.scrollTo({ left: offsetLeft - 12, behavior: "smooth" });
      } else if (offsetLeft + offsetWidth > scrollLeft + clientWidth) {
        strip.scrollTo({ left: offsetLeft + offsetWidth - clientWidth + 12, behavior: "smooth" });
      }
    }
  }, [active]);

  return (
    <div ref={stripRef} style={s.strip}>
      {FILTER_CHIPS.map((chip) => {
        const isActive = chip.key === active;
        return (
          <button
            key={chip.key}
            data-key={chip.key}
            style={{
              ...s.chip,
              ...(isActive ? s.chipActive : {}),
            }}
            onClick={() => onChange(chip.key)}
          >
            {chip.label}
          </button>
        );
      })}
    </div>
  );
}

const s = {
  strip: {
    display: "flex",
    gap: "6px",
    overflowX: "auto",
    scrollbarWidth: "none",
    padding: "10px 0 9px",
    borderBottom: "1px solid #dce8e0",
    marginBottom: "18px",
    WebkitOverflowScrolling: "touch",
  },
  chip: {
    flexShrink: 0,
    padding: "5px 13px",
    borderRadius: "20px",
    border: "1px solid #dce8e0",
    background: "transparent",
    color: "#4a6358",
    fontSize: "11px",
    fontWeight: "500",
    fontFamily: "'Nunito', 'DM Sans', sans-serif",
    cursor: "pointer",
    transition: "border-color 0.12s, color 0.12s",
    whiteSpace: "nowrap",
  },
  chipActive: {
    background: "#2d6a4f",
    borderColor: "#2d6a4f",
    color: "#fff",
    fontWeight: "600",
  },
};
