// Static SVG diagrams for the Architecture page (spec: run-dashboard). Server components:
// no hooks, no client JavaScript. Colors follow the dashboard's tokens, so a violet box
// means a model call here and in the run graph alike.

import type { ReactNode } from "react";

export type Tone = "llm" | "code" | "tool" | "human" | "plain" | "store" | "error";

// Full class names, so Tailwind finds them in the source.
const BOX: Record<Tone, string> = {
  llm: "fill-model-soft stroke-model",
  code: "fill-code-soft stroke-code",
  tool: "fill-tool-soft stroke-tool",
  human: "fill-signal-soft stroke-signal",
  plain: "fill-surface stroke-faint",
  store: "fill-wash stroke-ink",
  error: "fill-error-soft stroke-error",
};

export type Ink = "ink" | "code" | "staff" | "error" | "faint";

const LINE: Record<Ink, string> = {
  ink: "stroke-ink",
  code: "stroke-code",
  staff: "stroke-signal",
  error: "stroke-error",
  faint: "stroke-faint",
};

const HEAD: Record<Ink, string> = {
  ink: "fill-ink",
  code: "fill-code",
  staff: "fill-signal",
  error: "fill-error",
  faint: "fill-faint",
};

/**
 * One diagram: a heading that names it, the SVG, and a description screen readers get
 * with it. Below `minWidth` the drawing scrolls inside its frame, never the page.
 */
export function Diagram({
  id,
  title,
  description,
  caption,
  width,
  height,
  minWidth,
  className = "",
  children,
}: {
  id: string;
  title: string;
  description: ReactNode;
  caption?: string;
  width: number;
  height: number;
  minWidth?: number;
  className?: string;
  children: ReactNode;
}) {
  // A frame that can scroll is focusable, so a keyboard user can scroll it too.
  const scrolls = minWidth ? { tabIndex: 0, role: "region", "aria-labelledby": `${id}-title` } : {};
  return (
    <figure className={className}>
      <h3 id={`${id}-title`} className="text-lg font-semibold">
        {title}
      </h3>
      <div className="-mx-6 mt-4 overflow-x-auto bg-surface p-3 ring-1 ring-rule sm:mx-0 sm:rounded-2xl sm:p-6" {...scrolls}>
        <svg
          viewBox={`0 0 ${width} ${height}`}
          role="img"
          aria-labelledby={`${id}-title`}
          aria-describedby={`${id}-desc`}
          className="h-auto w-full"
          style={minWidth ? { minWidth } : undefined}
        >
          <defs>
            {(Object.keys(HEAD) as Ink[]).map((ink) => (
              <marker
                key={ink}
                id={`${id}-head-${ink}`}
                viewBox="0 0 10 10"
                refX="9"
                refY="5"
                markerUnits="userSpaceOnUse"
                markerWidth="10"
                markerHeight="10"
                orient="auto-start-reverse"
              >
                <path d="M0 0 L10 5 L0 10 z" className={HEAD[ink]} />
              </marker>
            ))}
          </defs>
          {children}
        </svg>
      </div>
      {caption && <p className="mt-3 text-sm text-faint">{caption}</p>}
      <div id={`${id}-desc`} className="sr-only">
        {description}
      </div>
    </figure>
  );
}

/** A rounded box with a title and up to two lines under it, centered. */
export function Box({
  x,
  y,
  w,
  h,
  tone,
  title,
  sub = [],
  dashed = false,
  ring = false,
}: {
  x: number;
  y: number;
  w: number;
  h: number;
  tone: Tone;
  title: string;
  sub?: string[];
  dashed?: boolean;
  ring?: boolean;
}) {
  const lines = sub.length;
  const titleY = y + h / 2 + 5 - lines * 8.5;
  return (
    <g>
      {ring && <rect x={x - 5} y={y - 5} width={w + 10} height={h + 10} rx={14} className="fill-none stroke-kennel" strokeWidth={2} />}
      <rect
        x={x}
        y={y}
        width={w}
        height={h}
        rx={10}
        className={BOX[tone]}
        strokeWidth={1.5}
        strokeDasharray={dashed ? "5 4" : undefined}
      />
      <text x={x + w / 2} y={titleY} textAnchor="middle" className="fill-ink text-[16px] font-semibold">
        {title}
      </text>
      {sub.map((line, i) => (
        <text key={line} x={x + w / 2} y={titleY + 19 + i * 16} textAnchor="middle" className="fill-muted text-[13.5px]">
          {line}
        </text>
      ))}
    </g>
  );
}

/** A database: a cylinder with a title and one line under it. */
export function Store({ x, y, w, h, title, sub }: { x: number; y: number; w: number; h: number; title: string; sub?: string }) {
  const ry = 9;
  return (
    <g>
      <path
        d={`M${x} ${y + ry} A${w / 2} ${ry} 0 0 1 ${x + w} ${y + ry} V${y + h - ry} A${w / 2} ${ry} 0 0 1 ${x} ${y + h - ry} Z`}
        className={BOX.store}
        strokeWidth={1.5}
      />
      <path d={`M${x} ${y + ry} A${w / 2} ${ry} 0 0 0 ${x + w} ${y + ry}`} className="fill-none stroke-ink" strokeWidth={1.5} />
      <text x={x + w / 2} y={y + h / 2 + 8} textAnchor="middle" className="fill-ink text-[16px] font-semibold">
        {title}
      </text>
      {sub && (
        <text x={x + w / 2} y={y + h / 2 + 26} textAnchor="middle" className="fill-muted text-[13.5px]">
          {sub}
        </text>
      )}
    </g>
  );
}

/** A line along `d` with an arrowhead at its end, optionally labeled at (lx, ly). */
export function Arrow({
  diagram,
  d,
  ink = "ink",
  heavy = false,
  dashed = false,
  label,
  lx,
  ly,
  anchor = "middle",
}: {
  diagram: string;
  d: string;
  ink?: Ink;
  heavy?: boolean;
  dashed?: boolean;
  label?: string;
  lx?: number;
  ly?: number;
  anchor?: "start" | "middle" | "end";
}) {
  return (
    <g>
      <path
        d={d}
        className={`fill-none ${LINE[ink]}`}
        strokeWidth={heavy ? 3 : 1.5}
        strokeDasharray={dashed ? "5 4" : undefined}
        markerEnd={`url(#${diagram}-head-${ink})`}
      />
      {label && lx !== undefined && ly !== undefined && <Note x={lx} y={ly} anchor={anchor}>{label}</Note>}
    </g>
  );
}

/** Small text on the drawing, with a paper-colored halo so it stays readable over lines. */
export function Note({
  x,
  y,
  anchor = "start",
  muted = true,
  children,
}: {
  x: number;
  y: number;
  anchor?: "start" | "middle" | "end";
  muted?: boolean;
  children: ReactNode;
}) {
  return (
    <text
      x={x}
      y={y}
      textAnchor={anchor}
      className={`${muted ? "fill-muted" : "fill-ink"} stroke-surface text-[13px]`}
      strokeWidth={4}
      paintOrder="stroke"
      strokeLinejoin="round"
    >
      {children}
    </text>
  );
}
