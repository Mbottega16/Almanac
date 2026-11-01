import { test } from "node:test";
import assert from "node:assert/strict";
import { EMPTY_FILTERS, switchAudience, toQuery, type Filters } from "./filters.ts";

function withFilters(patch: Partial<Filters>): Filters {
  return { ...EMPTY_FILTERS, ...patch };
}

test("classReady on maps to granularity=specific and is not sent as its own param", () => {
  const query = toQuery(withFilters({ classReady: true }));

  assert.equal(query.granularity, "specific");
  assert.ok(!("classReady" in query), "UI-only flag stays out of the query");
});

test("classReady off sends no granularity filter", () => {
  const query = toQuery(withFilters({ classReady: false }));

  assert.equal(query.granularity, "");
  assert.ok(!("classReady" in query));
});

test("other filters pass through to the query unchanged", () => {
  const query = toQuery(
    withFilters({ q: "fractions", subject: "Math", udl: "engagement", classReady: true })
  );

  assert.equal(query.q, "fractions");
  assert.equal(query.subject, "Math");
  assert.equal(query.udl, "engagement");
  assert.equal(query.audience, "students");
});

test("switching audience clears audience-specific filters", () => {
  const before = withFilters({
    audience: "students",
    scope: "unit",
    udl: "representation",
    age: "8",
    classReady: true,
    subject: "Math",
    grade_band: "3-5",
    resource_type: "video",
    tag: "fractions",
    standard: "CCSS.MATH.3.NF.A.1",
    cost: "free",
  });

  const after = switchAudience(before, "educators");

  assert.equal(after.audience, "educators");
  assert.equal(after.scope, "");
  assert.equal(after.udl, "");
  assert.equal(after.age, "");
  assert.equal(after.classReady, false);
  assert.equal(after.subject, "");
  assert.equal(after.grade_band, "");
  assert.equal(after.resource_type, "");
  assert.equal(after.tag, "");
  assert.equal(after.standard, "");
  assert.equal(after.cost, "");
});

test("switching audience clears credit_type when moving to lesson planning", () => {
  const after = switchAudience(withFilters({ audience: "educators", credit_type: "ceu" }), "students");

  assert.equal(after.audience, "students");
  assert.equal(after.credit_type, "");
});

test("switching audience keeps the search text", () => {
  const after = switchAudience(withFilters({ q: "cheetah pre-K movement", udl: "action" }), "educators");

  assert.equal(after.q, "cheetah pre-K movement");
});

test("switching audience does not mutate the previous filters", () => {
  const before = withFilters({ audience: "students", scope: "lesson", q: "x" });

  switchAudience(before, "educators");

  assert.equal(before.audience, "students");
  assert.equal(before.scope, "lesson");
});

test("the classReady flag does not survive an audience switch into a query", () => {
  const after = switchAudience(withFilters({ classReady: true }), "educators");
  const query = toQuery(after);

  assert.equal(query.granularity, "");
});
