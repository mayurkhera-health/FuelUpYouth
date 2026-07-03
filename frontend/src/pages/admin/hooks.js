import { useEffect, useState } from "react";

// Responsive helper: true when the viewport is narrower than `bp` (px). Shared
// by the shell + split views so breakpoints stay consistent. SSR-safe default.
export function useIsNarrow(bp = 768) {
  const [narrow, setNarrow] = useState(
    typeof window !== "undefined" && window.innerWidth < bp);
  useEffect(() => {
    const onResize = () => setNarrow(window.innerWidth < bp);
    onResize();
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, [bp]);
  return narrow;
}
