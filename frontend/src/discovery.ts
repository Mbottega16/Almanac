// The discovery layer: the three "doors" a first-time visitor walks through,
// the curated paths, and the duration buckets the doors and paths share.
//
// Field-mapping notes (all verified against the seed + API service code):
// - Door 1 sets `age`, NOT `grade_band`. The API's grade_band filter is an
//   exact match, so grade_band="3-5" would hide the ~355 rows whose band is
//   "All". The `age` filter instead checks age_min <= age <= age_max, and
//   the backend back-fills age ranges from grade bands at ingest
//   (GRADE_TO_AGE in resource_service.py), so one well-chosen age matches
//   its own band, the "All" rows, and neighbours that genuinely overlap.
// - Door 3 (time) cannot be an API parameter — the API has no duration
//   filter. Durations are matched client-side over the items the API does
//   return (see BrowsePage). Only rows that list a duration participate;
//   the wizard counts them honestly before the visitor commits.
// - Door 2's "whole unit" maps to `scope`, not `resource_type`: scope is
//   the plan-size axis ("how much of a plan is this?").

import { Resource, searchResources } from "./api/client";
import type { Filters } from "./components/FilterBar";

export type DurationBucket = "lt20" | "period" | "long";

export const DURATION_LABELS: Record<DurationBucket, string> = {
  lt20: "Under 20 min",
  period: "About a class period (21–60 min)",
  long: "Longer than an hour",
};

export function durationInBucket(
  minutes: number | null | undefined,
  bucket: string
): boolean {
  if (minutes == null) return false;
  if (bucket === "lt20") return minutes <= 20;
  if (bucket === "period") return minutes > 20 && minutes <= 60;
  if (bucket === "long") return minutes > 60;
  return false;
}

export function bucketForMinutes(minutes: number): DurationBucket {
  if (minutes <= 20) return "lt20";
  if (minutes <= 60) return "period";
  return "long";
}

export interface DoorChoice {
  label: string;
  hint?: string;
  /** Filter fields this choice sets. `{}` = "no preference". */
  patch: Partial<Filters>;
}

export interface Door {
  key: string;
  question: string;
  sub?: string;
  choices: DoorChoice[];
}

export const DOORS: Door[] = [
  {
    key: "who",
    question: "Who are you teaching?",
    sub: "One tap — you can fine-tune everything later.",
    choices: [
      { label: "Little kids", hint: "Pre-K to grade 2", patch: { age: "5" } },
      { label: "Elementary", hint: "grades 3–5", patch: { age: "10" } },
      { label: "Middle school", hint: "grades 6–8", patch: { age: "12" } },
      { label: "Older students", hint: "grades 9–12", patch: { age: "16" } },
      { label: "Any age", patch: {} },
    ],
  },
  {
    key: "what",
    question: "What do you need?",
    choices: [
      {
        label: "A full lesson",
        hint: "a complete lesson plan",
        patch: { resource_type: "lesson plan" },
      },
      {
        label: "A quick activity or filler",
        hint: "something to run with a class",
        patch: { resource_type: "activity" },
      },
      {
        label: "Something hands-on",
        hint: "interactive or a simulation",
        patch: { resource_type: "interactive/sim" },
      },
      {
        label: "A whole unit",
        hint: "several lessons on one topic",
        patch: { scope: "unit" },
      },
      { label: "Surprise me — anything", patch: {} },
    ],
  },
  {
    key: "time",
    question: "How much time do you have?",
    sub: "Counts only the resources that list a running time.",
    choices: [
      { label: "Under 20 minutes", patch: { duration: "lt20" } },
      { label: "About a class period", patch: { duration: "period" } },
      { label: "Longer than an hour", patch: { duration: "long" } },
      { label: "Any length", patch: {} },
    ],
  },
];

export interface CuratedPath {
  title: string;
  hint: string;
  patch: Partial<Filters>;
}

// Hand-built starting points for visitors who don't want questions at all.
// Each is just a preset over the same Filters the doors produce.
export const CURATED_PATHS: CuratedPath[] = [
  {
    title: "New teacher, first month",
    hint: "Free, class-ready lessons you can teach tomorrow",
    patch: { cost: "free", scope: "lesson", classReady: true },
  },
  {
    // Any format, but short and class-ready: 83 results against the seed.
    // (Narrowing to activities too left only 14 — too thin for a headline
    // path, and a 15-minute video or reading fills the same gap.)
    title: "Friday afternoon emergency",
    hint: "Short, class-ready, and under 20 minutes",
    patch: { duration: "lt20", classReady: true },
  },
  {
    title: "Homeschool parent",
    hint: "Whole units to build your week around",
    patch: { scope: "unit" },
  },
  {
    title: "Going deep: full curricula",
    hint: "Publisher programs that run a whole term or year",
    patch: { scope: "curriculum" },
  },
];

/** Tally the duration buckets over everything a filter set matches — the
 *  honest counts the time door shows before the visitor picks one. */
export async function countDurations(
  query: Record<string, unknown>
): Promise<{ lt20: number; period: number; long: number; unknown: number }> {
  const counts = { lt20: 0, period: 0, long: 0, unknown: 0 };
  let offset = 0;
  let total = Infinity;
  while (offset < total && offset < 2000) {
    const res = await searchResources({ ...query, limit: 200, offset });
    total = res.total;
    for (const r of res.items as Resource[]) {
      if (r.duration_minutes == null) counts.unknown += 1;
      else if (r.duration_minutes <= 20) counts.lt20 += 1;
      else if (r.duration_minutes <= 60) counts.period += 1;
      else counts.long += 1;
    }
    offset += res.items.length;
    if (res.items.length === 0) break;
  }
  return counts;
}
