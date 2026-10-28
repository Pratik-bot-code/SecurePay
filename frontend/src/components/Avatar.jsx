export default function Avatar({ name = "User", handle, color, size = "normal" }) {
  const safeName = String(name || "User").trim();
  const initials = safeName
    ? safeName.split(" ").filter(Boolean).map((word) => word[0]).slice(0, 2).join("").toUpperCase()
    : "SP";

  // Deterministic color assignment based on name or handle if color not specified
  const colors = ["teal", "lavender", "peach", "mint", "blue", "yellow"];
  const seed = (handle || safeName).split("").reduce((acc, char) => acc + char.charCodeAt(0), 0);
  const resolvedColor = color || colors[seed % colors.length];

  const isNumericSize = typeof size === "number";
  const inlineStyle = isNumericSize
    ? { width: `${size}px`, height: `${size}px`, minWidth: `${size}px`, fontSize: `${Math.round(size * 0.42)}px` }
    : undefined;

  const sizeClass = !isNumericSize && size === "large" ? "avatar-large" : "";

  return (
    <span
      className={`avatar avatar-${resolvedColor} ${sizeClass}`}
      style={inlineStyle}
      aria-label={safeName}
    >
      {initials}
    </span>
  );
}
