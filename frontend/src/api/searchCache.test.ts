import { test } from "node:test";
import assert from "node:assert/strict";
import { cachedLoad, SEARCH_CACHE_MS, type SearchCacheOptions } from "./searchCache.ts";

class MemoryStorage {
  items = new Map<string, string>();
  getItem(key: string): string | null {
    return this.items.get(key) ?? null;
  }
  setItem(key: string, value: string): void {
    this.items.set(key, value);
  }
}

function setup(start = 1_000) {
  let clock = start;
  const storage = new MemoryStorage();
  const opts: SearchCacheOptions = { storage, now: () => clock };
  return {
    storage,
    opts,
    advance: (ms: number) => (clock += ms),
  };
}

function counting<T>(value: T) {
  const calls = { n: 0 };
  const load = async () => {
    calls.n += 1;
    return value;
  };
  return { load, calls };
}

test("miss: first request calls the network and stores the result", async () => {
  const { opts, storage } = setup();
  const { load, calls } = counting({ total: 3, items: ["a"] });

  const got = await cachedLoad("almanac:search:q=fractions", load, opts);

  assert.deepEqual(got, { total: 3, items: ["a"] });
  assert.equal(calls.n, 1);
  assert.ok(storage.getItem("almanac:search:q=fractions"), "entry written");
});

test("hit: a repeat query inside the TTL returns from storage without loading", async () => {
  const { opts, advance } = setup();
  const { load, calls } = counting({ total: 3, items: ["a"] });

  await cachedLoad("almanac:search:q=fractions", load, opts);
  advance(SEARCH_CACHE_MS - 1);
  const again = await cachedLoad("almanac:search:q=fractions", load, opts);

  assert.deepEqual(again, { total: 3, items: ["a"] });
  assert.equal(calls.n, 1, "load ran only for the first request");
});

test("expiry: an entry older than the TTL is fetched again", async () => {
  const { opts, advance } = setup();
  const { load, calls } = counting({ total: 3, items: [] });

  await cachedLoad("almanac:search:q=fractions", load, opts);
  advance(SEARCH_CACHE_MS);
  await cachedLoad("almanac:search:q=fractions", load, opts);

  assert.equal(calls.n, 2);
});

test("keys are separate: a different query is a miss", async () => {
  const { opts } = setup();
  const { load, calls } = counting({ total: 0, items: [] });

  await cachedLoad("almanac:search:q=fractions", load, opts);
  await cachedLoad("almanac:search:q=photosynthesis", load, opts);

  assert.equal(calls.n, 2);
});

test("corrupt entry: treated as a miss and replaced", async () => {
  const { opts, storage } = setup();
  storage.setItem("almanac:search:q=x", "{not json");
  const { load, calls } = counting({ total: 1, items: [] });

  const got = await cachedLoad("almanac:search:q=x", load, opts);

  assert.deepEqual(got, { total: 1, items: [] });
  assert.equal(calls.n, 1);
  const again = await cachedLoad("almanac:search:q=x", load, opts);
  assert.deepEqual(again, { total: 1, items: [] });
  assert.equal(calls.n, 1, "replacement entry is a hit");
});

test("blocked storage: reads and writes fail quietly and the search still works", async () => {
  const broken = {
    getItem() {
      throw new Error("SecurityError");
    },
    setItem() {
      throw new Error("QuotaExceededError");
    },
  };
  const { load, calls } = counting({ total: 2, items: [] });

  const got = await cachedLoad("almanac:search:q=x", load, { storage: broken });

  assert.deepEqual(got, { total: 2, items: [] });
  assert.equal(calls.n, 1);
});
