"use client";

import { type ReactNode, useId, useState } from "react";

// Spec: run-dashboard "The worked example shows the attached vaccine card" and
// "The worked example shows what PawDesk did".

/**
 * Content behind a show/hide button. With `clip`, the content stays in the page and only
 * its top `clip` rem shows, fading out, until expanded; without it, the content is hidden.
 */
export function Expandable({
  showLabel,
  hideLabel,
  clip,
  children,
}: {
  showLabel: string;
  hideLabel: string;
  clip?: number;
  children: ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const id = useId();
  return (
    <>
      {clip === undefined ? (
        <div id={id} hidden={!open}>
          {children}
        </div>
      ) : (
        <div id={id} className="relative overflow-hidden" style={open ? undefined : { maxHeight: `${clip}rem` }}>
          {children}
          {!open && (
            <div aria-hidden className="pointer-events-none absolute inset-x-0 bottom-0 h-12 bg-linear-to-t from-surface to-transparent" />
          )}
        </div>
      )}
      <button
        type="button"
        aria-expanded={open}
        aria-controls={id}
        onClick={() => setOpen(!open)}
        className="mt-2 inline-flex items-center gap-1 text-sm font-medium text-kennel underline-offset-4 hover:underline"
      >
        {open ? hideLabel : showLabel}
        <svg aria-hidden viewBox="0 0 16 16" className={`h-3.5 w-3.5 transition-transform ${open ? "rotate-180" : ""}`}>
          <path d="M4 6l4 4 4-4" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>
    </>
  );
}
