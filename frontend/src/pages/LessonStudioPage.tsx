import { ChangeEvent, useEffect, useMemo, useRef, useState } from "react";

import {
  NameCount,
  Resource,
  UDL_LABELS,
  UDL_PRINCIPLES,
  UdlPrinciple,
  fetchGradeBands,
  fetchSubjects,
  searchResources,
} from "../api/client";
import { UDL_OPTIONS } from "../udlOptions";

// A lesson here is the teacher's own adapted plan. It keeps a link to the library lesson it
// started from (a pointer, never the lesson's text), the UDL moves the teacher chose, their
// notes, and any companion resources. It lives in this browser; Export keeps it safe.
const STORE_KEY = "almanac.studio";

interface Companion {
  id: number;
  title: string;
  link: string;
  principle: UdlPrinciple;
}

interface MyLesson {
  id: string;
  title: string;
  subject: string;
  grade_band: string;
  minutes: number | null;
  goal: string;
  baseTitle: string;
  baseLink: string;
  tweaks: Record<UdlPrinciple, string[]>;
  notes: Record<UdlPrinciple, string>;
  companions: Companion[];
  updated: string;
}

const emptyByPrinciple = <T,>(make: () => T): Record<UdlPrinciple, T> => ({
  engagement: make(),
  representation: make(),
  action_expression: make(),
});

function blankLesson(): MyLesson {
  return {
    id: `l${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`,
    title: "",
    subject: "",
    grade_band: "",
    minutes: null,
    goal: "",
    baseTitle: "",
    baseLink: "",
    tweaks: emptyByPrinciple<string[]>(() => []),
    notes: emptyByPrinciple<string>(() => ""),
    companions: [],
    updated: new Date().toISOString(),
  };
}

// Older or imported data may miss a field; fill it so the editor never crashes.
function normalize(raw: Partial<MyLesson>): MyLesson {
  const base = blankLesson();
  const out: MyLesson = { ...base, ...raw, tweaks: { ...base.tweaks }, notes: { ...base.notes } };
  for (const p of UDL_PRINCIPLES) {
    out.tweaks[p] = Array.isArray(raw.tweaks?.[p]) ? (raw.tweaks![p] as string[]) : [];
    out.notes[p] = typeof raw.notes?.[p] === "string" ? (raw.notes![p] as string) : "";
  }
  out.companions = Array.isArray(raw.companions) ? raw.companions : [];
  return out;
}

function load(): MyLesson[] {
  try {
    const parsed = JSON.parse(localStorage.getItem(STORE_KEY) || "[]");
    return Array.isArray(parsed) ? parsed.map(normalize) : [];
  } catch {
    return [];
  }
}

function save(items: MyLesson[]) {
  try {
    localStorage.setItem(STORE_KEY, JSON.stringify(items));
  } catch {
    // per-viewer convenience only
  }
}

function toText(l: MyLesson): string {
  const lines = [`# ${l.title || "Untitled lesson"}`];
  const facts = [l.subject, l.grade_band, l.minutes ? `${l.minutes} min` : ""].filter(Boolean).join(" · ");
  if (facts) lines.push(facts);
  if (l.baseLink) lines.push(`Based on: ${l.baseTitle || l.baseLink} (${l.baseLink})`);
  if (l.goal) lines.push("", `**Goal:** ${l.goal}`);
  for (const p of UDL_PRINCIPLES) {
    lines.push("", `## ${UDL_LABELS[p]}`);
    for (const o of UDL_OPTIONS[p]) if (l.tweaks[p].includes(o.key)) lines.push(`- ${o.label}`);
    if (l.notes[p].trim()) lines.push("", l.notes[p].trim());
    const extra = l.companions.filter((c) => c.principle === p);
    if (extra.length) lines.push("", "Resources:", ...extra.map((c) => `- ${c.title} (${c.link})`));
  }
  return lines.join("\n");
}

function download(name: string, text: string, type: string) {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
}

export default function LessonStudioPage() {
  const [lessons, setLessons] = useState<MyLesson[]>(load);
  const [currentId, setCurrentId] = useState<string | null>(() => load()[0]?.id ?? null);
  const [message, setMessage] = useState("");
  const importRef = useRef<HTMLInputElement>(null);

  useEffect(() => save(lessons), [lessons]);

  const current = lessons.find((l) => l.id === currentId) ?? null;

  const update = (patch: Partial<MyLesson>) =>
    setLessons((all) =>
      all.map((l) => (l.id === currentId ? { ...l, ...patch, updated: new Date().toISOString() } : l))
    );

  const add = (l: MyLesson) => {
    setLessons((all) => [l, ...all]);
    setCurrentId(l.id);
  };

  const remove = () => {
    if (!current || !window.confirm(`Delete "${current.title || "Untitled lesson"}"?`)) return;
    const rest = lessons.filter((l) => l.id !== current.id);
    setLessons(rest);
    setCurrentId(rest[0]?.id ?? null);
  };

  const onImport = async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    try {
      const data = JSON.parse(await file.text());
      const incoming: MyLesson[] = (Array.isArray(data) ? data : [data]).map(normalize);
      const have = new Set(lessons.map((l) => l.id));
      const fresh = incoming.filter((l) => !have.has(l.id));
      setLessons((all) => [...fresh, ...all]);
      setMessage(`Imported ${fresh.length} lesson${fresh.length === 1 ? "" : "s"}.`);
    } catch {
      setMessage("That file is not a lesson export.");
    }
  };

  return (
    <div className="studio">
      <aside className="studio-side">
        <button className="studio-primary" onClick={() => add(blankLesson())}>
          + New lesson
        </button>
        <Picker onPick={add} />
        <ul className="studio-list">
          {lessons.map((l) => (
            <li key={l.id}>
              <button className={l.id === currentId ? "active" : ""} onClick={() => setCurrentId(l.id)}>
                <strong>{l.title || "Untitled lesson"}</strong>
                <span>{[l.subject, l.grade_band].filter(Boolean).join(" · ") || "No subject yet"}</span>
              </button>
            </li>
          ))}
        </ul>
        <div className="studio-io">
          <button onClick={() => download("my-lessons.json", JSON.stringify(lessons, null, 2), "application/json")} disabled={!lessons.length}>
            Export all
          </button>
          <button onClick={() => importRef.current?.click()}>Import</button>
          <input ref={importRef} type="file" accept="application/json" hidden onChange={onImport} />
        </div>
        <p className="studio-note">
          Lessons are saved in this browser only. Use Export all to keep a copy or move them to another computer.
        </p>
        {message && <p className="studio-note" role="status">{message}</p>}
      </aside>

      <section className="studio-main">
        {!current ? (
          <div className="studio-empty">
            <h2>Adapt a lesson with UDL</h2>
            <p>
              Start from a lesson in the library, or write your own. Then pick the ways you will widen it for
              different learners. Each choice is saved as part of your lesson plan.
            </p>
          </div>
        ) : (
          <Editor key={current.id} lesson={current} onChange={update} onDelete={remove} />
        )}
      </section>
    </div>
  );
}

function Picker({ onPick }: { onPick: (l: MyLesson) => void }) {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const [subject, setSubject] = useState("");
  const [grade, setGrade] = useState("");
  const [subjects, setSubjects] = useState<NameCount[]>([]);
  const [grades, setGrades] = useState<NameCount[]>([]);
  const [items, setItems] = useState<Resource[]>([]);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!open || subjects.length) return;
    fetchSubjects().then(setSubjects).catch(() => {});
    fetchGradeBands().then(setGrades).catch(() => {});
  }, [open, subjects.length]);

  useEffect(() => {
    if (!open) return;
    setBusy(true);
    const t = setTimeout(() => {
      searchResources({ q, subject, grade_band: grade, scope: "lesson", granularity: "specific", audience: "students", limit: 12 })
        .then((r) => setItems(r.items))
        .catch(() => setItems([]))
        .finally(() => setBusy(false));
    }, 250);
    return () => clearTimeout(t);
  }, [open, q, subject, grade]);

  const start = (r: Resource) => {
    const l = blankLesson();
    l.title = r.title || "";
    l.subject = r.subject || "";
    l.grade_band = r.grade_band || "";
    l.minutes = r.duration_minutes;
    l.goal = r.learning_outcomes[0] || "";
    l.baseTitle = r.title || "";
    l.baseLink = r.link;
    onPick(l);
    setOpen(false);
  };

  return (
    <div className="studio-picker">
      <button onClick={() => setOpen((v) => !v)} aria-expanded={open}>
        {open ? "Close library" : "Start from a library lesson"}
      </button>
      {open && (
        <div className="studio-picker-body">
          <input placeholder="Search lessons" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search lessons" />
          <select value={subject} onChange={(e) => setSubject(e.target.value)} aria-label="Subject">
            <option value="">Any subject</option>
            {subjects.map((s) => (
              <option key={s.name} value={s.name}>{s.name}</option>
            ))}
          </select>
          <select value={grade} onChange={(e) => setGrade(e.target.value)} aria-label="Grade band">
            <option value="">Any grade</option>
            {grades.map((g) => (
              <option key={g.name} value={g.name}>{g.name}</option>
            ))}
          </select>
          {busy && <p className="studio-note">Searching…</p>}
          <ul>
            {items.map((r) => (
              <li key={r.id}>
                <button onClick={() => start(r)}>
                  <strong>{r.title || r.link}</strong>
                  <span>
                    {[r.subject, r.grade_band, r.duration_minutes ? `${r.duration_minutes} min` : ""].filter(Boolean).join(" · ")}
                  </span>
                </button>
              </li>
            ))}
            {!busy && !items.length && <li className="studio-note">No lessons match.</li>}
          </ul>
        </div>
      )}
    </div>
  );
}

function Editor({ lesson, onChange, onDelete }: { lesson: MyLesson; onChange: (p: Partial<MyLesson>) => void; onDelete: () => void }) {
  const [copied, setCopied] = useState(false);
  const covered = useMemo(() => UDL_PRINCIPLES.filter((p) => lesson.tweaks[p].length > 0), [lesson.tweaks]);

  const toggle = (p: UdlPrinciple, key: string) => {
    const has = lesson.tweaks[p].includes(key);
    onChange({ tweaks: { ...lesson.tweaks, [p]: has ? lesson.tweaks[p].filter((k) => k !== key) : [...lesson.tweaks[p], key] } });
  };

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(toText(lesson));
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      download(`${lesson.title || "lesson"}.md`, toText(lesson), "text/markdown");
    }
  };

  return (
    <div className="studio-editor">
      <div className="studio-bar">
        <div className="studio-cover" aria-label="UDL coverage">
          {UDL_PRINCIPLES.map((p) => (
            <span key={p} className={`udl-pill udl-${p}${covered.includes(p) ? "" : " absent"}`}>
              {UDL_LABELS[p]}
              {covered.includes(p) ? " ✓" : " —"}
            </span>
          ))}
        </div>
        <div className="studio-actions">
          <button onClick={copy}>{copied ? "Copied" : "Copy as text"}</button>
          <button onClick={() => download(`${lesson.title || "lesson"}.md`, toText(lesson), "text/markdown")}>Download .md</button>
          <button onClick={() => download(`${lesson.title || "lesson"}.json`, JSON.stringify(lesson, null, 2), "application/json")}>Export</button>
          <button className="danger" onClick={onDelete}>Delete</button>
        </div>
      </div>

      <div className="studio-basics">
        <label className="wide">
          Lesson title
          <input value={lesson.title} onChange={(e) => onChange({ title: e.target.value })} placeholder="e.g. Fractions on a number line" />
        </label>
        <label>
          Subject
          <input value={lesson.subject} onChange={(e) => onChange({ subject: e.target.value })} />
        </label>
        <label>
          Grade
          <input value={lesson.grade_band} onChange={(e) => onChange({ grade_band: e.target.value })} placeholder="e.g. 3-5" />
        </label>
        <label>
          Minutes
          <input
            type="number"
            min={0}
            value={lesson.minutes ?? ""}
            onChange={(e) => onChange({ minutes: e.target.value === "" ? null : Math.max(0, Number(e.target.value)) })}
          />
        </label>
        <label className="wide">
          Learning goal
          <textarea rows={2} value={lesson.goal} onChange={(e) => onChange({ goal: e.target.value })} placeholder="Students will be able to…" />
        </label>
        {lesson.baseLink && (
          <p className="studio-base wide">
            Based on <a href={lesson.baseLink} target="_blank" rel="noreferrer">{lesson.baseTitle || lesson.baseLink}</a>. The lesson text stays at the source.
          </p>
        )}
      </div>

      {UDL_PRINCIPLES.map((p) => (
        <PrincipleCard key={p} principle={p} lesson={lesson} onToggle={(k) => toggle(p, k)} onChange={onChange} />
      ))}
    </div>
  );
}

function PrincipleCard({
  principle,
  lesson,
  onToggle,
  onChange,
}: {
  principle: UdlPrinciple;
  lesson: MyLesson;
  onToggle: (key: string) => void;
  onChange: (p: Partial<MyLesson>) => void;
}) {
  const [found, setFound] = useState<Resource[] | null>(null);
  const [busy, setBusy] = useState(false);
  const mine = lesson.companions.filter((c) => c.principle === principle);

  const find = async () => {
    setBusy(true);
    try {
      const r = await searchResources({
        subject: lesson.subject || undefined,
        grade_band: lesson.grade_band || undefined,
        udl: principle,
        audience: "students",
        granularity: "specific",
        limit: 6,
      });
      const taken = new Set(lesson.companions.map((c) => c.id));
      setFound(r.items.filter((i) => !taken.has(i.id) && i.link !== lesson.baseLink));
    } catch {
      setFound([]);
    } finally {
      setBusy(false);
    }
  };

  const attach = (r: Resource) => {
    onChange({ companions: [...lesson.companions, { id: r.id, title: r.title || r.link, link: r.link, principle }] });
    setFound((f) => (f ? f.filter((x) => x.id !== r.id) : f));
  };

  return (
    <section className={`studio-card studio-${principle}`}>
      <h3>{UDL_LABELS[principle]}</h3>
      <ul className="studio-options">
        {UDL_OPTIONS[principle].map((o) => (
          <li key={o.key}>
            <label>
              <input type="checkbox" checked={lesson.tweaks[principle].includes(o.key)} onChange={() => onToggle(o.key)} />
              <span>
                <strong>{o.label}</strong>
                <small>{o.hint}</small>
              </span>
            </label>
          </li>
        ))}
      </ul>
      <label className="studio-notes">
        How I will do this
        <textarea
          rows={3}
          value={lesson.notes[principle]}
          onChange={(e) => onChange({ notes: { ...lesson.notes, [principle]: e.target.value } })}
          placeholder="Your own notes for this class"
        />
      </label>
      {mine.length > 0 && (
        <ul className="studio-companions">
          {mine.map((c) => (
            <li key={c.id}>
              <a href={c.link} target="_blank" rel="noreferrer">{c.title}</a>
              <button onClick={() => onChange({ companions: lesson.companions.filter((x) => x.id !== c.id) })} aria-label={`Remove ${c.title}`}>✕</button>
            </li>
          ))}
        </ul>
      )}
      <button className="studio-find" onClick={find} disabled={busy}>
        {busy ? "Searching…" : `Find ${UDL_LABELS[principle]} resources`}
      </button>
      {found && (
        <ul className="studio-found">
          {found.length === 0 && <li className="studio-note">Nothing new found for this lesson.</li>}
          {found.map((r) => (
            <li key={r.id}>
              <a href={r.link} target="_blank" rel="noreferrer">
                {r.title || r.link}
              </a>
              <span>{[r.subject, r.grade_band, r.resource_type].filter(Boolean).join(" · ")}</span>
              <button onClick={() => attach(r)}>Add</button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
