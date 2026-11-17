import { test } from "node:test";
import assert from "node:assert/strict";
import { EMPTY_FILTERS, groupStandardsByFramework, switchAudience, toQuery, type Filters } from "./filters.ts";
import type { StandardCount } from "./client.ts";

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

test("groupStandardsByFramework groups standards by framework using optgroup format", () => {
  const standards: StandardCount[] = [
    { name: "D2.CIV.1.K-2", code: "D2.CIV.1.K-2", framework: "C3", count: 1 },
    { name: "CCSS.MATH.3.NF.A.1", code: "CCSS.MATH.3.NF.A.1", framework: "CCSS", count: 2 },
    { name: "MS-LS1-1", code: "MS-LS1-1", framework: "NGSS", count: 3 },
  ];

  const grouped = groupStandardsByFramework(standards);
  assert.equal(grouped.length, 3);
  assert.equal(grouped[0].framework, "C3");
  assert.equal(grouped[0].items.length, 1);
  assert.equal(grouped[0].items[0].code, "D2.CIV.1.K-2");
  assert.equal(grouped[1].framework, "CCSS");
  assert.equal(grouped[1].items[0].code, "CCSS.MATH.3.NF.A.1");
  assert.equal(grouped[2].framework, "NGSS");
  assert.equal(grouped[2].items[0].code, "MS-LS1-1");
});

test("groupStandardsByFramework handles empty or missing framework gracefully", () => {
  assert.deepEqual(groupStandardsByFramework([]), []);

  const standards = [
    { name: "CUSTOM-1", code: "CUSTOM-1", framework: "", count: 1 },
  ] as StandardCount[];
  const grouped = groupStandardsByFramework(standards);
  assert.equal(grouped.length, 1);
  assert.equal(grouped[0].framework, "Other");
});

test("stats matrix filter patch produces valid query with subject and udl", () => {
  const statsFilter: Partial<Filters> = { subject: "Math", udl: "representation" };
  const combined: Filters = { ...EMPTY_FILTERS, ...statsFilter };
  const query = toQuery(combined);

  assert.equal(query.subject, "Math");
  assert.equal(query.udl, "representation");
  assert.equal(query.audience, "students");
  assert.equal(query.q, "");
});

test("theme filter updates query and explicitly clearing q resets query", () => {
  const withTheme = withFilters({ q: "fractions", subject: "Math" });
  assert.equal(toQuery(withTheme).q, "fractions");

  const cleared = { ...withTheme, q: "" };
  assert.equal(toQuery(cleared).q, "");
});

test("appending tag badge to active filter set preserves active filters and produces query with tag", () => {
  const active = withFilters({ subject: "Science", grade_band: "6-8", cost: "free" });
  const updated: Filters = { ...active, tag: "biology" };
  const query = toQuery(updated);

  assert.equal(query.subject, "Science");
  assert.equal(query.grade_band, "6-8");
  assert.equal(query.cost, "free");
  assert.equal(query.tag, "biology");
});

test("appending standard badge to active filter set preserves active filters and produces query with standard", () => {
  const active = withFilters({ subject: "Math", cost: "free", tag: "fractions" });
  const updated: Filters = { ...active, standard: "CCSS.MATH.CONTENT.6.RP.A.3" };
  const query = toQuery(updated);

  assert.equal(query.subject, "Math");
  assert.equal(query.cost, "free");
  assert.equal(query.tag, "fractions");
  assert.equal(query.standard, "CCSS.MATH.CONTENT.6.RP.A.3");
});

