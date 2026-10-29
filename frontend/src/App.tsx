import { useEffect, useState } from "react";

import { ApiError, fetchAuthStatus, markVisited, randomResource, searchResources } from "./api/client";
import { EMPTY_FILTERS, Filters } from "./components/FilterBar";
import LoginGate from "./components/LoginGate";
import BrowsePage from "./pages/BrowsePage";
import CapturePage from "./pages/CapturePage";
import DiscoverPage from "./pages/DiscoverPage";
import LessonStudioPage from "./pages/LessonStudioPage";
import StatsPage from "./pages/StatsPage";

type Tab = "browse" | "studio" | "capture" | "stats";
const DISCOVERED_KEY = "almanac.discovered";

const DISPLAY_KEY = "almanac.display";

// Display options a reader can switch on: a high-contrast palette and a
// dyslexia-friendly typeface with looser spacing. Both are off by default.
type Display = { contrast: boolean; dyslexiaFont: boolean };
const DISPLAY_OFF: Display = { contrast: false, dyslexiaFont: false };

function loadDisplay(): Display {
  try {
    return { ...DISPLAY_OFF, ...JSON.parse(localStorage.getItem(DISPLAY_KEY) ?? "{}") };
  } catch {
    return DISPLAY_OFF;
  }
}

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
  const [display, setDisplay] = useState<Display>(loadDisplay);

  // The CSS in index.css reads these two attributes on <html>.
  useEffect(() => {
    const root = document.documentElement;
    root.dataset.contrast = display.contrast ? "high" : "";
    root.dataset.font = display.dyslexiaFont ? "dyslexia" : "";
    try {
      localStorage.setItem(DISPLAY_KEY, JSON.stringify(display));
    } catch {
      // fine — the choice just won't be remembered
    }
  }, [display]);

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
  const [rolling, setRolling] = useState(false);

  const handleSurpriseMe = async () => {
    setRolling(true);
    try {
      const r = await randomResource();
      window.open(r.link, "_blank", "noopener,noreferrer");
      markVisited(r.id).catch(() => {});
    } catch {
      // Silent — a failed roll just means "try again".
    } finally {
      setRolling(false);
    }
  };

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
    <div className="app-shell almanac-shell">
      <header className="app-header">
        <a className="brand-lockup" href="#" onClick={(e) => { e.preventDefault(); setTab("browse"); }} aria-label="Almanac home">
          <span className="brand-mark" aria-hidden="true">A</span>
          <span className="brand-name">almanac<span className="brand-period">.</span><small>TEACHING LIBRARY</small></span>
        </a>
        <div className="header-note"><span className="status-dot" /> A growing library for thoughtful teaching</div>
        <div className="display-toggles" role="group" aria-label="Display options">
          <button
            type="button"
            aria-pressed={display.contrast}
            onClick={() => setDisplay((d) => ({ ...d, contrast: !d.contrast }))}
          >
            High contrast
          </button>
          <button
            type="button"
            aria-pressed={display.dyslexiaFont}
            onClick={() => setDisplay((d) => ({ ...d, dyslexiaFont: !d.dyslexiaFont }))}
          >
            Dyslexia-friendly font
          </button>
        </div>
      </header>
      <section className="welcome-hero">
        <div className="hero-copy">
          <p className="eyebrow">PLAN WITH MORE POSSIBILITY</p>
          <h1>Good teaching starts<br />with <em>good options.</em></h1>
          <p className="tagline">Find lessons, activities, and courses that meet learners where they are — and bring every UDL principle into view.</p>
        </div>
        <div className="hero-art" aria-hidden="true"><span className="orbit orbit-one"/><span className="orbit orbit-two"/><span className="orbit-core">✳</span><span className="orbit-label orbit-label-one">ENGAGE</span><span className="orbit-label orbit-label-two">EXPLORE</span><span className="orbit-label orbit-label-three">EXPRESS</span></div>
      </section>
      <nav className="app-nav">
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
            setTab("studio");
          }}
          style={{ opacity: tab === "studio" ? 1 : 0.5 }}
          title="Adapt a lesson with UDL moves"
        >
          Lesson Studio
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
            setTab("stats");
          }}
          style={{ opacity: tab === "stats" ? 1 : 0.5 }}
          title="Where the library itself is thin"
        >
          📊 Stats
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
          className="nav-push"
          style={{ opacity: rolling ? 0.5 : 1 }}
          title="Open a random resource from the whole library"
        >
          🎲 Surprise me
        </a>
      </nav>
      {tab === "browse" && (
        <BrowsePage
          key={browseKey}
          initialFilters={browseFilters}
        />
      )}
      {tab === "studio" && <LessonStudioPage />}
      {tab === "capture" && <CapturePage />}
      {tab === "stats" && <StatsPage />}
    </div>
  );
}
