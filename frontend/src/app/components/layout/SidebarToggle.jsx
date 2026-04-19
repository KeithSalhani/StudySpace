export default function SidebarToggle({ side, open, onClick, mobile = false, label }) {
  const buttonLabel = label || `${open ? "Hide" : "Open"} ${side} sidebar`;

  return (
    <button
      className={`sidebar-toggle ${mobile ? "mobile" : ""}`}
      type="button"
      onClick={onClick}
      aria-label={buttonLabel}
    >
      <span className="sidebar-toggle-icon">
        {side === "left" ? (open ? "←" : "→") : open ? "→" : "←"}
      </span>
      <span className="sidebar-toggle-label">{label || (open ? "Hide" : "Open")}</span>
    </button>
  );
}
