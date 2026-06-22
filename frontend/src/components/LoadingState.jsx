export default function LoadingState({ message = "Loading…", subtle = false }) {
  return (
    <div style={subtle ? styles.inline : styles.center}>
      <div style={styles.spinner} />
      <p style={subtle ? styles.textInline : styles.text}>{message}</p>
    </div>
  );
}

const styles = {
  center: { display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "60px 20px", gap: "16px" },
  inline: { display: "flex", alignItems: "center", gap: "10px", padding: "8px 0" },
  spinner: { width: "40px", height: "40px", border: "3px solid #e5e7eb", borderTopColor: "#2d6a4f", borderRadius: "50%", animation: "spin 0.8s linear infinite", flexShrink: 0 },
  text: { color: "#4a6358", fontSize: "19px", margin: 0 },
  textInline: { color: "#4a6358", fontSize: "16px", margin: 0 },
};
