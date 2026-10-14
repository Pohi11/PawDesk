import Markdown from "react-markdown";

// Renders repository markdown (proposals, requirements, decision records) with the
// dashboard's typography. No raw HTML: react-markdown ignores it by default.
export function Md({ children, compact = false }: { children: string; compact?: boolean }) {
  return (
    <div className={`space-y-2 text-sm leading-relaxed text-ink ${compact ? "" : "max-w-3xl"}`}>
      <Markdown
        components={{
          h1: ({ children }) => <h3 className="mt-4 text-base font-semibold text-ink">{children}</h3>,
          h2: ({ children }) => <h4 className="mt-4 font-semibold text-ink">{children}</h4>,
          h3: ({ children }) => <h5 className="mt-3 font-semibold text-ink">{children}</h5>,
          ul: ({ children }) => <ul className="list-disc space-y-1 pl-5">{children}</ul>,
          ol: ({ children }) => <ol className="list-decimal space-y-1 pl-5">{children}</ol>,
          code: ({ children }) => (
            <code className="rounded bg-wash px-1 py-0.5 font-mono text-[0.85em] text-ink">
              {children}
            </code>
          ),
          pre: ({ children }) => (
            <pre className="overflow-auto rounded-lg bg-wash p-3 text-xs">{children}</pre>
          ),
          a: ({ children, href }) => {
            // Links between decision records become anchors on the decisions page.
            const record = href?.match(/^(?:\.\/)?(\d{4})-[^/]*\.md$/);
            return (
              <a href={record ? `/build/decisions#adr-${record[1]}` : href} className="text-code underline">
                {children}
              </a>
            );
          },
          table: ({ children }) => (
            <div className="overflow-auto">
              <table className="w-full border-collapse text-xs">{children}</table>
            </div>
          ),
          th: ({ children }) => <th className="border border-rule bg-wash px-2 py-1 text-left">{children}</th>,
          td: ({ children }) => <td className="border border-rule px-2 py-1 align-top">{children}</td>,
        }}
      >
        {children}
      </Markdown>
    </div>
  );
}
