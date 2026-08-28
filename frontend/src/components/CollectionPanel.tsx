import { useEffect, useState } from "react";

import { Resource, searchResources } from "../api/client";

export default function CollectionPanel({
  open,
  onClose,
  refreshKey,
}: {
  open: boolean;
  onClose: () => void;
  refreshKey: number;
}) {
  const [saved, setSaved] = useState<Resource[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    searchResources({ favorite: true })
      .then((res) => setSaved(res.items))
      .finally(() => setLoading(false));
  }, [open, refreshKey]);

  return (
    <div className={`favorites-panel${open ? " open" : ""}`}>
      <div className="favorites-panel-header">
        <h2>★ My Collection</h2>
        <button onClick={onClose} aria-label="Close collection panel">
          ✕
        </button>
      </div>
      {loading && <p>Loading…</p>}
      {!loading && saved.length === 0 && (
        <p>Nothing saved yet — click the star on any resource to build a lesson set here.</p>
      )}
      {saved.map((e) => (
        <a
          key={e.id}
          href={e.link}
          target="_blank"
          rel="noreferrer"
          className="favorites-panel-item"
        >
          <strong>{e.title || e.link}</strong>
          <span>
            {[e.subject, e.grade_band].filter(Boolean).join(" · ")}
            {e.udl_principles.length ? ` — ${e.udl_principles.join(", ")}` : ""}
          </span>
        </a>
      ))}
    </div>
  );
}
