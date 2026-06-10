const API = import.meta.env.VITE_API_URL ?? "";

function urlBase64ToUint8Array(base64String) {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = atob(base64);
  return Uint8Array.from([...raw].map((c) => c.charCodeAt(0)));
}

export async function registerServiceWorker() {
  if (!("serviceWorker" in navigator) || !("PushManager" in window)) return null;
  const reg = await navigator.serviceWorker.register("/sw.js");
  await navigator.serviceWorker.ready;
  return reg;
}

export async function requestPermission() {
  if (!("Notification" in window)) return "unsupported";
  if (Notification.permission === "granted") return "granted";
  if (Notification.permission === "denied") return "denied";
  return await Notification.requestPermission();
}

export async function subscribePush(athleteId) {
  const reg = await registerServiceWorker();
  if (!reg) return false;

  const keyRes = await fetch(`${API}/api/notifications/vapid-public-key`);
  const { publicKey } = await keyRes.json();

  const sub = await reg.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(publicKey),
  });

  const json = sub.toJSON();
  await fetch(`${API}/api/notifications/subscribe`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      athlete_id: athleteId,
      endpoint: json.endpoint,
      p256dh: json.keys.p256dh,
      auth: json.keys.auth,
    }),
  });
  return true;
}

export async function unsubscribePush(athleteId) {
  const reg = await navigator.serviceWorker?.getRegistration();
  if (reg) {
    const sub = await reg.pushManager.getSubscription();
    if (sub) await sub.unsubscribe();
  }
  await fetch(`${API}/api/notifications/${athleteId}/unsubscribe`, { method: "DELETE" });
}

export async function getPrefs(athleteId) {
  const res = await fetch(`${API}/api/notifications/${athleteId}/prefs`);
  return res.ok ? res.json() : null;
}

export async function savePrefs(athleteId, prefs) {
  await fetch(`${API}/api/notifications/${athleteId}/prefs`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(prefs),
  });
}

export async function sendTestNotification(athleteId) {
  await fetch(`${API}/api/notifications/${athleteId}/send-daily`, { method: "POST" });
}
