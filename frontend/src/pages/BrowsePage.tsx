import { useEffect, useState } from "react";

import {
  NameCount,
  Resource,
  UdlCoverage,
  fetchSubjects,
  fetchTags,
  fetchUdlCoverage,
  searchResources,
} from "../api/client";
import FilterBar, { EMPTY_FILTERS, Filters } from "../components/FilterBar";
import ResourceCard from "../components/ResourceCard";
import UdlCoverageStrip from "../components/UdlCoverageStrip";

type ViewMode = "grid" | "list" | "large";
const VIEW_STORAGE_KEY = "almanac.viewMode";

function loadViewMode(): ViewMode {
  try {
    const stored = localStorage.getItem(VIEW_STORAGE_KEY);
    if (stored === "grid" || stored === "list" || stored === "large") return stored;
  } catch {
    // ignore — falls through to default
  }
  return "grid";
}

export default function BrowsePage({
  initialFilters,
  onVisit,
  onFavoriteToggle,
}: {
  initialFilters?: Filters;
  onVisit: () => void;
  onFavoriteToggle: () => void;
}) {
  const [filters, setFilters] = useState<Filters>(() => ({
    ...EMPTY_FILTERS,
    ...initialFilters,
  }));
  const [resources, setResources] = useState<Resource[]>([]);
  const [total, setTotal] = useState(0);
  const [subjects, setSubjects] = useState<NameCount[]>([]);
  const [tags, setTags] = useState<NameCount[]>([]);
  const [coverage, setCoverage] = useState<UdlCoverage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [view, setView] = useState<ViewMode>(loadViewMode);

  const changeView = (next: ViewMode) => {
    setView(next);
    try {
      localStorage.setItem(VIEW_STORAGE_KEY, next);
    } catch {
      // ignore — per-viewer convenience only
    }
  };

  useEffect(() => {
    fetchSubjects().then(setSubjects).catch(() => {});
    fetchTags().then(setTags).catch(() => {});
  }, []);

  // A "theme search" is any query or theme filter — that's when the UDL
  // coverage strip is meaningful.
  const themeActive = filters.q.trim() !== "" || filters.tag !== "";

  useEffect(() => {
    setLoading(true);
    setError(null);
    const handle = setTimeout(() => {
      searchResources(filters)
        .then((res) => {
          setResources(res.items);
          setTotal(res.total);
        })
        .catch(() => setError("Couldn't reach the Almanac backend — is it running?"))
        .finally(() => setLoading(false));

      if (themeActive) {
        fetchUdlCoverage({
          q: filters.q,
          subject: filters.subject,
          grade_band: filters.grade_band,
          tag: filters.tag,
        })
          .then(setCoverage)
          .catch(() => setCoverage(null));
      } else {
        setCoverage(null);
      }
    }, 200); // debounce typing in the search box
    return () => clearTimeout(handle);
  }, [filters, themeActive]);

  return (
    <div>
      <FilterBar filters={filters} onChange={setFilters} subjects={subjects} tags={tags} />
      {error && <p style={{ color: "crimson" }}>{error}</p>}
      {!error && (
        <>
          {coverage && (
            <UdlCoverageStrip
              coverage={coverage}
              active={filters.udl}
              onPick={(principle) => setFilters((f) => ({ ...f, udl: principle }))}
            />
          )}
          <div className="results-row">
            <p>{loading ? "Loading…" : `${total} result${total === 1 ? "" : "s"}`}</p>
            <div className="view-toggle" role="group" aria-label="View">
              <button
                className={view === "list" ? "active" : ""}
                onClick={() => changeView("list")}
                title="List view"
                aria-pressed={view === "list"}
              >
                ☰
              </button>
              <button
                className={view === "grid" ? "active" : ""}
                onClick={() => changeView("grid")}
                title="Grid view"
                aria-pressed={view === "grid"}
              >
                ▦
              </button>
              <button
                className={view === "large" ? "active" : ""}
                onClick={() => changeView("large")}
                title="Large panels"
                aria-pressed={view === "large"}
              >
                ▢
              </button>
            </div>
          </div>
          <div className={`entries-grid view-${view}`}>
            {resources.map((r) => (
              <ResourceCard
                key={r.id}
                resource={r}
                view={view}
                onVisit={onVisit}
                onFavoriteToggle={onFavoriteToggle}
              />
            ))}
          </div>
          {!loading && resources.length === 0 && (
            <p>No resources match — try a broader theme or clear a filter.</p>
          )}
        </>
      )}
    </div>
  );
}
