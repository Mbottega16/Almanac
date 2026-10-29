// sessionStorage cache for search responses. Repeat searches are answered
// without the network, which matters on Render's free tier, where a cold start
// can take about 40 seconds. Entries expire after 10 minutes, so a reload does
// not keep old results for the rest of the tab's life.
//
// No Vite-only imports here, so `node --test` can run the cache logic directly.

export const SEARCH_CACHE_MS = 10 * 60 * 1000;

export interface SearchCacheOptions {
  /** Defaults to the browser's sessionStorage. */
  storage?: Pick<Storage, "getItem" | "setItem">;
  now?: () => number;
  ttlMs?: number;
}

/**
 * Returns the cached response for `key` while it is fresh. Otherwise calls
 * `load`, stores the result, and returns it. Storage failures (blocked,
 * full, or corrupt entries) fall through to `load`, so search never breaks.
 */
export async function cachedLoad<T>(
  key: string,
  load: () => Promise<T>,
  opts: SearchCacheOptions = {}
): Promise<T> {
  const hit = readFresh<T>(key, opts);
  if (hit !== undefined) return hit;
  const data = await load();
  writeEntry(key, data, opts);
  return data;
}

function readFresh<T>(key: string, opts: SearchCacheOptions): T | undefined {
  try {
    const storage = opts.storage ?? sessionStorage;
    const raw = storage.getItem(key);
    if (!raw) return undefined;
    const { at, data } = JSON.parse(raw) as { at: number; data?: T };
    const now = (opts.now ?? Date.now)();
    return data !== undefined && now - at < (opts.ttlMs ?? SEARCH_CACHE_MS) ? data : undefined;
  } catch {
    return undefined;
  }
}

function writeEntry<T>(key: string, data: T, opts: SearchCacheOptions): void {
  try {
    const storage = opts.storage ?? sessionStorage;
    storage.setItem(key, JSON.stringify({ at: (opts.now ?? Date.now)(), data }));
  } catch {
    // Quota full or storage blocked: the search still works without the cache.
  }
}
