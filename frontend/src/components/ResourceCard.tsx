import { useState } from "react";

import { Resource, UDL_LABELS, UdlPrinciple, markVisited, setFavorite } from "../api/client";

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
  const meta = [resource.subject, resource.grade_band, resource.resource_type]
    .filter(Boolean)
    .join(" · ");

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
          {resource.source_site ? ` — ${resource.source_site}` : ""}
        </div>
        {resource.description && <p>{resource.description}</p>}
        <div className="udl-row">
          {resource.udl_principles.map((p) => (
            <span key={p} className={`udl-pill udl-${p}`}>
              {UDL_LABELS[p as UdlPrinciple] ?? p}
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
