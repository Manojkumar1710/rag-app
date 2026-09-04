import { NavLink } from "react-router-dom";
import { MessageSquare, FileUp, Image as ImageIcon, Search, Database, Sparkles } from "lucide-react";

const links = [
  { to: "/", label: "Chat", icon: MessageSquare },
  { to: "/documents", label: "Documents", icon: FileUp },
  { to: "/images", label: "Image Upload", icon: ImageIcon },
  { to: "/search", label: "Semantic Search", icon: Search },
  { to: "/explorer", label: "Indexed Explorer", icon: Database },
];

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <Sparkles size={20} color="var(--accent)" />
        RAG Studio
      </div>
      <nav className="sidebar-nav">
        {links.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) => `sidebar-link${isActive ? " active" : ""}`}
          >
            <Icon size={16} />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}