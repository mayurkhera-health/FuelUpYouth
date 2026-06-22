export default function ErrorState({ message = "Something went wrong.", onRetry }) {
  return (
    <div style={styles.center}>
      <p style={styles.text}>⚠ {message}</p>
      {onRetry && (
        <button style={styles.btn} onClick={onRetry}>Try again</button>
      )}
    </div>
  );
}

const styles = {
  center: { display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "40px 20px", gap: "14px" },
  text: { color: "#dc2626", fontSize: "18px", margin: 0, textAlign: "center" },
  btn: { background: "#2d6a4f", color: "#fff", border: "none", borderRadius: "10px", padding: "10px 18px", fontSize: "16px", fontWeight: "700", cursor: "pointer" },
};
