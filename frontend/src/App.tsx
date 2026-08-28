import { useEffect, useState } from "react";

import { ApiError, fetchAuthStatus, markVisited, randomResource, searchResources } from "./api/client";
import CollectionPanel from "./components/CollectionPanel";
import LoginGate from "./components/LoginGate";
import BrowsePage from "./pages/BrowsePage";
import CapturePage from "./pages/CapturePage";

type Tab = "browse" | "capture";

export default function App() {
  const [tab, setTab] = useState<Tab>("browse");
  const [authed, setAuthed] = useState<boolean | null>(null); // null = still checking

  useEffect(() => {
    (async () => {
      try {
        const { gate_enabled } = await fetchAuthStatus();
        if (!gate_enabled) return setAuthed(true);
        // Gate is on — probe a protected route to see if we already have a cookie.
        try {
          await searchResources({});
          setAuthed(true);
        } catch (e) {
          setAuthed(e instanceof ApiError && e.status === 401 ? false : true);
        }
      } catch {
        setAuthed(true); // if even the status check fails, don't hard-block the UI
      }
    })();
  }, []);
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

  if (authed === null) return <div style={{ padding: "2rem" }}>Loading…</div>;
  if (authed === false) return <LoginGate onAuthed={() => setAuthed(true)} />;

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
