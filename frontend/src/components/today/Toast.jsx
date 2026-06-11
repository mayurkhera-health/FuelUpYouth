import { useState, useCallback } from "react";

export function useToast() {
  const [message, setMessage] = useState(null);

  const showToast = useCallback((msg) => {
    setMessage(msg);
    setTimeout(() => setMessage(null), 2200);
  }, []);

  return { message, showToast };
}

export default function Toast({ message }) {
  const visible = !!message;
  return (
    <div style={{
      ...s.toast,
      opacity: visible ? 1 : 0,
      transform: visible ? "translateX(-50%) translateY(0)" : "translateX(-50%) translateY(6px)",
      pointerEvents: visible ? "auto" : "none",
    }}>
      {message}
    </div>
  );
}

const s = {
  toast: {
    position: "fixed",
    bottom: "80px",
    left: "50%",
    transform: "translateX(-50%)",
    background: "#2d6a4f",
    color: "#d4ead8",
    fontFamily: "'Nunito', sans-serif",
    fontSize: "13px",
    fontWeight: "700",
    padding: "10px 20px",
    borderRadius: "8px",
    whiteSpace: "nowrap",
    zIndex: 50,
    transition: "opacity 0.22s, transform 0.22s",
  },
};
