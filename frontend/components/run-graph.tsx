"use client";

import "@xyflow/react/dist/style.css";

import {
  Background,
  type Edge,
  Handle,
  type Node,
  type NodeProps,
  Position,
  ReactFlow,
} from "@xyflow/react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { EDGES, NODES, type NodeId, type NodeStatus, type WorkflowNode } from "@/lib/graph";
import { stepSummary } from "@/lib/step-summary";
import type { RequestDetail } from "@/lib/types";

import { KIND_STYLE, NODE_STATUS_LABEL } from "./ui";

const POSITION: Record<NodeId, { x: number; y: number }> = {
  intake: { x: 0, y: 0 },
  records: { x: 0, y: 84 },
  compliance: { x: 156, y: 42 },
  capacity: { x: 312, y: 42 },
  route: { x: 468, y: 42 },
  resolver: { x: 624, y: 0 },
  reply: { x: 780, y: 42 },
  review: { x: 936, y: 0 },
  send: { x: 1092, y: 42 },
};

const TIP_WIDTH = 288;
const STEP_SIZE = { width: 132, height: 50 };
const HIDDEN_HANDLE = { opacity: 0, pointerEvents: "none" as const, border: 0, minWidth: 0, minHeight: 0 };

type StepData = {
  step: WorkflowNode;
  status: NodeStatus;
  description: string;
  onSelect: (id: NodeId) => void;
  onShow: (id: NodeId, el: HTMLElement) => void;
  onHide: (delay: number) => void;
};
type StepNode = Node<StepData, "step">;

/** One step of the path: a button, so it can be tabbed to, and opened with Enter. */
function Step({ data }: NodeProps<StepNode>) {
  const { step, status, description, onSelect, onShow, onHide } = data;
  const kind = KIND_STYLE[step.kind];
  const lit = status === "ok" || status === "running";
  const descriptionId = `step-${step.id}-description`;
  return (
    <>
      <Handle type="target" position={Position.Left} isConnectable={false} style={HIDDEN_HANDLE} />
      <button
        type="button"
        aria-label={`${step.label}: ${NODE_STATUS_LABEL[status]}`}
        aria-describedby={descriptionId}
        onClick={() => onSelect(step.id)}
        onMouseEnter={(e) => onShow(step.id, e.currentTarget)}
        onMouseLeave={() => onHide(120)}
        onFocus={(e) => onShow(step.id, e.currentTarget)}
        onBlur={() => onHide(0)}
        className={`nodrag flex h-full w-full items-center gap-2 text-left focus-visible:outline-offset-4 ${status === "running" ? "motion-safe:animate-pulse" : ""}`}
        style={{
          padding: "10px 12px",
          fontSize: 13,
          borderRadius: "8px 999px 999px 8px", // a kennel tag, like the state tags
          color: status === "error" ? "#c42b3e" : status === "skipped" ? "#8b95a3" : "#1a2338",
          background: status === "error" ? "#f9dfe3" : lit ? kind.soft : "#ffffff",
          border: `1.5px ${status === "skipped" ? "dashed" : "solid"} ${lit ? kind.color : "#d5dbd3"}`,
          boxShadow: status === "running" ? `0 0 0 4px ${kind.soft}` : "none",
        }}
      >
        <span
          aria-hidden
          className="h-2 w-2 shrink-0 rounded-full"
          style={{ background: status === "error" ? "#c42b3e" : lit ? kind.color : "#d5dbd3" }}
        />
        <span className="leading-tight">
          <span className="block font-semibold">{step.label}</span>
          <span className="block text-[11px] opacity-80">{NODE_STATUS_LABEL[status]}</span>
        </span>
        <span id={descriptionId} className="sr-only">
          {description}
        </span>
      </button>
      <Handle type="source" position={Position.Right} isConnectable={false} style={HIDDEN_HANDLE} />
    </>
  );
}

const nodeTypes = { step: Step };

export function RunGraph({
  statuses,
  detail,
  onSelect,
}: {
  statuses: Record<NodeId, NodeStatus>;
  detail: RequestDetail;
  onSelect: (node: NodeId) => void;
}) {
  const wrapper = useRef<HTMLDivElement>(null);
  const hideTimer = useRef<ReturnType<typeof setTimeout>>(undefined);
  const [tip, setTip] = useState<{ id: NodeId; left: number; top: number; width: number } | null>(null);

  // The tooltip sits in the wrapper, outside React Flow, which clips its own contents (D3).
  const show = useCallback((id: NodeId, el: HTMLElement) => {
    clearTimeout(hideTimer.current);
    const box = wrapper.current?.getBoundingClientRect();
    if (!box) return;
    const step = el.getBoundingClientRect();
    const width = Math.min(TIP_WIDTH, box.width);
    const left = Math.min(Math.max(0, step.left - box.left), box.width - width);
    setTip({ id, left, top: step.bottom - box.top + 8, width });
  }, []);
  const hide = useCallback((delay: number) => {
    clearTimeout(hideTimer.current);
    hideTimer.current = setTimeout(() => setTip(null), delay);
  }, []);

  useEffect(() => {
    if (!tip) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setTip(null);
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [tip]);
  useEffect(() => () => clearTimeout(hideTimer.current), []);

  // The run view re-renders several times a second while live; a stable callback keeps the
  // nodes below unchanged until the run itself changes.
  const selectRef = useRef(onSelect);
  useEffect(() => {
    selectRef.current = onSelect;
  }, [onSelect]);
  const select = useCallback((id: NodeId) => selectRef.current(id), []);

  const nodes = useMemo<StepNode[]>(
    () =>
      NODES.map((step) => {
        const summary = stepSummary(step.id, statuses[step.id], detail);
        return {
          id: step.id,
          type: "step",
          position: POSITION[step.id],
          // A fixed size: React Flow hides a replaced node until it measures it again, and a
          // hidden button loses keyboard focus.
          width: STEP_SIZE.width,
          height: STEP_SIZE.height,
          draggable: false,
          // React Flow ignores the pointer on nodes that can't be selected or dragged; steps are buttons.
          style: { pointerEvents: "all" },
          data: {
            step,
            status: statuses[step.id],
            description: `${summary.does} ${summary.result}`,
            onSelect: select,
            onShow: show,
            onHide: hide,
          },
        };
      }),
    [statuses, detail, select, show, hide],
  );
  const edges: Edge[] = EDGES.map(([source, target]) => {
    const done = statuses[target] === "ok" || statuses[target] === "running";
    return {
      id: `${source}-${target}`,
      source,
      target,
      animated: statuses[target] === "running",
      style: { stroke: done ? "#1a2338" : "#c9d0c7", strokeWidth: done ? 1.5 : 1 },
    };
  });

  const active = tip && NODES.find((n) => n.id === tip.id);
  const summary = active && stepSummary(active.id, statuses[active.id], detail);

  return (
    <div ref={wrapper} className="relative">
      <div className="h-52 w-full sm:h-60">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.04 }}
          minZoom={0.2} // the whole path fits a phone; the tooltips carry the detail
          nodesConnectable={false}
          nodesFocusable={false}
          edgesFocusable={false}
          elementsSelectable={false}
          zoomOnScroll={false}
          panOnDrag={false}
          onMove={() => setTip(null)}
        >
          <Background gap={28} size={1.5} color="#dfe5dd" />
        </ReactFlow>
      </div>
      {tip && active && summary && (
        <div
          role="tooltip"
          onMouseEnter={() => clearTimeout(hideTimer.current)}
          onMouseLeave={() => hide(120)}
          className="absolute z-20 rounded-xl bg-ink p-3 text-sm leading-snug text-white shadow-lg"
          style={{ left: tip.left, top: tip.top, width: tip.width }}
        >
          <p className="font-semibold">{active.label}</p>
          <p className="mt-1 text-white/75">{summary.does}</p>
          <p className="mt-2">{summary.result}</p>
        </div>
      )}
    </div>
  );
}
