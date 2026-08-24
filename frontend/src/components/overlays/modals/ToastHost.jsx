/** Shared toast overlay. */
export default function ToastHost() {
  return (
    <div id="toast" style={{ position: "fixed", bottom: "20px", right: "20px", zIndex: "50", display: "flex", flexDirection: "column", gap: "8px" }}></div>
  );
}
