"use client";

import { useEffect, useRef, useState } from "react";

// Spec: run-dashboard "Long pages offer a way back to the top".
const RADIUS = 19;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

export function BackToTop() {
  const [visible, setVisible] = useState(false);
  const ring = useRef<SVGCircleElement>(null);

  useEffect(() => {
    let frame = 0;
    const update = () => {
      frame = 0;
      const { scrollY, innerHeight } = window;
      setVisible(scrollY > innerHeight);
      // The ring is written straight to the DOM: it changes every frame while scrolling,
      // and a React render per frame would buy nothing.
      const room = document.documentElement.scrollHeight - innerHeight;
      const progress = room > 0 ? Math.min(scrollY / room, 1) : 0;
      ring.current?.style.setProperty("stroke-dashoffset", String(CIRCUMFERENCE * (1 - progress)));
    };
    const onScroll = () => {
      if (!frame) frame = requestAnimationFrame(update);
    };
    update();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
    };
  }, []);

  function toTop() {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    window.scrollTo({ top: 0, behavior: reduce ? "auto" : "smooth" });
  }

  return (
    <button
      type="button"
      onClick={toTop}
      aria-label="Back to top"
      title="Back to top"
      // Hidden but still mounted so it can fade; inert keeps it out of the tab order and
      // the accessibility tree until it shows.
      inert={!visible}
      className={`group fixed right-4 bottom-4 z-40 grid h-12 w-12 place-items-center rounded-full bg-ink text-white shadow-lg shadow-ink/25 transition duration-300 ease-out hover:-translate-y-0.5 hover:shadow-xl hover:shadow-ink/30 sm:right-6 sm:bottom-6 ${
        visible ? "translate-y-0 opacity-100" : "pointer-events-none translate-y-3 opacity-0"
      }`}
    >
      <svg aria-hidden viewBox="0 0 48 48" className="absolute inset-0 h-full w-full -rotate-90">
        <circle cx="24" cy="24" r={RADIUS} fill="none" stroke="currentColor" strokeOpacity="0.18" strokeWidth="2.5" />
        <circle
          ref={ring}
          cx="24"
          cy="24"
          r={RADIUS}
          fill="none"
          stroke="currentColor"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeDasharray={CIRCUMFERENCE}
          strokeDashoffset={CIRCUMFERENCE}
        />
      </svg>
      <svg
        aria-hidden
        viewBox="0 0 24 24"
        className="h-5 w-5 transition-transform duration-300 ease-out group-hover:-translate-y-0.5"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.25"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M12 19V5" />
        <path d="m5 12 7-7 7 7" />
      </svg>
    </button>
  );
}
