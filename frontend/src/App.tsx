import { useEffect, useState } from "react";

import { ApiError, fetchAuthStatus, markVisited, randomResource, searchResources } from "./api/client";
import CollectionPanel from "./components/CollectionPanel";
import { EMPTY_FILTERS, Filters } from "./components/FilterBar";
import LoginGate from "./components/LoginGate";
import BrowsePage from "./pages/BrowsePage";
import CapturePage from "./pages/CapturePage";
import DiscoverPage from "./pages/DiscoverPage";

type Tab = "browse" | "capture";
const DISCOVERED_KEY = "almanac.discovered";

function seenDiscover(): boolean {
  try {
    return localStorage.getItem(DISCOVERED_KEY) === "1";
  } catch {
    return false;
  }
}

export default function App() {
  const [tab, setTab] = useState<Tab>("browse");
  const [authed, setAuthed] = useState<boolean | null>(null); // null = still checking
  const [discovering, setDiscovering] = useState(!seenDiscover());
  const [browseFilters, setBrowseFilters] = useState<Filters>(EMPTY_FILTERS);
  const [browseKey, setBrowseKey] = useState(0);

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

  const leaveDiscover = (filters?: Filters) => {
    try {
      localStorage.setItem(DISCOVERED_KEY, "1");
    } catch {
      // fine — they'll just see it again next visit
    }
    if (filters) {
      setBrowseFilters(filters);
      setBrowseKey((k) => k + 1); // force BrowsePage to re-seed its filter state
    }
    setTab("browse");
    setDiscovering(false);
  };

  if (authed === null) return <div style={{ padding: "2rem" }}>Loading…</div>;
  if (authed === false) return <LoginGate onAuthed={() => setAuthed(true)} />;
  if (discovering)
    return <DiscoverPage onDone={(f) => leaveDiscover(f)} onSkip={() => leaveDiscover()} />;

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
            setDiscovering(true);
          }}
          title="Answer a few questions to narrow things down"
        >
          ✨ Guided
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
        <BrowsePage
          key={browseKey}
          initialFilters={browseFilters}
          onVisit={handleVisit}
          onFavoriteToggle={handleFavoriteToggle}
        />
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
