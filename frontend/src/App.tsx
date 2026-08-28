import { useState } from "react";

import { markVisited, randomResource } from "./api/client";
import CollectionPanel from "./components/CollectionPanel";
import BrowsePage from "./pages/BrowsePage";
import CapturePage from "./pages/CapturePage";

type Tab = "browse" | "capture";

export default function App() {
  const [tab, setTab] = useState<Tab>("browse");
  const [collectionOpen, setCollectionOpen] = useState(false);
  const [collectionRefreshKey, setCollectionRefreshKey] = useState(0);
  const [hasAutoOpened, setHasAutoOpened] = useState(false);
  const [rolling, setRolling] = useState(false);

  const handleSurpriseMe = async () => {
    setRolling(true);
    try {
      const r = await randomResource();
      window.open(r.link, "_blank", "noopener,noreferrer");
      markVisited(r.id).catch(() => {});
      handleVisit();
    } catch {
      // Silent — a failed roll just means "try again".
    } finally {
      setRolling(false);
    }
  };

  const handleVisit = () => {
    if (!hasAutoOpened) {
      setCollectionOpen(true);
      setHasAutoOpened(true);
    }
  };

  const handleFavoriteToggle = () => setCollectionRefreshKey((k) => k + 1);

  return (
    <div>
      <h1>Almanac</h1>
      <p className="tagline">
        Search a theme, get teaching content for it — with every UDL principle in view.
      </p>
      <nav>
        <a
          href="#"
          onClick={(e) => {
            e.preventDefault();
            setTab("browse");
          }}
          style={{ opacity: tab === "browse" ? 1 : 0.5 }}
        >
          Browse
        </a>
        <a
          href="#"
          onClick={(e) => {
            e.preventDefault();
            setTab("capture");
          }}
          style={{ opacity: tab === "capture" ? 1 : 0.5 }}
        >
          Capture
        </a>
        <a
          href="#"
          onClick={(e) => {
            e.preventDefault();
            if (!rolling) handleSurpriseMe();
          }}
          style={{ marginLeft: "auto", opacity: rolling ? 0.5 : 1 }}
          title="Open a random resource from the whole library"
        >
          🎲 Surprise me
        </a>
        <a
          href="#"
          onClick={(e) => {
            e.preventDefault();
            setCollectionOpen((v) => !v);
          }}
          style={{ opacity: collectionOpen ? 1 : 0.5 }}
        >
          ★ My Collection
        </a>
      </nav>
      {tab === "browse" ? (
        <BrowsePage onVisit={handleVisit} onFavoriteToggle={handleFavoriteToggle} />
      ) : (
        <CapturePage />
      )}
      <CollectionPanel
        open={collectionOpen}
        onClose={() => setCollectionOpen(false)}
        refreshKey={collectionRefreshKey}
      />
    </div>
  );
}
