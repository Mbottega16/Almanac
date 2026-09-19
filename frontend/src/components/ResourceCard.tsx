import { CSSProperties, useState } from "react";

import {
  Resource,
  SCOPE_LABELS,
  Scope,
  UDL_LABELS,
  UdlPrinciple,
  creditLabel,
  markVisited,
  setFavorite,
} from "../api/client";
import { tintFor } from "../palette";

function faviconUrl(link: string): string | null {
  try {
    const { hostname } = new URL(link);
    return `https://www.google.com/s2/favicons?sz=128&domain=${hostname}`;
  } catch {
    return null;
  }
}

// Cards showed the full description everywhere, which turned a grid into a
// wall of text. Lead with the first sentence — these descriptions are written
// claim-first, so it carries the point — and keep the rest behind "Details".
function firstSentence(text: string, max = 140): string {
  const trimmed = text.trim();
  const match = trimmed.match(/^.*?[.!?](?=\s|$)/);
  const lead = match ? match[0] : trimmed;
  if (lead.length <= max) return lead;
  return `${lead.slice(0, max).replace(/\s+\S*$/, "")}…`;
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
  const [expanded, setExpanded] = useState(false);

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
  const tint = tintFor(resource.link);
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

  const description = resource.description || "";
  const summary = description ? firstSentence(description) : "";
  const hasMore =
    description.length > summary.length ||
    resource.learning_outcomes.length > 0 ||
    !!resource.materials ||
    !!resource.credit_note;

  const tintStyle = {
    "--card-accent": tint.accent,
    "--card-wash": tint.wash,
  } as CSSProperties;

  return (
    <div
      className={`entry-card view-${view}${visited ? " visited" : ""}`}
      style={tintStyle}
    >
      <div className="entry-card-accent" aria-hidden="true" />
      <div className="entry-card-head">
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
        <div className="entry-card-headings">
          <h3>
            <a href={resource.link} target="_blank" rel="noreferrer" onClick={handleOpen}>
              {resource.title || resource.link}
            </a>
          </h3>
          <div className="meta">
            {meta}
            {resource.publisher
              ? ` — ${resource.publisher}`
              : resource.source_site
                ? ` — ${resource.source_site}`
                : ""}
          </div>
          <div className="badge-row">
            <span className={`cost-badge cost-${resource.cost}`}>
              {COST_LABEL[resource.cost] ?? resource.cost}
              {resource.price_note ? ` · ${resource.price_note}` : ""}
            </span>
            {resource.credit_type && (
              <span
                className="credit-badge"
                title={resource.credit_note || "Credit granted on completion"}
              >
                {creditLabel(resource.credit_type, resource.credit_hours)}
              </span>
            )}
            {scopeLabel && resource.audience === "students" && (
              <span className={`scope-badge scope-${resource.scope}`}>{scopeLabel}</span>
            )}
            {resource.granularity === "collection" && (
              <span
                className="scope-badge"
                title="Links a browse / portal page, not one class-ready resource"
              >
                Browse page
              </span>
            )}
            {resource.link_status === "dead" && (
              <span
                className="link-warn-badge"
                title="Our last check couldn't reach this page — it may have moved or been removed"
              >
                ⚠ link may be broken
              </span>
            )}
            {visited && (
              <span className="visited-badge" title="You've opened this before">
                ✓ visited
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="entry-card-body">
        {summary && <p className="entry-summary">{summary}</p>}
        {expanded && (
          <div className="entry-details">
            {description && description !== summary && <p>{description}</p>}
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
            {resource.credit_note && (
              <p className="materials">
                <strong>Credit:</strong> {resource.credit_note}
              </p>
            )}
          </div>
        )}
        {hasMore && (
          <button
            className="entry-more"
            onClick={() => setExpanded((v) => !v)}
            aria-expanded={expanded}
          >
            {expanded ? "Less" : "Details"}
          </button>
        )}
        <div className="udl-row">
          {resource.udl_principles.map((p) => (
            <span
              key={p}
              className={`udl-pill udl-${p}${rationale[p] ? " has-why" : ""}`}
              title={
                rationale[p]
                  ? `Why ${UDL_LABELS[p as UdlPrinciple] ?? p}: ${rationale[p]}`
                  : undefined
              }
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
