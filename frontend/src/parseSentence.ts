// Plain-language search: turn a sentence like
//   "a 45-minute hands-on science activity for 4th graders"
// into the library's ordinary filters —
//   Science · Grade 4 · ~45 min · Hands-on
// plus whatever words are left over as the theme query. The parse is
// transparent on purpose: the UI shows every extracted chip and lets the
// visitor remove one before searching, because a parser that guesses
// silently is worse than the filter list it replaces.
//
// A specific grade maps to the `age` filter the same way door 1 does
// (typical age for the grade), so bands overlap instead of exact-matching.

import type { Filters } from "./components/FilterBar";
import { bucketForMinutes } from "./discovery";

export interface ParsedChip {
  id: string;
  label: string;
  patch: Partial<Filters>;
}

export interface ParsedSentence {
  chips: ParsedChip[];
  /** Leftover words the parser couldn't place — the theme query. */
  q: string;
}

const STOPWORDS = new Set([
  "a", "an", "the", "for", "me", "find", "show", "i", "need", "needs",
  "want", "wants", "looking", "look", "with", "about", "on", "of", "to",
  "please", "some", "any", "get", "give", "in", "my", "our", "something",
  "lesson", "lessons", "resource", "resources", "idea", "ideas", "whole",
]);

interface Rule {
  id: string;
  pattern: RegExp;
  /** Build the chip from the match. Return null to consume without a chip. */
  chip: (m: RegExpMatchArray) => { label: string; patch: Partial<Filters> } | null;
  /** Only the first rule of a given "slot" (subject/type/grade/…) fires. */
  slot: string;
}

const gradeAge = (grade: number) => String(grade + 5);

const RULES: Rule[] = [
  // --- time -------------------------------------------------------------
  {
    id: "duration-hours-decimal",
    slot: "duration",
    pattern: /\b(\d+(?:\.\d+)?)\s*(?:hours?|hrs?)\b/,
    chip: (m) => {
      const mins = Math.round(parseFloat(m[1]) * 60);
      return { label: `~${mins} min`, patch: { duration: bucketForMinutes(mins) } };
    },
  },
  {
    id: "duration-minutes",
    slot: "duration",
    pattern: /\b(\d+)\s*-?\s*(?:minutes?|mins?)\b/,
    chip: (m) => {
      const mins = parseInt(m[1], 10);
      return { label: `~${mins} min`, patch: { duration: bucketForMinutes(mins) } };
    },
  },
  {
    id: "duration-half-hour",
    slot: "duration",
    pattern: /\bhalf\s+(?:an\s+)?hour\b/,
    chip: () => ({ label: "~30 min", patch: { duration: bucketForMinutes(30) } }),
  },
  {
    id: "duration-hour-and-half",
    slot: "duration",
    pattern: /\ban?\s+hour\s+and\s+a\s+half\b/,
    chip: () => ({ label: "~90 min", patch: { duration: bucketForMinutes(90) } }),
  },
  {
    id: "duration-one-hour",
    slot: "duration",
    pattern: /\b(?:an|one)\s+hour\b/,
    chip: () => ({ label: "~60 min", patch: { duration: bucketForMinutes(60) } }),
  },
  // --- who ----------------------------------------------------------------
  {
    id: "grade-prek",
    slot: "who",
    pattern: /\b(?:pre[-\s]?k|preschool|pre[-\s]?kindergarten)\b/,
    chip: () => ({ label: "Pre-K / little kids", patch: { age: "5" } }),
  },
  {
    id: "grade-kindergarten",
    slot: "who",
    pattern: /\bkindergarten\b/,
    chip: () => ({ label: "Kindergarten", patch: { age: "6" } }),
  },
  {
    id: "grade-nth-graders",
    slot: "who",
    pattern: /\b(\d{1,2})(?:st|nd|rd|th)\s+graders?\b/,
    chip: (m) => ({ label: `Grade ${m[1]}`, patch: { age: gradeAge(+m[1]) } }),
  },
  {
    id: "grade-grade-n",
    slot: "who",
    pattern: /\bgrade\s+(\d{1,2})\b/,
    chip: (m) => ({ label: `Grade ${m[1]}`, patch: { age: gradeAge(+m[1]) } }),
  },
  {
    id: "grade-elementary",
    slot: "who",
    pattern: /\belementary\b/,
    chip: () => ({ label: "Elementary", patch: { age: "10" } }),
  },
  {
    id: "grade-middle",
    slot: "who",
    pattern: /\bmiddle\s+school\b/,
    chip: () => ({ label: "Middle school", patch: { age: "12" } }),
  },
  {
    id: "grade-high",
    slot: "who",
    pattern: /\bhigh\s+school\b/,
    chip: () => ({ label: "High school", patch: { age: "16" } }),
  },
  {
    id: "grade-little-kids",
    slot: "who",
    pattern: /\b(?:little|young)\s+kids\b|\btoddlers?\b/,
    chip: () => ({ label: "Little kids", patch: { age: "5" } }),
  },
  // --- subject (multi-word first, then single words) -----------------------
  {
    id: "subject-social-studies",
    slot: "subject",
    pattern: /\bsocial\s+studies\b|\bhistory\b/,
    chip: () => ({ label: "Social Studies", patch: { subject: "Social Studies" } }),
  },
  {
    id: "subject-sel",
    slot: "subject",
    pattern: /\bsocial[-\s]emotional\b|\bsel\b/,
    chip: () => ({ label: "SEL", patch: { subject: "SEL" } }),
  },
  {
    id: "subject-cs",
    slot: "subject",
    pattern: /\bcomputer\s+science\b|\bcoding\b|\bstem\b/,
    chip: () => ({ label: "CS / STEM", patch: { subject: "CS / STEM" } }),
  },
  {
    id: "subject-pe",
    slot: "subject",
    pattern: /\bphysical\s+education\b|\bpe\b|\bhealth\b/,
    chip: () => ({ label: "PE / Health", patch: { subject: "PE / Health" } }),
  },
  {
    id: "subject-lang",
    slot: "subject",
    pattern: /\bspanish\b|\bfrench\b|\bgerman\b|\bmandarin\b|\bworld\s+languages?\b/,
    chip: () => ({ label: "World Languages", patch: { subject: "World Languages" } }),
  },
  {
    id: "subject-science",
    slot: "subject",
    pattern: /\bscience\b/,
    chip: () => ({ label: "Science", patch: { subject: "Science" } }),
  },
  {
    id: "subject-math",
    slot: "subject",
    pattern: /\bmaths?\b|\bmathematics\b/,
    chip: () => ({ label: "Math", patch: { subject: "Math" } }),
  },
  {
    id: "subject-ela",
    slot: "subject",
    pattern: /\breading\b|\bela\b|\benglish\b|\bliteracy\b/,
    chip: () => ({ label: "ELA / Reading", patch: { subject: "ELA / Reading" } }),
  },
  {
    id: "subject-arts",
    slot: "subject",
    pattern: /\barts?\b|\bmusic\b/,
    chip: () => ({ label: "Arts", patch: { subject: "Arts" } }),
  },
  // --- cost -----------------------------------------------------------------
  {
    id: "cost-free",
    slot: "cost",
    pattern: /\bfree\b/,
    chip: () => ({ label: "Free", patch: { cost: "free" } }),
  },
  // --- what (format) --------------------------------------------------------
  {
    id: "type-hands-on",
    slot: "type",
    pattern: /\bhands[-\s]?on\b/,
    chip: () => ({
      label: "Hands-on",
      patch: { resource_type: "interactive/sim" },
    }),
  },
  {
    id: "type-worksheet",
    slot: "type",
    pattern: /\bworksheets?\b|\bprintables?\b/,
    chip: () => ({
      label: "Worksheet / printable",
      patch: { resource_type: "worksheet/printable" },
    }),
  },
  {
    id: "type-sim",
    slot: "type",
    pattern: /\bsimulations?\b|\binteractive\b/,
    chip: () => ({
      label: "Interactive / sim",
      patch: { resource_type: "interactive/sim" },
    }),
  },
  {
    id: "type-video",
    slot: "type",
    pattern: /\bvideos?\b/,
    chip: () => ({ label: "Video", patch: { resource_type: "video" } }),
  },
  {
    id: "type-project",
    slot: "type",
    pattern: /\bprojects?\b/,
    chip: () => ({ label: "Project", patch: { resource_type: "project" } }),
  },
  {
    id: "type-game",
    slot: "type",
    pattern: /\bgames?\b/,
    chip: () => ({ label: "Game", patch: { resource_type: "game" } }),
  },
  {
    id: "type-lesson-plan",
    slot: "type",
    pattern: /\blesson\s+plans?\b|\bfull\s+lesson\b/,
    chip: () => ({
      label: "Lesson plan",
      patch: { resource_type: "lesson plan" },
    }),
  },
  {
    id: "type-unit",
    slot: "type",
    pattern: /\bunits?\b/,
    chip: () => ({ label: "Whole unit", patch: { scope: "unit" } }),
  },
  {
    id: "type-article",
    slot: "type",
    pattern: /\barticles?\b/,
    chip: () => ({
      label: "Article / text",
      patch: { resource_type: "article/text" },
    }),
  },
  {
    id: "type-activity",
    slot: "type",
    pattern: /\bactivit(?:y|ies)\b/,
    chip: () => ({ label: "Activity", patch: { resource_type: "activity" } }),
  },
];

export function parseSentence(raw: string): ParsedSentence {
  let rest = ` ${raw.toLowerCase()} `;
  const chips: ParsedChip[] = [];
  const firedSlots = new Set<string>();

  for (const rule of RULES) {
    if (firedSlots.has(rule.slot)) continue;
    const m = rest.match(rule.pattern);
    if (!m || m.index == null) continue;
    firedSlots.add(rule.slot);
    const made = rule.chip(m);
    if (made) chips.push({ id: rule.id, label: made.label, patch: made.patch });
    rest = `${rest.slice(0, m.index)} ${rest.slice(m.index + m[0].length)}`;
    // "hands-on science activity": hands-on takes the format slot, and the
    // generic word "activity" next to it is packaging, not a second format
    // and not a theme word.
    if (rule.id === "type-hands-on") {
      rest = rest.replace(/\bactivit(?:y|ies)\b/, " ");
    }
  }

  // Display chips in a fixed reading order, not rule-firing order:
  // subject · who · time · format · cost.
  const SLOT_ORDER = ["subject", "who", "duration", "type", "cost"];
  const slotOf = (id: string) => RULES.find((r) => r.id === id)?.slot ?? "";
  chips.sort(
    (a, b) => SLOT_ORDER.indexOf(slotOf(a.id)) - SLOT_ORDER.indexOf(slotOf(b.id))
  );

  const q = rest
    .replace(/[^a-z0-9'\s-]/g, " ")
    .split(/\s+/)
    .filter((w) => w && !STOPWORDS.has(w))
    .join(" ")
    .trim();

  // Nothing understood: behave like the ordinary search box.
  if (chips.length === 0) return { chips, q: raw.trim() };
  return { chips, q };
}

/** Merge chip patches (in order) into one filter patch. */
export function chipsToPatch(chips: ParsedChip[]): Partial<Filters> {
  const patch: Partial<Filters> = {};
  for (const c of chips) Object.assign(patch, c.patch);
  return patch;
}
