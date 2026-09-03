import { useEffect, useRef, useState } from "react";

import { searchResources } from "../api/client";
import { EMPTY_FILTERS, Filters, toQuery } from "../components/FilterBar";

// Only the string-valued filter keys can be a wizard step.
type StepKey = "subject" | "grade_band" | "scope" | "resource_type" | "cost" | "udl" | "q";

interface Choice {
  label: string;
  hint?: string;
  value: string;
}

interface Step {
  key: StepKey;
  question: string;
  sub?: string;
  choices: Choice[];
  /** free-text step instead of choice buttons */
  freeText?: boolean;
}

const STEPS: Step[] = [
  {
    key: "subject",
    question: "What subject are you planning for?",
    choices: [
      { label: "Math", value: "Math" },
      { label: "ELA / Reading", value: "ELA / Reading" },
      { label: "Science", value: "Science" },
      { label: "Social Studies", value: "Social Studies" },
      { label: "Arts", value: "Arts" },
      { label: "SEL", value: "SEL", hint: "social–emotional learning" },
      { label: "World Languages", value: "World Languages" },
      { label: "CS / STEM", value: "CS / STEM" },
      { label: "PE / Health", value: "PE / Health" },
      { label: "Any subject", value: "" },
    ],
  },
  {
    key: "grade_band",
    question: "Which learners?",
    choices: [
      { label: "Pre-K", hint: "ages 3–5", value: "PreK" },
      { label: "K–2", hint: "ages 5–8", value: "K-2" },
      { label: "Grades 3–5", hint: "ages 8–11", value: "3-5" },
      { label: "Grades 6–8", hint: "ages 11–14", value: "6-8" },
      { label: "Grades 9–12", hint: "ages 14–18", value: "9-12" },
      { label: "College / adult", value: "HigherEd/Adult" },
      { label: "Any age", value: "" },
    ],
  },
  {
    key: "scope",
    question: "How much are you planning?",
    sub: "A single class, or a whole program to run from.",
    choices: [
      { label: "One lesson or activity", hint: "a single class period", value: "lesson" },
      { label: "A unit", hint: "a few lessons on one topic", value: "unit" },
      { label: "A full course", hint: "a semester or year", value: "course" },
      {
        label: "A whole curriculum",
        hint: "a publisher's complete program",
        value: "curriculum",
      },
      { label: "Doesn't matter", value: "" },
    ],
  },
  {
    key: "resource_type",
    question: "What kind of resource do you want?",
    choices: [
      { label: "A full lesson plan or unit", value: "lesson plan" },
      { label: "A hands-on activity", value: "activity" },
      { label: "A project", value: "project" },
      { label: "A video", value: "video" },
      { label: "A reading or article", value: "article/text" },
      { label: "An interactive or simulation", value: "interactive/sim" },
      { label: "A worksheet or printable", value: "worksheet/printable" },
      { label: "Any format", value: "" },
    ],
  },
  {
    key: "cost",
    question: "Free only, or is paid okay?",
    choices: [
      { label: "Free only", value: "free" },
      { label: "Free is fine, but show paid too", value: "" },
    ],
  },
  {
    key: "udl",
    question: "Which part of the lesson are you building out?",
    sub: "Universal Design for Learning — pick the one you need most right now.",
    choices: [
      { label: "The hook", hint: "Engagement — the why", value: "engagement" },
      { label: "The content", hint: "Representation — the what", value: "representation" },
      {
        label: "What students produce",
        hint: "Action & Expression — the how",
        value: "action_expression",
      },
      { label: "Not sure / all three", value: "" },
    ],
  },
  {
    key: "q",
    question: "Any specific theme?",
    sub: "Optional — a topic, skill, or unit. Leave blank to skip.",
    freeText: true,
    choices: [],
  },
];

export default function DiscoverPage({
  onDone,
  onSkip,
}: {
  onDone: (filters: Filters) => void;
  onSkip: () => void;
}) {
  const [i, setI] = useState(0);
  const [filters, setFilters] = useState<Filters>(EMPTY_FILTERS);
  const [count, setCount] = useState<number | null>(null);
  const [text, setText] = useState("");
  // The last narrowing choice, so a dead-end run can undo it in one tap.
  const [lastPick, setLastPick] = useState<{ key: StepKey; label: string } | null>(null);
  const dragX = useRef<number | null>(null);

  const step = STEPS[i];
  const last = i === STEPS.length - 1;

  // Live "how many match so far" — the pinpoint feedback.
  useEffect(() => {
    let cancelled = false;
    searchResources(toQuery(filters))
      .then((r) => !cancelled && setCount(r.total))
      .catch(() => !cancelled && setCount(null));
    return () => {
      cancelled = true;
    };
  }, [filters]);

  const advance = () => (last ? finish(filters) : setI((n) => n + 1));
  const back = () => setI((n) => Math.max(0, n - 1));

  const pick = (value: string) => {
    const next = { ...filters, [step.key]: value };
    setFilters(next);
    const label = STEPS[i].choices.find((c) => c.value === value)?.label;
    setLastPick(value && label ? { key: step.key, label } : null);
    if (last) finish(next);
    else setI((n) => n + 1);
  };

  // Zero results: let them drop the choice that killed it and try again.
  const undoLast = () => {
    if (!lastPick) return;
    setFilters((f) => ({ ...f, [lastPick.key]: "" }));
    setLastPick(null);
    setI((n) => Math.max(0, n - 1));
  };

  const finish = (f: Filters) => onDone({ ...f, q: (f.q || text).trim() });

  // Pointer/touch swipe: drag left = next, right = back.
  const onDown = (e: React.PointerEvent) => (dragX.current = e.clientX);
  const onUp = (e: React.PointerEvent) => {
    if (dragX.current == null) return;
    const dx = e.clientX - dragX.current;
    dragX.current = null;
    if (dx < -60 && !last) advance();
    else if (dx > 60 && i > 0) back();
  };

  return (
    <div className="discover">
      <header className="discover-head">
        <span className="discover-brand">Almanac</span>
        <button className="discover-skip" onClick={onSkip}>
          Skip to browse →
        </button>
      </header>

      <div className="discover-progress">
        {STEPS.map((_, n) => (
          <span key={n} className={`discover-dot${n === i ? " on" : n < i ? " done" : ""}`} />
        ))}
      </div>

      <div className="discover-viewport" onPointerDown={onDown} onPointerUp={onUp}>
        <div
          className="discover-track"
          style={{ transform: `translateX(calc(-${i * 100}% - ${i * 1.5}rem))` }}
        >
          {STEPS.map((s, n) => (
            <section className="discover-panel" key={s.key} aria-hidden={n !== i}>
              <h1>{s.question}</h1>
              {s.sub && <p className="discover-sub">{s.sub}</p>}

              {s.freeText ? (
                <form
                  className="discover-freetext"
                  onSubmit={(e) => {
                    e.preventDefault();
                    finish(filters);
                  }}
                >
                  <input
                    type="text"
                    autoFocus={n === i}
                    placeholder="e.g. fractions, the water cycle, the Civil Rights Movement"
                    value={text}
                    onChange={(e) => setText(e.target.value)}
                  />
                  <button type="submit">Show me these resources →</button>
                </form>
              ) : (
                <div className="discover-choices">
                  {s.choices.map((c) => (
                    <button
                      key={c.label}
                      className={`discover-choice${
                        filters[s.key] === c.value ? " picked" : ""
                      }`}
                      onClick={() => pick(c.value)}
                    >
                      <span className="discover-choice-label">{c.label}</span>
                      {c.hint && <span className="discover-choice-hint">{c.hint}</span>}
                    </button>
                  ))}
                </div>
              )}
            </section>
          ))}
        </div>
      </div>

      <footer className="discover-foot">
        <button className="discover-nav" onClick={back} disabled={i === 0}>
          ← Back
        </button>
        {count === 0 && lastPick ? (
          <button className="discover-recover" onClick={undoLast}>
            Nothing matches — undo "{lastPick.label}"
          </button>
        ) : (
          <span className="discover-count">
            {count == null
              ? "…"
              : `${count} resource${count === 1 ? "" : "s"} match so far`}
          </span>
        )}
        <button className="discover-nav" onClick={advance}>
          {last ? "Done" : "Skip this →"}
        </button>
      </footer>
    </div>
  );
}
