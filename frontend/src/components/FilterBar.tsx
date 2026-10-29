import { useState } from "react";

import type { Audience, NameCount } from "../api/client";
import { SCOPE_LABELS, UDL_LABELS, UDL_PRINCIPLES } from "../api/client";
import { DURATION_LABELS, DurationBucket } from "../discovery";
import { GRADE_BANDS, PD_RESOURCE_TYPES, RESOURCE_TYPES, SUBJECTS } from "../subjectGroups";

export interface Filters {
  q: string;
  // Lesson planning ('students') vs professional learning ('educators').
  audience: Audience;
  subject: string;
  grade_band: string;
  resource_type: string;
  scope: string;
  cost: string;
  udl: string;
  tag: string;
  standard: string;
  age: string;
  // "" = anything, "any" = grants some credit, else a specific credit type
  credit_type: string;
  // true => only granularity=specific (hide browse/portal pages)
  classReady: boolean;
  // "" = any length, else a DurationBucket key. NOT an API parameter — the
  // API has no duration filter, so BrowsePage matches durations client-side
  // over the returned items (see discovery.ts).
  duration: string;
}

export const EMPTY_FILTERS: Filters = {
  q: "",
  audience: "students",
  subject: "",
  grade_band: "",
  resource_type: "",
  scope: "",
  cost: "",
  udl: "",
  tag: "",
  standard: "",
  age: "",
  credit_type: "",
  classReady: false,
  duration: "",
};

// Filters -> API query params. `classReady` is a UI convenience for
// `granularity=specific` and `duration` is matched client-side; keep both
// translations in one place.
export function toQuery(f: Filters) {
  const { classReady, duration, ...rest } = f;
  return { ...rest, granularity: classReady ? "specific" : "" };
}

const COST_OPTIONS = [
  { value: "", label: "All" },
  { value: "free", label: "Free" },
  { value: "freemium", label: "Freemium" },
  { value: "paid", label: "Paid" },
];

const CREDIT_OPTIONS = [
  { value: "", label: "Any" },
  { value: "any", label: "Offers credit" },
  { value: "ceu", label: "CEUs" },
  { value: "pd_hours", label: "PD hours" },
  { value: "certificate", label: "Certificate" },
];

// What size of thing to plan with — a single period, or a whole program.
const SCOPE_OPTIONS = [
  { value: "", label: "Anything" },
  { value: "lesson", label: "Single lessons" },
  { value: "unit", label: "Units" },
  { value: "course", label: "Full courses" },
  { value: "curriculum", label: "Curricula" },
];

interface ActiveChip {
  key: string;
  label: string;
  clear: Partial<Filters>;
}

/** The filters currently in force, as removable chips — so a visitor who
 *  arrived via the guided doors or a sentence can see (and undo) exactly
 *  what is narrowing their results without opening the Refine panel. */
export function activeChips(f: Filters): ActiveChip[] {
  const chips: ActiveChip[] = [];
  if (f.subject) chips.push({ key: "subject", label: f.subject, clear: { subject: "" } });
  if (f.grade_band)
    chips.push({ key: "grade_band", label: `Grades ${f.grade_band}`, clear: { grade_band: "" } });
  if (f.age) chips.push({ key: "age", label: `Age ${f.age}`, clear: { age: "" } });
  if (f.duration)
    chips.push({
      key: "duration",
      label: DURATION_LABELS[f.duration as DurationBucket] ?? f.duration,
      clear: { duration: "" },
    });
  if (f.resource_type)
    chips.push({ key: "resource_type", label: f.resource_type, clear: { resource_type: "" } });
  if (f.scope)
    chips.push({
      key: "scope",
      label: SCOPE_LABELS[f.scope as keyof typeof SCOPE_LABELS] ?? f.scope,
      clear: { scope: "" },
    });
  if (f.cost)
    chips.push({
      key: "cost",
      label: f.cost[0].toUpperCase() + f.cost.slice(1),
      clear: { cost: "" },
    });
  if (f.udl)
    chips.push({
      key: "udl",
      label: UDL_LABELS[f.udl as keyof typeof UDL_LABELS] ?? f.udl,
      clear: { udl: "" },
    });
  if (f.tag) chips.push({ key: "tag", label: `Theme: ${f.tag}`, clear: { tag: "" } });
  if (f.standard)
    chips.push({ key: "standard", label: f.standard, clear: { standard: "" } });
  if (f.credit_type)
    chips.push({ key: "credit_type", label: "Offers credit", clear: { credit_type: "" } });
  if (f.classReady)
    chips.push({ key: "classReady", label: "Class-ready only", clear: { classReady: false } });
  return chips;
}

export default function FilterBar({
  filters,
  onChange,
  subjects,
  tags,
  standards = [],
}: {
  filters: Filters;
  onChange: (next: Filters) => void;
  subjects: NameCount[];
  tags: NameCount[];
  standards?: NameCount[];
}) {
  const countFor = (name: string) => subjects.find((s) => s.name === name)?.count ?? 0;
  const known = new Set(subjects.map((s) => s.name));
  const set = (patch: Partial<Filters>) => onChange({ ...filters, ...patch });
  const lessonMode = filters.audience === "students";
  // The whole point of the overhaul: everything beyond the search box lives
  // behind this one toggle, shut unless the visitor asks for it.
  const [refineOpen, setRefineOpen] = useState(false);
  const chips = activeChips(filters);

  return (
    <div className="filter-bar">
      <input
        type="text"
        placeholder={
          lessonMode
            ? "Search anything — 'fractions', 'cheetah pre-K movement', 'Civil Rights primary sources'…"
            : "Search professional learning — 'UDL', 'IEPs', 'science of reading', 'free CEUs'…"
        }
        value={filters.q}
        onChange={(e) => set({ q: e.target.value })}
      />

      <div className="refine-row">
        <button
          type="button"
          className="refine-toggle"
          aria-expanded={refineOpen}
          onClick={() => setRefineOpen((v) => !v)}
        >
          Refine {refineOpen ? "▴" : "▾"}
          {chips.length > 0 && <span className="refine-count">{chips.length} on</span>}
        </button>
        {chips.length > 0 && (
          <div className="active-chips" role="group" aria-label="Active filters">
            {chips.map((c) => (
              <button
                key={c.key}
                type="button"
                className="active-chip"
                title={`Remove “${c.label}”`}
                onClick={() => set(c.clear)}
              >
                {c.label} ✕
              </button>
            ))}
            {chips.length > 1 && (
              <button
                type="button"
                className="active-chip clear-all"
                onClick={() =>
                  onChange({ ...EMPTY_FILTERS, audience: filters.audience, q: filters.q })
                }
              >
                Clear all
              </button>
            )}
          </div>
        )}
      </div>

      {refineOpen && (
        <div className="refine-panel">
          {/* Free / Paid is the first cut a teacher makes. */}
          <div className="cost-toggle" role="group" aria-label="Cost">
            {COST_OPTIONS.map((o) => (
              <button
                key={o.value}
                className={filters.cost === o.value ? "active" : ""}
                onClick={() => set({ cost: o.value })}
              >
                {o.label}
              </button>
            ))}
          </div>

          {lessonMode ? (
            /* Scope — one-off lesson vs. a full commercial curriculum. */
            <div className="cost-toggle" role="group" aria-label="Lesson vs. curriculum">
              {SCOPE_OPTIONS.map((o) => (
                <button
                  key={o.value}
                  className={filters.scope === o.value ? "active" : ""}
                  onClick={() => set({ scope: o.value })}
                >
                  {o.label}
                </button>
              ))}
            </div>
          ) : (
            <div className="cost-toggle" role="group" aria-label="Credit">
              {CREDIT_OPTIONS.map((o) => (
                <button
                  key={o.value}
                  className={filters.credit_type === o.value ? "active" : ""}
                  onClick={() => set({ credit_type: o.value })}
                >
                  {o.label}
                </button>
              ))}
            </div>
          )}

          {/* How long it runs — matched client-side (the API has no
              duration parameter), so it sits with the other refinements. */}
          {lessonMode && (
            <div className="cost-toggle" role="group" aria-label="Running time">
              <button
                className={filters.duration === "" ? "active" : ""}
                onClick={() => set({ duration: "" })}
              >
                Any length
              </button>
              {(Object.keys(DURATION_LABELS) as DurationBucket[]).map((b) => (
                <button
                  key={b}
                  className={filters.duration === b ? "active" : ""}
                  onClick={() => set({ duration: filters.duration === b ? "" : b })}
                >
                  {DURATION_LABELS[b]}
                </button>
              ))}
            </div>
          )}

          {/* Subject chips — jump straight to a subject instead of a dropdown scan. */}
          <div className="category-groups" role="group" aria-label="Browse by subject">
            <button
              className={filters.subject === "" ? "active" : ""}
              onClick={() => set({ subject: "" })}
            >
              All subjects
            </button>
            {SUBJECTS.filter((s) => known.has(s)).map((s) => (
              <button
                key={s}
                className={filters.subject === s ? "active" : ""}
                onClick={() => set({ subject: filters.subject === s ? "" : s })}
              >
                {s}
              </button>
            ))}
          </div>

          {/* UDL principle — the point of the tool: cover all three. */}
          {lessonMode && (
            <div className="udl-toggle" role="group" aria-label="UDL principle">
              <span className="udl-toggle-label">UDL:</span>
              {UDL_PRINCIPLES.map((p) => (
                <button
                  key={p}
                  className={`udl-${p}${filters.udl === p ? " active" : ""}`}
                  onClick={() => set({ udl: filters.udl === p ? "" : p })}
                >
                  {UDL_LABELS[p]}
                </button>
              ))}
            </div>
          )}

          <div className="filter-row">
            <select value={filters.grade_band} onChange={(e) => set({ grade_band: e.target.value })}>
              <option value="">{lessonMode ? "All grades" : "Grades you teach: all"}</option>
              {GRADE_BANDS.map((g) => (
                <option key={g} value={g}>
                  {g}
                </option>
              ))}
            </select>
            {lessonMode && (
              <input
                className="age-input"
                type="number"
                min={2}
                max={99}
                placeholder="Age"
                value={filters.age}
                onChange={(e) => set({ age: e.target.value })}
              />
            )}
            <select
              value={filters.resource_type}
              onChange={(e) => set({ resource_type: e.target.value })}
            >
              <option value="">All formats</option>
              {(lessonMode ? RESOURCE_TYPES : PD_RESOURCE_TYPES).map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
            <select value={filters.tag} onChange={(e) => set({ tag: e.target.value })}>
              <option value="">All themes</option>
              {tags.map((t) => (
                <option key={t.name} value={t.name}>
                  {t.name} ({t.count})
                </option>
              ))}
            </select>
            {standards.length > 0 && (
              <select
                value={filters.standard}
                onChange={(e) => set({ standard: e.target.value })}
                title="Filter to resources aligned to a specific standard"
              >
                <option value="">Any standard</option>
                {standards.map((s) => (
                  <option key={s.name} value={s.name}>
                    {s.name} ({s.count})
                  </option>
                ))}
              </select>
            )}
            {lessonMode && (
              <label
                className="class-ready-toggle"
                title="Hide browse / portal pages — show only resources a class can use as-is"
              >
                <input
                  type="checkbox"
                  checked={filters.classReady}
                  onChange={(e) => set({ classReady: e.target.checked })}
                />
                Class-ready only
              </label>
            )}
          </div>
          {filters.subject && (
            <p className="filter-hint">
              {countFor(filters.subject)} in "{filters.subject}"
            </p>
          )}
        </div>
      )}
    </div>
  );
}
