import { useEffect, useState } from "react";

import { Resource, searchResources } from "../api/client";
import ResourceCard from "../components/ResourceCard";

/**
 * Current phase: capture happens inside a Claude Code session rooted in this
 * repo — paste raw links or name a source site, and it researches each one
 * (subject, grade, format, cost, UDL principles, a short description) and
 * saves them via POST /api/resources/batch. This page is a read-only view of
 * what landed most recently, so you can confirm a batch import worked.
 *
 * Later (needs an approved ANTHROPIC_API_KEY): this becomes a real
 * paste-box-and-review UI backed by POST /api/capture/research.
 */
export default function CapturePage() {
  const [recent, setRecent] = useState<Resource[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    searchResources({})
      .then((res) => setRecent(res.items.filter((r) => r.source === "capture").slice(0, 20)))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <p>
        To add resources right now, paste a raw list of links — or the name of a site to pull
        from — into a Claude Code session rooted in this repo. It researches and tags each one
        (subject, grade band, format, free/paid, UDL principles) and saves it here. A direct
        paste-box UI arrives once live Claude-assisted capture is approved and built.
      </p>
      <h3>Recently added</h3>
      {loading && <p>Loading…</p>}
      {!loading && recent.length === 0 && <p>Nothing captured yet.</p>}
      {recent.map((r) => (
        <ResourceCard key={r.id} resource={r} />
      ))}
    </div>
  );
}
