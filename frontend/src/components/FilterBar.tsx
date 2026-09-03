import type { NameCount } from "../api/client";
import { UDL_LABELS, UDL_PRINCIPLES } from "../api/client";
import { GRADE_BANDS, RESOURCE_TYPES, SUBJECTS } from "../subjectGroups";

export interface Filters {
  q: string;
  subject: string;
  grade_band: string;
  resource_type: string;
  scope: string;
  cost: string;
  udl: string;
  tag: string;
  standard: string;
  age: string;
  // true => only granularity=specific (hide browse/portal pages)
  classReady: boolean;
}

export const EMPTY_FILTERS: Filters = {
  q: "",
  subject: "",
  grade_band: "",
  resource_type: "",
  scope: "",
  cost: "",
  udl: "",
  tag: "",
  standard: "",
  age: "",
  classReady: false,
};

// Filters -> API query params. `classReady` is a UI convenience for
// `granularity=specific`; keep the translation in one place.
export function toQuery(f: Filters) {
  const { classReady, ...rest } = f;
  return { ...rest, granularity: classReady ? "specific" : "" };
}

const COST_OPTIONS = [
  { value: "", label: "All" },
  { value: "free", label: "Free" },
  { value: "freemium", label: "Freemium" },
  { value: "paid", label: "Paid" },
];

// What size of thing to plan with — a single period, or a whole program.
const SCOPE_OPTIONS = [
  { value: "", label: "Anything" },
  { value: "lesson", label: "Single lessons" },
  { value: "unit", label: "Units" },
  { value: "course", label: "Full courses" },
  { value: "curriculum", label: "Curricula" },
];

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

  return (
    <div className="filter-bar">
      <input
        type="text"
        placeholder="Search a theme — 'fractions', 'the water cycle', 'the Civil Rights Movement'…"
        value={filters.q}
        onChange={(e) => set({ q: e.target.value })}
      />

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

      {/* Scope — one-off lesson vs. a full commercial curriculum. */}
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

      <div className="filter-row">
        <select value={filters.grade_band} onChange={(e) => set({ grade_band: e.target.value })}>
          <option value="">All grades</option>
          {GRADE_BANDS.map((g) => (
            <option key={g} value={g}>
              {g}
            </option>
          ))}
        </select>
        <input
          className="age-input"
          type="number"
          min={2}
          max={99}
          placeholder="Age"
          value={filters.age}
          onChange={(e) => set({ age: e.target.value })}
        />
        <select
          value={filters.resource_type}
          onChange={(e) => set({ resource_type: e.target.value })}
        >
          <option value="">All formats</option>
          {RESOURCE_TYPES.map((t) => (
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
        <label className="class-ready-toggle" title="Hide browse / portal pages — show only resources a class can use as-is">
          <input
            type="checkbox"
            checked={filters.classReady}
            onChange={(e) => set({ classReady: e.target.checked })}
          />
          Class-ready only
        </label>
      </div>
      {filters.subject && (
        <p className="filter-hint">
          {countFor(filters.subject)} in "{filters.subject}"
        </p>
      )}
    </div>
  );
}
