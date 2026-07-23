export default function Spinner({ label }: { label?: string }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10, color: "var(--text-secondary)", fontSize: 14 }}>
      <div className="spinner" />
      {label}
    </div>
  );
}
