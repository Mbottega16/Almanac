// The canonical subject list. Kept flat for now — it's short enough to show
// as a chip row. If it ever grows past ~12, group it the way Atlas groups
// its categories (categoryGroups.ts). `subject` on Resource stays the source
// of truth; this is only display order.
export const SUBJECTS = [
  "Math",
  "ELA / Reading",
  "Science",
  "Social Studies",
  "Arts",
  "SEL",
  "World Languages",
  "CS / STEM",
  "PE / Health",
  "Other",
] as const;

export const GRADE_BANDS = [
  "PreK",
  "K-2",
  "3-5",
  "6-8",
  "9-12",
  "HigherEd/Adult",
  "All",
] as const;

export const RESOURCE_TYPES = [
  "lesson plan",
  "unit",
  "worksheet/printable",
  "video",
  "interactive/sim",
  "slides",
  "activity",
  "assessment",
  "project",
  "game",
  "article/text",
] as const;
