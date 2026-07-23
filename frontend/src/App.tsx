import { HashRouter, Routes, Route } from "react-router-dom";
import Sidebar from "./components/Sidebar";
import ChatPage from "./pages/ChatPage";
import DocumentsPage from "./pages/DocumentsPage";
import ImagesPage from "./pages/ImagesPage";
import SearchPage from "./pages/SearchPage";
import ExplorerPage from "./pages/ExplorerPage";

export default function App() {
  return (
    <HashRouter>
      <div className="app-shell">
        <Sidebar />
        <main className="main-content">
          <Routes>
            <Route path="/" element={<ChatPage />} />
            <Route path="/documents" element={<DocumentsPage />} />
            <Route path="/images" element={<ImagesPage />} />
            <Route path="/search" element={<SearchPage />} />
            <Route path="/explorer" element={<ExplorerPage />} />
          </Routes>
        </main>
      </div>
    </HashRouter>
  );
}
