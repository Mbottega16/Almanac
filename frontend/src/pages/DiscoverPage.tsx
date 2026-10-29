import { useEffect, useRef, useState } from "react";

import { searchResources } from "../api/client";
import { EMPTY_FILTERS, Filters, toQuery } from "../components/FilterBar";
import { CURATED_PATHS, DOORS, countDurations } from "../discovery";
import { chipsToPatch, parseSentence } from "../parseSentence";

// The front door for a first-time visitor. Three ways in, none of them a
// wall of filter checklists:
// 1. Say it in a sentence — we show the filters we understood as chips.
// 2. Three doors — who / what / how much time — one tap each.
// 3. A ready-made path — a preset for a situation, not a subject.
// Every route lands on the ordinary Browse page with ordinary filters, so
// anything chosen here can be undone there (each filter shows as a chip).

type BucketCounts = { lt20: number; period: number; long: number; unknown: number };

export default function DiscoverPage({
  onDone,
  onSkip,
}: {
  onDone: (filters: Filters) => void;
  onSkip: () => void;
}) {
  const [i, setI] = useState(0);
  const [filters, setFilters] = useState<Filters>(EMPTY_FILTERS);
  const [count, setCount] = useState<number | null>(null);
  const [buckets, setBuckets] = useState<BucketCounts | null>(null);
  // The last door pick, so a dead end can be undone in one tap.
  const [lastPick, setLastPick] = useState<{
    prev: Partial<Filters>;
    label: string;
  } | null>(null);
  const dragX = useRef<number | null>(null);

  // --- plain-language sentence -------------------------------------------
  const [sentence, setSentence] = useState("");
  const [removedChips, setRemovedChips] = useState<Set<string>>(new Set());
  const parsed = parseSentence(sentence);
  const liveChips = parsed.chips.filter((c) => !removedChips.has(c.id));

  const submitSentence = (e: React.FormEvent) => {
    e.preventDefault();
    if (!sentence.trim()) return;
    onDone({
      ...EMPTY_FILTERS,
      ...chipsToPatch(liveChips),
      q: parsed.q,
    });
  };

  // --- the three doors -----------------------------------------------------
  const last = i === DOORS.length - 1;

  // Live "how many match so far" for the first two doors — the pinpoint
  // feedback. The time door needs real duration tallies instead (below).
  useEffect(() => {
    if (last) return;
    let cancelled = false;
    searchResources(toQuery(filters))
      .then((r) => !cancelled && setCount(r.total))
      .catch(() => !cancelled && setCount(null));
    return () => {
      cancelled = true;
    };
  }, [filters, last]);

  // On the time door, count each bucket honestly over everything the first
  // two doors matched — including how many list no time at all.
  useEffect(() => {
    if (!last) return;
    let cancelled = false;
    setBuckets(null);
    countDurations(toQuery(filters) as Record<string, unknown>)
      .then((b) => !cancelled && setBuckets(b))
      .catch(() => !cancelled && setBuckets(null));
    return () => {
      cancelled = true;
    };
  }, [filters, last]);

  const pick = (patch: Partial<Filters>, label: string) => {
    const prev: Partial<Filters> = {};
    (Object.keys(patch) as (keyof Filters)[]).forEach((k) => {
      (prev as Record<string, unknown>)[k] = filters[k];
    });
    const next = { ...filters, ...patch };
    setFilters(next);
    setLastPick(Object.keys(patch).length > 0 ? { prev, label } : null);
    if (last) onDone(next);
    else setI((n) => n + 1);
  };

  const undoLast = () => {
    if (!lastPick) return;
    setFilters((f) => ({ ...f, ...lastPick.prev }));
    setLastPick(null);
    setI((n) => Math.max(0, n - 1));
  };

  const back = () => setI((n) => Math.max(0, n - 1));
  const skipStep = () => (last ? onDone(filters) : setI((n) => n + 1));

  // Pointer/touch swipe: drag left = next, right = back.
  const onDown = (e: React.PointerEvent) => (dragX.current = e.clientX);
  const onUp = (e: React.PointerEvent) => {
    if (dragX.current == null) return;
    const dx = e.clientX - dragX.current;
    dragX.current = null;
    if (dx < -60 && !last) setI((n) => n + 1);
    else if (dx > 60 && i > 0) back();
  };

  const bucketCount = (patch: Partial<Filters>): number | null => {
    if (!buckets) return null;
    const d = patch.duration;
    if (!d) return buckets.lt20 + buckets.period + buckets.long + buckets.unknown;
    return buckets[d as keyof BucketCounts] ?? null;
  };

  return (
    <div className="discover">
      <header className="discover-head">
        <span className="discover-brand">Almanac</span>
        <button className="discover-skip" onClick={onSkip}>
          Skip to browse →
        </button>
      </header>

      {/* 1 — say it in a sentence */}
      <section className="discover-sentence" aria-label="Search in plain language">
        <h1>What are you looking for?</h1>
        <p className="discover-sub">
          Describe it the way you'd say it — we'll translate it into filters
          and show you what we understood.
        </p>
        <form className="discover-freetext" onSubmit={submitSentence}>
          <input
            type="text"
            placeholder="Try: a 45-minute hands-on science activity for 4th graders"
            value={sentence}
            onChange={(e) => {
              setSentence(e.target.value);
              setRemovedChips(new Set());
            }}
            aria-label="Describe what you are looking for"
          />
          {sentence.trim() && (
            <div className="parsed-chips" aria-live="polite">
              {liveChips.map((c) => (
                <button
                  key={c.id}
                  type="button"
                  className="parsed-chip"
                  title={`Not right? Remove “${c.label}”`}
                  onClick={() =>
                    setRemovedChips((s) => new Set(s).add(c.id))
                  }
                >
                  {c.label} ✕
                </button>
              ))}
              {parsed.q && (
                <span className="parsed-theme">Theme: “{parsed.q}”</span>
              )}
              {liveChips.length === 0 && !parsed.q && (
                <span className="parsed-theme">Searching those words as a theme</span>
              )}
            </div>
          )}
          <button type="submit" disabled={!sentence.trim()}>
            Show me these resources →
          </button>
        </form>
      </section>

      {/* 2 — three doors */}
      <section aria-label="Answer three quick questions">
        <h2 className="discover-section-title">…or answer three quick questions</h2>
        <div className="discover-progress">
          {DOORS.map((_, n) => (
            <span key={n} className={`discover-dot${n === i ? " on" : n < i ? " done" : ""}`} />
          ))}
        </div>

        <div className="discover-viewport" onPointerDown={onDown} onPointerUp={onUp}>
          <div
            className="discover-track"
            style={{ transform: `translateX(calc(-${i * 100}% - ${i * 1.5}rem))` }}
          >
            {DOORS.map((door, n) => (
              <section className="discover-panel" key={door.key} aria-hidden={n !== i}>
                <h1>{door.question}</h1>
                {door.sub && <p className="discover-sub">{door.sub}</p>}
                <div className="discover-choices">
                  {door.choices.map((c) => {
                    const n2 = door.key === "time" ? bucketCount(c.patch) : null;
                    return (
                      <button
                        key={c.label}
                        className="discover-choice"
                        onClick={() => pick(c.patch, c.label)}
                        tabIndex={n === i ? 0 : -1}
                      >
                        <span className="discover-choice-label">{c.label}</span>
                        {c.hint && <span className="discover-choice-hint">{c.hint}</span>}
                        {n2 != null && (
                          <span className="discover-choice-hint">· {n2} match</span>
                        )}
                        {door.key === "time" && !buckets && (
                          <span className="discover-choice-hint">· counting…</span>
                        )}
                      </button>
                    );
                  })}
                </div>
                {door.key === "time" && buckets && buckets.unknown > 0 && (
                  <p className="discover-sub" style={{ marginTop: "0.9rem" }}>
                    {buckets.unknown} matching resources don't list a running
                    time — pick "Any length" to include them.
                  </p>
                )}
              </section>
            ))}
          </div>
        </div>

        <footer className="discover-foot">
          <button className="discover-nav" onClick={back} disabled={i === 0}>
            ← Back
          </button>
          {!last && count === 0 && lastPick ? (
            <button className="discover-recover" onClick={undoLast}>
              Nothing matches — undo "{lastPick.label}"
            </button>
          ) : (
            <span className="discover-count">
              {last
                ? buckets
                  ? `${buckets.lt20 + buckets.period + buckets.long + buckets.unknown} resources match so far`
                  : "…"
                : count == null
                  ? "…"
                  : `${count} resource${count === 1 ? "" : "s"} match so far`}
            </span>
          )}
          <button className="discover-nav" onClick={skipStep}>
            {last ? "See results →" : "Skip this question →"}
          </button>
        </footer>
      </section>

      {/* 3 — ready-made paths */}
      <section className="discover-paths" aria-label="Ready-made starting points">
        <h2 className="discover-section-title">…or start from a situation</h2>
        <div className="path-grid">
          {CURATED_PATHS.map((p) => (
            <button
              key={p.title}
              className="path-card"
              onClick={() => onDone({ ...EMPTY_FILTERS, ...p.patch })}
            >
              <span className="path-title">{p.title}</span>
              <span className="path-hint">{p.hint}</span>
            </button>
          ))}
        </div>
      </section>
    </div>
  );
}
