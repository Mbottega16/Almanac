import { UDL_PRINCIPLES, UdlCoverage } from "../api/client";

const LABEL: Record<string, string> = {
  engagement: "Engagement",
  representation: "Representation",
  action_expression: "Action & Expression",
};

const BLURB: Record<string, string> = {
  engagement: "the why — hooks, choice, relevance",
  representation: "the what — video, text, visuals, audio",
  action_expression: "the how — build, write, perform, show",
};

/**
 * For the current theme search, shows how many matching resources support
 * each UDL principle. A thin or empty cell is a gap the teacher still needs
 * to fill. Clicking a cell filters results to that principle.
 */
export default function UdlCoverageStrip({
  coverage,
  active,
  onPick,
}: {
  coverage: UdlCoverage;
  active: string;
  onPick: (principle: string) => void;
}) {
  return (
    <div className="udl-coverage">
      <div className="udl-coverage-caption">
        UDL coverage for these {coverage.total} result{coverage.total === 1 ? "" : "s"}
      </div>
      <div className="udl-coverage-cells">
        {UDL_PRINCIPLES.map((p) => {
          const n = coverage[p];
          const thin = n === 0 ? " empty" : n <= 2 ? " thin" : "";
          return (
            <button
              key={p}
              className={`udl-coverage-cell udl-${p}${active === p ? " active" : ""}${thin}`}
              onClick={() => onPick(active === p ? "" : p)}
              title={
                n === 0
                  ? `No ${LABEL[p]} resources yet for this search — a gap to fill`
                  : `${n} support ${LABEL[p]}`
              }
            >
              <span className="udl-coverage-count">{n}</span>
              <span className="udl-coverage-name">{LABEL[p]}</span>
              <span className="udl-coverage-blurb">{BLURB[p]}</span>
            </button>
          );
        })}
      </div>
      {Object.keys(coverage.by_type).length > 0 && (
        <div className="udl-coverage-types">
          {Object.entries(coverage.by_type).map(([type, n]) => (
            <span key={type} className="tag-pill">
              {type} · {n}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
