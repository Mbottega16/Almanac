import { useState } from "react";

import {
  Resource,
  SCOPE_LABELS,
  Scope,
  UDL_LABELS,
  UdlPrinciple,
  markVisited,
  setFavorite,
} from "../api/client";

function faviconUrl(link: string): string | null {
  try {
    const { hostname } = new URL(link);
    return `https://www.google.com/s2/favicons?sz=64&domain=${hostname}`;
  } catch {
    return null;
  }
}

const COST_LABEL: Record<string, string> = {
  free: "Free",
  paid: "Paid",
  freemium: "Freemium",
};

export default function ResourceCard({
  resource,
  view = "grid",
  onVisit,
  onFavoriteToggle,
}: {
  resource: Resource;
  view?: "grid" | "list" | "large";
  onVisit?: () => void;
  onFavoriteToggle?: () => void;
}) {
  const [visited, setVisited] = useState(!!resource.visited_at);
  const [favorite, setFavoriteState] = useState(resource.is_favorite);
  const [busy, setBusy] = useState(false);

  const handleOpen = () => {
    markVisited(resource.id).catch(() => {});
    setVisited(true);
    onVisit?.();
  };

  const handleFavoriteClick = async () => {
    if (busy) return;
    setBusy(true);
    const next = !favorite;
    try {
      await setFavorite(resource.id, next);
      setFavoriteState(next);
      onFavoriteToggle?.();
    } catch {
      // leave state as-is on failure
    } finally {
      setBusy(false);
    }
  };

  const favicon = faviconUrl(resource.link);
  const ageLabel =
    resource.age_min != null && resource.age_max != null
      ? `ages ${resource.age_min}–${resource.age_max}`
      : null;
  const durationLabel =
    resource.duration_minutes != null ? `${resource.duration_minutes} min` : null;
  const meta = [
    resource.subject,
    resource.grade_band,
    ageLabel,
    resource.resource_type,
    durationLabel,
  ]
    .filter(Boolean)
    .join(" · ");

  // Only worth calling out when it's bigger than a single lesson.
  const scopeLabel =
    resource.scope && resource.scope !== "lesson"
      ? SCOPE_LABELS[resource.scope as Scope] ?? resource.scope
      : null;

  // Per-principle "why this applies", parsed from the newline/`;`-separated
  // udl_rationale string -> { principle: reason }.
  const rationale: Record<string, string> = {};
  (resource.udl_rationale || "")
    .split(/[\n;]+/)
    .map((s) => s.trim())
    .filter(Boolean)
    .forEach((line) => {
      const m = line.match(/^([a-z_ &]+?)\s*[:\-]\s*(.+)$/i);
      if (m) rationale[m[1].trim().toLowerCase().replace(/[ &]+/g, "_")] = m[2].trim();
    });

  return (
    <div className={`entry-card view-${view}${visited ? " visited" : ""}`}>
      <button
        className={`favorite-btn${favorite ? " active" : ""}`}
        onClick={handleFavoriteClick}
        title={favorite ? "Remove from collection" : "Save to collection"}
        aria-pressed={favorite}
      >
        {favorite ? "★" : "☆"}
      </button>
      <div className="entry-card-logo">
        {favicon ? (
          <img src={favicon} alt="" loading="lazy" />
        ) : (
          <span className="entry-card-logo-fallback">
            {(resource.title || resource.link)[0]?.toUpperCase()}
          </span>
        )}
      </div>
      <div className="entry-card-body">
        <div className="badge-row">
          <span className={`cost-badge cost-${resource.cost}`}>
            {COST_LABEL[resource.cost] ?? resource.cost}
            {resource.price_note ? ` · ${resource.price_note}` : ""}
          </span>
          {scopeLabel && (
            <span className={`scope-badge scope-${resource.scope}`}>{scopeLabel}</span>
          )}
          {resource.granularity === "collection" && (
            <span className="scope-badge" title="Links a browse / portal page, not one class-ready resource">
              Browse page
            </span>
          )}
          {resource.link_status === "dead" && (
            <span className="link-warn-badge" title="Our last check couldn't reach this page — it may have moved or been removed">
              ⚠ link may be broken
            </span>
          )}
          {visited && (
            <span className="visited-badge" title="You've opened this before">
              ✓ visited
            </span>
          )}
        </div>
        <h3>
          <a href={resource.link} target="_blank" rel="noreferrer" onClick={handleOpen}>
            {resource.title || resource.link}
          </a>
        </h3>
        <div className="meta">
          {meta}
          {resource.publisher ? ` — ${resource.publisher}` : resource.source_site ? ` — ${resource.source_site}` : ""}
        </div>
        {resource.description && <p>{resource.description}</p>}
        {resource.learning_outcomes.length > 0 && (
          <ul className="outcomes">
            {resource.learning_outcomes.map((o, i) => (
              <li key={i}>{o}</li>
            ))}
          </ul>
        )}
        {resource.materials && (
          <p className="materials">
            <strong>Materials:</strong> {resource.materials}
          </p>
        )}
        <div className="udl-row">
          {resource.udl_principles.map((p) => (
            <span
              key={p}
              className={`udl-pill udl-${p}${rationale[p] ? " has-why" : ""}`}
              title={rationale[p] ? `Why ${UDL_LABELS[p as UdlPrinciple] ?? p}: ${rationale[p]}` : undefined}
            >
              {UDL_LABELS[p as UdlPrinciple] ?? p}
              {rationale[p] ? " ⓘ" : ""}
            </span>
          ))}
        </div>
        <div className="tag-row">
          {resource.tags.map((t) => (
            <span key={t} className="tag-pill">
              {t}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
