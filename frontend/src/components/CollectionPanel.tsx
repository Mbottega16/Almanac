import { useEffect, useMemo, useState } from "react";

import { Resource, UDL_LABELS, UDL_PRINCIPLES, UdlPrinciple, searchResources } from "../api/client";

// The Vercel /tmp DB resets on every cold start, so server-side favorites
// vanish. Mirror them into localStorage on each successful load and fall
// back to that cache when the API is unreachable — the collection then
// survives a cold start for this browser.
const CACHE_KEY = "almanac.collection";

function loadCache(): Resource[] {
  try {
    const raw = localStorage.getItem(CACHE_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function saveCache(items: Resource[]) {
  try {
    localStorage.setItem(CACHE_KEY, JSON.stringify(items));
  } catch {
    // per-viewer convenience only — fine if it fails
  }
}

function splitMaterials(raw: string | null): string[] {
  return (raw || "")
    .split(/[\n;,]+/)
    .map((s) => s.trim())
    .filter((s) => s && s.toLowerCase() !== "none");
}

export default function CollectionPanel({
  open,
  onClose,
  refreshKey,
}: {
  open: boolean;
  onClose: () => void;
  refreshKey: number;
}) {
  const [saved, setSaved] = useState<Resource[]>(loadCache);
  const [loading, setLoading] = useState(true);
  const [stale, setStale] = useState(false);
  const [asPlan, setAsPlan] = useState(false);

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    searchResources({ favorite: true, limit: 200 })
      .then((res) => {
        setSaved(res.items);
        saveCache(res.items);
        setStale(false);
      })
      .catch(() => setStale(true)) // keep the cached list on screen
      .finally(() => setLoading(false));
  }, [open, refreshKey]);

  const plan = useMemo(() => {
    const ordered = [...saved].sort(
      (a, b) => (a.duration_minutes ?? 1e9) - (b.duration_minutes ?? 1e9)
    );
    const totalMin = saved.reduce((n, r) => n + (r.duration_minutes ?? 0), 0);
    const materials = Array.from(
      new Set(saved.flatMap((r) => splitMaterials(r.materials)))
    ).sort();
    const covered = new Set(saved.flatMap((r) => r.udl_principles));
    const missing = UDL_PRINCIPLES.filter((p) => !covered.has(p));
    return { ordered, totalMin, materials, covered, missing };
  }, [saved]);

  return (
    <div className={`favorites-panel${open ? " open" : ""}`}>
      <div className="favorites-panel-header">
        <h2>★ My Collection</h2>
        <button onClick={onClose} aria-label="Close collection panel">
          ✕
        </button>
      </div>

      {saved.length > 0 && (
        <div className="collection-modes" role="group" aria-label="View">
          <button className={asPlan ? "" : "active"} onClick={() => setAsPlan(false)}>
            List
          </button>
          <button className={asPlan ? "active" : ""} onClick={() => setAsPlan(true)}>
            Lesson plan
          </button>
        </div>
      )}
      {stale && (
        <p className="collection-stale">
          Showing your saved set from this device — the library API isn't reachable right now.
        </p>
      )}
      {loading && saved.length === 0 && <p>Loading…</p>}
      {!loading && saved.length === 0 && (
        <p>Nothing saved yet — click the star on any resource to build a lesson set here.</p>
      )}

      {asPlan && saved.length > 0 && (
        <div className="lessonplan-summary">
          <p>
            <strong>{plan.totalMin ? `${plan.totalMin} min` : "untimed"}</strong> across{" "}
            {saved.length} resource{saved.length === 1 ? "" : "s"}
          </p>
          <p className="lessonplan-udl">
            UDL:{" "}
            {UDL_PRINCIPLES.map((p) => (
              <span
                key={p}
                className={`udl-pill udl-${p}${plan.covered.has(p) ? "" : " absent"}`}
              >
                {UDL_LABELS[p as UdlPrinciple]}
                {plan.covered.has(p) ? " ✓" : " —"}
              </span>
            ))}
          </p>
          {plan.missing.length > 0 && (
            <p className="lessonplan-gap">
              Add a resource for{" "}
              {plan.missing.map((p) => UDL_LABELS[p as UdlPrinciple]).join(" & ")} to cover all
              three.
            </p>
          )}
          {plan.materials.length > 0 && (
            <p className="lessonplan-materials">
              <strong>Materials:</strong> {plan.materials.join(", ")}
            </p>
          )}
        </div>
      )}

      {(asPlan ? plan.ordered : saved).map((e) => (
        <a
          key={e.id}
          href={e.link}
          target="_blank"
          rel="noreferrer"
          className="favorites-panel-item"
        >
          <strong>{e.title || e.link}</strong>
          <span>
            {[
              e.subject,
              e.grade_band,
              e.duration_minutes != null ? `${e.duration_minutes} min` : null,
            ]
              .filter(Boolean)
              .join(" · ")}
            {e.udl_principles.length ? ` — ${e.udl_principles.join(", ")}` : ""}
          </span>
        </a>
      ))}
    </div>
  );
}
