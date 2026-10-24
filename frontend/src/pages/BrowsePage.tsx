import { useCallback, useEffect, useRef, useState } from "react";

import {
  NameCount,
  Resource,
  UdlCoverage,
  fetchAudiences,
  fetchStandards,
  fetchSubjects,
  fetchTags,
  fetchUdlCoverage,
  searchResources,
} from "../api/client";
import FilterBar, { EMPTY_FILTERS, Filters, toQuery } from "../components/FilterBar";
import ResourceCard from "../components/ResourceCard";
import UdlCoverageStrip from "../components/UdlCoverageStrip";

type ViewMode = "grid" | "list" | "large";
const VIEW_STORAGE_KEY = "almanac.viewMode";
// Results arrive a page at a time as the user scrolls. The API used to hand
// back a silent 50 and stop, so "385 results" rendered 50 cards.
const PAGE_SIZE = 60;

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
}: {
  initialFilters?: Filters;
}) {
  const [filters, setFilters] = useState<Filters>(() => ({
    ...EMPTY_FILTERS,
    ...initialFilters,
  }));
  const [resources, setResources] = useState<Resource[]>([]);
  const [total, setTotal] = useState(0);
  const [unmatched, setUnmatched] = useState<string[]>([]);
  const [subjects, setSubjects] = useState<NameCount[]>([]);
  const [tags, setTags] = useState<NameCount[]>([]);
  const [standards, setStandards] = useState<NameCount[]>([]);
  const [audiences, setAudiences] = useState<NameCount[]>([]);
  const [coverage, setCoverage] = useState<UdlCoverage | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [view, setView] = useState<ViewMode>(loadViewMode);
  // Bumped on every new search so a slow page from the previous search can't
  // land on top of the new results.
  const generation = useRef(0);
  const sentinel = useRef<HTMLDivElement | null>(null);

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
    fetchStandards().then(setStandards).catch(() => {});
    fetchAudiences().then(setAudiences).catch(() => {});
  }, []);

  const lessonMode = filters.audience === "students";
  // A "theme search" is any query or theme filter — that's when the UDL
  // coverage strip is meaningful. It's a lesson-planning readout, so it
  // stays off in professional learning.
  const themeActive = lessonMode && (filters.q.trim() !== "" || filters.tag !== "");

  useEffect(() => {
    const mine = ++generation.current;
    setLoading(true);
    setError(null);
    const handle = setTimeout(() => {
      searchResources({ ...toQuery(filters), limit: PAGE_SIZE, offset: 0 })
        .then((res) => {
          if (mine !== generation.current) return;
          setResources(res.items);
          setTotal(res.total);
          setUnmatched(res.unmatched_terms ?? []);
        })
        .catch(() => {
          if (mine === generation.current) {
            setError("Couldn't reach the Almanac backend — is it running?");
          }
        })
        .finally(() => {
          if (mine === generation.current) setLoading(false);
        });

      if (themeActive) {
        fetchUdlCoverage({
          q: filters.q,
          subject: filters.subject,
          grade_band: filters.grade_band,
          tag: filters.tag,
          audience: filters.audience,
        })
          .then((c) => mine === generation.current && setCoverage(c))
          .catch(() => setCoverage(null));
      } else {
        setCoverage(null);
      }
    }, 200); // debounce typing in the search box
    return () => clearTimeout(handle);
  }, [filters, themeActive]);

  const hasMore = !loading && resources.length < total;

  const loadMore = useCallback(() => {
    if (!hasMore || loadingMore) return;
    const mine = generation.current;
    setLoadingMore(true);
    searchResources({ ...toQuery(filters), limit: PAGE_SIZE, offset: resources.length })
      .then((res) => {
        if (mine !== generation.current) return;
        setResources((prev) => {
          const seen = new Set(prev.map((r) => r.id));
          return [...prev, ...res.items.filter((r) => !seen.has(r.id))];
        });
        setTotal(res.total);
      })
      .catch(() => {})
      .finally(() => setLoadingMore(false));
  }, [filters, hasMore, loadingMore, resources.length]);

  // Fetch the next page when the end of the list scrolls into view. The
  // button below stays as the fallback for keyboards and old browsers.
  useEffect(() => {
    const node = sentinel.current;
    if (!node || !hasMore || typeof IntersectionObserver === "undefined") return;
    const observer = new IntersectionObserver(
      (entries) => entries.some((e) => e.isIntersecting) && loadMore(),
      { rootMargin: "600px 0px" }
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, [hasMore, loadMore]);

  const countFor = (name: string) => audiences.find((a) => a.name === name)?.count;
  const switchAudience = (audience: Filters["audience"]) =>
    setFilters({ ...EMPTY_FILTERS, audience, q: filters.q });

  return (
    <div>
      <div className="audience-switch" role="tablist" aria-label="What are you looking for">
        <button
          role="tab"
          aria-selected={lessonMode}
          className={lessonMode ? "active" : ""}
          onClick={() => switchAudience("students")}
        >
          <span className="audience-title">Lesson planning</span>
          <span className="audience-sub">
            Things to teach with{countFor("students") != null ? ` · ${countFor("students")}` : ""}
          </span>
        </button>
        <button
          role="tab"
          aria-selected={!lessonMode}
          className={!lessonMode ? "active" : ""}
          onClick={() => switchAudience("educators")}
        >
          <span className="audience-title">Professional learning</span>
          <span className="audience-sub">
            Courses &amp; CEUs for you
            {countFor("educators") != null ? ` · ${countFor("educators")}` : ""}
          </span>
        </button>
      </div>

      <FilterBar
        filters={filters}
        onChange={setFilters}
        subjects={subjects}
        tags={tags}
        standards={standards}
      />
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
          {!loading && unmatched.length > 0 && total > 0 && (
            <p className="search-note">
              No matches for{" "}
              {unmatched.map((t, i) => (
                <span key={t}>
                  {i > 0 && ", "}
                  <strong>“{t}”</strong>
                </span>
              ))}
              . Showing the closest matches for the rest of your search.
            </p>
          )}
          <div className="results-row">
            <p>
              {loading
                ? "Loading…"
                : total === 0
                  ? "No results"
                  : `Showing ${resources.length} of ${total} result${total === 1 ? "" : "s"}`}
            </p>
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
              />
            ))}
          </div>
          {hasMore && (
            <div ref={sentinel} className="load-more">
              <button onClick={loadMore} disabled={loadingMore}>
                {loadingMore ? "Loading…" : `Show more (${total - resources.length} left)`}
              </button>
            </div>
          )}
          {!loading && resources.length === 0 && (
            <p>
              {lessonMode
                ? "No resources match — try a broader theme or clear a filter."
                : "No professional learning matches yet — try a broader topic."}
            </p>
          )}
        </>
      )}
    </div>
  );
}
