import { useEffect, useState } from "react";

import {
  Resource,
  ResourceDraft,
  batchImport,
  fetchCaptureEnabled,
  researchLinks,
  searchResources,
} from "../api/client";
import ResourceCard from "../components/ResourceCard";

/**
 * Two modes:
 *  - Dormant (no ANTHROPIC_API_KEY on the backend): read-only view of what was
 *    added recently. Capture happens in a Claude Code session rooted in the
 *    repo — paste links / name a site, it researches + tags + saves via
 *    POST /api/resources/batch.
 *  - Live (key set): a paste box that calls POST /api/capture/research, shows
 *    draft resources, and commits the chosen ones via the same batch endpoint.
 */
export default function CapturePage() {
  const [recent, setRecent] = useState<Resource[]>([]);
  const [loading, setLoading] = useState(true);
  const [liveEnabled, setLiveEnabled] = useState(false);

  const [raw, setRaw] = useState("");
  const [notes, setNotes] = useState("");
  const [drafts, setDrafts] = useState<ResourceDraft[] | null>(null);
  const [working, setWorking] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  const loadRecent = () =>
    searchResources({})
      .then((res) => setRecent(res.items.filter((r) => r.source === "capture").slice(0, 20)))
      .finally(() => setLoading(false));

  useEffect(() => {
    loadRecent();
    fetchCaptureEnabled().then((r) => setLiveEnabled(r.enabled)).catch(() => {});
  }, []);

  const research = async () => {
    const links = raw
      .split(/\s+/)
      .map((s) => s.trim())
      .filter((s) => /^https?:\/\//.test(s));
    if (links.length === 0) {
      setMsg("Paste one or more http(s) links first.");
      return;
    }
    setWorking(true);
    setMsg(null);
    try {
      const { drafts } = await researchLinks(links, notes || undefined);
      setDrafts(drafts);
    } catch {
      setMsg("Research failed — check the backend logs.");
    } finally {
      setWorking(false);
    }
  };

  const commit = async () => {
    if (!drafts) return;
    setWorking(true);
    try {
      const res = await batchImport(drafts);
      setMsg(`Saved ${res.created.length} new, updated ${res.updated.length}.`);
      setDrafts(null);
      setRaw("");
      setNotes("");
      loadRecent();
    } catch {
      setMsg("Save failed.");
    } finally {
      setWorking(false);
    }
  };

  return (
    <div>
      {liveEnabled ? (
        <div className="capture-live">
          <p>Paste links (one per line). Claude drafts a tagged entry for each; you review before saving.</p>
          <textarea
            rows={5}
            value={raw}
            onChange={(e) => setRaw(e.target.value)}
            placeholder="https://www.commonlit.org/en/texts/...
https://phet.colorado.edu/en/simulations/..."
          />
          <input
            type="text"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Optional context (grade, unit, why it's useful)…"
          />
          <div className="capture-actions">
            <button onClick={research} disabled={working}>
              {working ? "Working…" : "Research"}
            </button>
            {drafts && (
              <button onClick={commit} disabled={working}>
                Save {drafts.length} to library
              </button>
            )}
          </div>
        </div>
      ) : (
        <p>
          To add resources right now, paste a raw list of links — or the name of a site to pull
          from — into a Claude Code session rooted in this repo. It researches and tags each one
          (subject, grade band, format, free/paid, UDL principles) and saves it here. The
          paste-box UI on this page activates once <code>ANTHROPIC_API_KEY</code> is set on the
          backend.
        </p>
      )}

      {msg && <p className="capture-msg">{msg}</p>}

      {drafts && (
        <>
          <h3>Drafts (not saved yet)</h3>
          {drafts.map((d, i) => (
            <ResourceCard
              key={i}
              resource={{
                ...d,
                id: -i - 1,
                source: "capture",
                granularity: d.granularity ?? "specific",
                udl_rationale: d.udl_rationale ?? null,
                audience: "students",
                credit_type: null,
                credit_hours: null,
                credit_note: null,
                standard_codes: [],
                link_status: "unknown",
                link_checked_at: null,
                visited_at: null,
                created_at: "",
                updated_at: "",
              }}
            />
          ))}
        </>
      )}

      <h3>Recently added</h3>
      {loading && <p>Loading…</p>}
      {!loading && recent.length === 0 && <p>Nothing captured yet.</p>}
      {recent.map((r) => (
        <ResourceCard key={r.id} resource={r} />
      ))}
    </div>
  );
}
