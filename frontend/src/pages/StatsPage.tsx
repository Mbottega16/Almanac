import { useEffect, useState } from "react";

import { LibraryStats, UDL_LABELS, UDL_PRINCIPLES, UdlPrinciple, fetchLibraryStats } from "../api/client";

export default function StatsPage() {
  const [stats, setStats] = useState<LibraryStats | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    fetchLibraryStats().then(setStats).catch(() => setError(true));
  }, []);

  if (error) return <p style={{ color: "crimson" }}>Couldn't load stats.</p>;
  if (!stats) return <p>Loading…</p>;

  const subjects = stats.by_subject.map((s) => s.name);
  const cell = (subj: string, p: string) => stats.subject_udl[subj]?.[p] ?? 0;
  const max = Math.max(1, ...subjects.flatMap((s) => UDL_PRINCIPLES.map((p) => cell(s, p))));

  return (
    <div className="stats-page">
      <h2>Library map — {stats.total} resources</h2>
      <p className="stats-sub">
        The per-search UDL strip tells you if a theme is covered. This tells you where the
        library itself is thin, so the next capture pass targets a real gap.
      </p>

      <h3>Subject × UDL principle</h3>
      <div className="stats-matrix" style={{ overflowX: "auto" }}>
        <table>
          <thead>
            <tr>
              <th>Subject</th>
              {UDL_PRINCIPLES.map((p) => (
                <th key={p}>{UDL_LABELS[p as UdlPrinciple]}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {subjects.map((s) => (
              <tr key={s}>
                <td>{s}</td>
                {UDL_PRINCIPLES.map((p) => {
                  const n = cell(s, p);
                  return (
                    <td
                      key={p}
                      className="stats-cell"
                      style={{ background: `rgba(70,130,180,${(n / max) * 0.75})` }}
                      title={`${n} ${s} resources support ${UDL_LABELS[p as UdlPrinciple]}`}
                    >
                      {n}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h3>Thinnest cells — fill these first</h3>
      <ul className="stats-thin">
        {stats.thin_cells.map((c, i) => (
          <li key={i}>
            <strong>{c.subject}</strong> · {UDL_LABELS[c.principle as UdlPrinciple] ?? c.principle}
            <span className="stats-thin-count"> — {c.count}</span>
          </li>
        ))}
      </ul>

      <div className="stats-breakdowns">
        <div>
          <h3>By subject</h3>
          <ul>
            {stats.by_subject.map((s) => (
              <li key={s.name}>
                {s.name} <span>{s.count}</span>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <h3>By cost</h3>
          <ul>
            {stats.by_cost.map((s) => (
              <li key={s.name}>
                {s.name} <span>{s.count}</span>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <h3>By scope</h3>
          <ul>
            {stats.by_scope.map((s) => (
              <li key={s.name}>
                {s.name} <span>{s.count}</span>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <h3>Link health</h3>
          <ul>
            {stats.by_link_status.map((s) => (
              <li key={s.name}>
                {s.name} <span>{s.count}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
