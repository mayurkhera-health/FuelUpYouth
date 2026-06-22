import { useState, useEffect } from "react";

/**
 * Cycles through `messages` every `intervalMs` while `active` is true.
 * Holds on the LAST message (never loops — looping implies a stall).
 * Resets to the first message when `active` becomes false.
 * A string or single-item array is returned as-is with no timer.
 */
export function useRotatingMessage(messages, { intervalMs = 2500, active = true } = {}) {
  const list = Array.isArray(messages) ? messages : [messages];
  const [index, setIndex] = useState(0);

  useEffect(() => {
    if (!active) { setIndex(0); return; }
    if (list.length <= 1) return;
    const id = setInterval(() => {
      setIndex((i) => (i < list.length - 1 ? i + 1 : i));
    }, intervalMs);
    return () => clearInterval(id);
  }, [active, intervalMs, list.length]);

  return list[Math.min(index, list.length - 1)];
}
