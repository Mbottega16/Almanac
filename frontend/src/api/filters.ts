// Pure filter logic: the filter state shape, its empty value, the filter ->
// API query translation, and the audience-switch reset. No React and no
// Vite-only imports, so `node --test` can run it directly.

import type { Audience } from "./client";

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
};

// Filters -> API query params. `classReady` is a UI convenience for
// `granularity=specific`; keep the translation in one place.
export function toQuery(f: Filters) {
  const { classReady, ...rest } = f;
  return { ...rest, granularity: classReady ? "specific" : "" };
}

// Switching audience resets every filter except the search text: the
// students-only and educators-only controls would otherwise carry over into
// a track they don't apply to.
export function switchAudience(filters: Filters, audience: Audience): Filters {
  return { ...EMPTY_FILTERS, audience, q: filters.q };
}
