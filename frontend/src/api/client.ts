export interface Resource {
  id: number;
  link: string;
  title: string | null;
  description: string | null;
  description_source: string;
  subject: string;
  grade_band: string | null;
  age_min: number | null;
  age_max: number | null;
  resource_type: string | null;
  scope: string;
  publisher: string | null;
  granularity: string;
  duration_minutes: number | null;
  materials: string | null;
  learning_outcomes: string[];
  cost: string;
  price_note: string | null;
  source_site: string | null;
  license: string | null;
  standards: string | null;
  standard_codes: string[];
  udl_rationale: string | null;
  /** 'students' = something you teach with; 'educators' = your own PD. */
  audience: Audience;
  credit_type: CreditType | null;
  credit_hours: number | null;
  credit_note: string | null;
  tags: string[];
  udl_principles: string[];
  source: string;
  link_status: string;
  link_checked_at: string | null;
  visited_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface LibraryStats {
  total: number;
  by_subject: NameCount[];
  by_cost: NameCount[];
  by_scope: NameCount[];
  by_link_status: NameCount[];
  subject_udl: Record<string, Record<string, number>>;
  thin_cells: { subject: string; principle: string; count: number }[];
}

export interface ResourceListResponse {
  total: number;
  items: Resource[];
  /** Query words the library has nothing for — shown so a search that can't
   *  be answered exactly says which part it couldn't answer. */
  unmatched_terms?: string[];
  matched_terms?: string[];
  /** True when the dead terms had to be dropped to return anything at all. */
  broadened?: boolean;
}

export interface NameCount {
  name: string;
  count: number;
}

export interface UdlCoverage {
  total: number;
  engagement: number;
  representation: number;
  action_expression: number;
  by_type: Record<string, number>;
}

export const UDL_PRINCIPLES = ["engagement", "representation", "action_expression"] as const;
export type UdlPrinciple = (typeof UDL_PRINCIPLES)[number];

export const UDL_LABELS: Record<UdlPrinciple, string> = {
  engagement: "Engagement",
  representation: "Representation",
  action_expression: "Action & Expression",
};

// How big a chunk of teaching a resource is. 'lesson' is the default and
// covers one-off lessons/activities; 'course'/'curriculum' are the
// commercial full programs.
export const SCOPES = ["lesson", "unit", "course", "curriculum"] as const;
export type Scope = (typeof SCOPES)[number];

export const SCOPE_LABELS: Record<Scope, string> = {
  lesson: "Single lesson",
  unit: "Unit",
  course: "Full course",
  curriculum: "Curriculum",
};

export type Audience = "students" | "educators";

export const CREDIT_TYPES = ["ceu", "pd_hours", "certificate", "graduate_credit"] as const;
export type CreditType = (typeof CREDIT_TYPES)[number];

export const CREDIT_LABELS: Record<CreditType, string> = {
  ceu: "CEU",
  pd_hours: "PD hours",
  certificate: "Certificate",
  graduate_credit: "Graduate credit",
};

/** "1.5 CEUs", "3 PD hours", "Certificate" — the badge text on a card. */
export function creditLabel(type: CreditType, hours: number | null): string {
  if (hours == null || type === "certificate") return CREDIT_LABELS[type];
  const unit = type === "ceu" ? (hours === 1 ? "CEU" : "CEUs") : CREDIT_LABELS[type];
  return `${hours} ${unit}`;
}

const BASE = import.meta.env.VITE_API_BASE_URL || "";

export class ApiError extends Error {
  constructor(public status: number, path: string) {
    super(`Request to ${path} failed: ${status}`);
  }
}

async function apiGet<T>(path: string): Promise<T> {
  const resp = await fetch(`${BASE}${path}`, { credentials: "include" });
  if (!resp.ok) throw new ApiError(resp.status, path);
  return resp.json();
}

async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  const resp = await fetch(`${BASE}${path}`, {
    method: "POST",
    credentials: "include",
    headers: body !== undefined ? { "Content-Type": "application/json" } : undefined,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!resp.ok) throw new ApiError(resp.status, path);
  return resp.json();
}

export interface ResourceQuery {
  q?: string;
  subject?: string;
  grade_band?: string;
  resource_type?: string;
  scope?: string;
  publisher?: string;
  granularity?: string;
  cost?: string;
  source_site?: string;
  udl?: string;
  tag?: string;
  standard?: string;
  age?: number | string;
  audience?: Audience;
  /** A specific credit type, or "any" for everything that grants credit. */
  credit_type?: string;
  limit?: number;
  offset?: number;
}

function toQs(params: Record<string, unknown>): string {
  return new URLSearchParams(
    Object.entries(params)
      .filter(([, v]) => v !== undefined && v !== "" && v !== false)
      .map(([k, v]) => [k, String(v)])
  ).toString();
}

// Repeat searches are answered from sessionStorage, so going back to a result
// skips the network. That matters on Render's free tier, where a cold start
// can take about 40 seconds. Entries expire after 10 minutes, so a reload
// does not keep old results for the rest of the tab's life.
const SEARCH_CACHE_PREFIX = "almanac:search:";
const SEARCH_CACHE_MS = 10 * 60 * 1000;

function readSearchCache(key: string): ResourceListResponse | null {
  try {
    const raw = sessionStorage.getItem(key);
    if (!raw) return null;
    const { at, data } = JSON.parse(raw) as { at: number; data: ResourceListResponse };
    return Date.now() - at < SEARCH_CACHE_MS ? data : null;
  } catch {
    return null; // storage blocked or corrupt: just fetch
  }
}

function writeSearchCache(key: string, data: ResourceListResponse): void {
  try {
    sessionStorage.setItem(key, JSON.stringify({ at: Date.now(), data }));
  } catch {
    // Quota full or storage blocked: the search still works without the cache.
  }
}

export async function searchResources(params: ResourceQuery): Promise<ResourceListResponse> {
  const qs = toQs(params as Record<string, unknown>);
  const key = `${SEARCH_CACHE_PREFIX}${qs}`;
  const cached = readSearchCache(key);
  if (cached) return cached;
  const data = await apiGet<ResourceListResponse>(`/api/resources?${qs}`);
  writeSearchCache(key, data);
  return data;
}

export function fetchSubjects(): Promise<NameCount[]> {
  return apiGet("/api/subjects");
}
export function fetchGradeBands(): Promise<NameCount[]> {
  return apiGet("/api/grade-bands");
}
export function fetchResourceTypes(): Promise<NameCount[]> {
  return apiGet("/api/resource-types");
}
export function fetchSources(): Promise<NameCount[]> {
  return apiGet("/api/sources");
}
export function fetchScopes(): Promise<NameCount[]> {
  return apiGet("/api/scopes");
}
export function fetchPublishers(): Promise<NameCount[]> {
  return apiGet("/api/publishers");
}
export function fetchTags(): Promise<NameCount[]> {
  return apiGet("/api/tags");
}
export function fetchStandards(): Promise<NameCount[]> {
  return apiGet("/api/standards");
}
export function fetchLibraryStats(): Promise<LibraryStats> {
  return apiGet("/api/stats");
}

export function fetchUdlCoverage(params: {
  q?: string;
  subject?: string;
  grade_band?: string;
  tag?: string;
  audience?: Audience;
}): Promise<UdlCoverage> {
  return apiGet(`/api/udl-coverage?${toQs(params)}`);
}

export function fetchAudiences(): Promise<NameCount[]> {
  return apiGet("/api/audiences");
}

export function randomResource(
  params: { subject?: string; tag?: string; cost?: string } = {}
): Promise<Resource> {
  const qs = toQs(params);
  return apiGet(`/api/resources/random${qs ? `?${qs}` : ""}`);
}

export function markVisited(id: number): Promise<Resource> {
  return apiPost(`/api/resources/${id}/visit`);
}

// --- auth gate (dormant unless the backend has ADMIN_PASSWORD set) ---

export function fetchAuthStatus(): Promise<{ gate_enabled: boolean }> {
  return apiGet("/api/auth-status");
}

export function login(password: string): Promise<{ ok?: boolean; detail?: string }> {
  return apiPost("/api/login", { password });
}

// --- live capture (dormant unless the backend has ANTHROPIC_API_KEY set) ---

export function fetchCaptureEnabled(): Promise<{ enabled: boolean }> {
  return apiGet("/api/capture/enabled");
}

export function researchLinks(
  links: string[],
  notes?: string
): Promise<{ drafts: ResourceDraft[] }> {
  return apiPost("/api/capture/research", { links, notes });
}

export type ResourceDraft = {
  link: string;
  title: string | null;
  description: string | null;
  description_source: string;
  subject: string;
  grade_band: string | null;
  age_min: number | null;
  age_max: number | null;
  resource_type: string | null;
  scope: string;
  publisher: string | null;
  granularity?: string;
  duration_minutes: number | null;
  materials: string | null;
  learning_outcomes: string[];
  cost: string;
  price_note: string | null;
  source_site: string | null;
  license: string | null;
  standards: string | null;
  evidence?: string | null;
  udl_rationale?: string | null;
  tags: string[];
  udl_principles: string[];
};

export function batchImport(items: ResourceDraft[]): Promise<{ created: Resource[]; updated: Resource[] }> {
  return apiPost("/api/resources/batch", items);
}
