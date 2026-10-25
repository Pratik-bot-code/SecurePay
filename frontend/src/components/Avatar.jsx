export default function Avatar({ name, color = "lavender", size = "normal" }) {
  const initials = name.split(" ").map((word) => word[0]).slice(0, 2).join("").toUpperCase();
  return <span className={`avatar avatar-${color} ${size === "large" ? "avatar-large" : ""}`} aria-label={name}>{initials}</span>;
}
