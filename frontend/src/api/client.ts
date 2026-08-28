export interface Resource {
  id: number;
  link: string;
  title: string | null;
  description: string | null;
  description_source: string;
  subject: string;
  grade_band: string | null;
  resource_type: string | null;
  cost: string;
  price_note: string | null;
  source_site: string | null;
  license: string | null;
  standards: string | null;
  tags: string[];
  udl_principles: string[];
  source: string;
  is_favorite: boolean;
  visited_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ResourceListResponse {
  total: number;
  items: Resource[];
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

const BASE = import.meta.env.VITE_API_BASE_URL || "";

async function apiGet<T>(path: string): Promise<T> {
  const resp = await fetch(`${BASE}${path}`);
  if (!resp.ok) throw new Error(`Request to ${path} failed: ${resp.status}`);
  return resp.json();
}

async function apiPost<T>(path: string): Promise<T> {
  const resp = await fetch(`${BASE}${path}`, { method: "POST" });
  if (!resp.ok) throw new Error(`Request to ${path} failed: ${resp.status}`);
  return resp.json();
}

export interface ResourceQuery {
  q?: string;
  subject?: string;
  grade_band?: string;
  resource_type?: string;
  cost?: string;
  source_site?: string;
  udl?: string;
  tag?: string;
  favorite?: boolean;
}

function toQs(params: Record<string, unknown>): string {
  return new URLSearchParams(
    Object.entries(params)
      .filter(([, v]) => v !== undefined && v !== "" && v !== false)
      .map(([k, v]) => [k, String(v)])
  ).toString();
}

export function searchResources(params: ResourceQuery): Promise<ResourceListResponse> {
  return apiGet(`/api/resources?${toQs(params as Record<string, unknown>)}`);
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
export function fetchTags(): Promise<NameCount[]> {
  return apiGet("/api/tags");
}

export function fetchUdlCoverage(params: {
  q?: string;
  subject?: string;
  grade_band?: string;
  tag?: string;
}): Promise<UdlCoverage> {
  return apiGet(`/api/udl-coverage?${toQs(params)}`);
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

export function setFavorite(id: number, favorite: boolean): Promise<Resource> {
  return apiPost(`/api/resources/${id}/favorite?favorite=${favorite}`);
}
