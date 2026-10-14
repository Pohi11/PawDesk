"use client";

import "@xyflow/react/dist/style.css";

import { Background, type Edge, type Node, Position, ReactFlow } from "@xyflow/react";

import { EDGES, NODES, type NodeId, type NodeStatus } from "@/lib/graph";

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

export function RunGraph({
  statuses,
  onSelect,
}: {
  statuses: Record<NodeId, NodeStatus>;
  onSelect: (node: NodeId) => void;
}) {
  const nodes: Node[] = NODES.map((node) => {
    const status = statuses[node.id];
    const kind = KIND_STYLE[node.kind];
    const lit = status === "ok" || status === "running";
    return {
      id: node.id,
      position: POSITION[node.id],
      sourcePosition: Position.Right,
      targetPosition: Position.Left,
      draggable: false,
      ariaLabel: `${node.label}: ${NODE_STATUS_LABEL[status]}`,
      data: {
        label: (
          <div className="flex items-center gap-2 text-left">
            <span
              aria-hidden
              className="h-2 w-2 shrink-0 rounded-full"
              style={{ background: status === "error" ? "#c42b3e" : lit ? kind.color : "#d5dbd3" }}
            />
            <div className="leading-tight">
              <div className="font-semibold">{node.label}</div>
              <div className="text-[11px] opacity-80">{NODE_STATUS_LABEL[status]}</div>
            </div>
          </div>
        ),
      },
      className: status === "running" ? "motion-safe:animate-pulse" : undefined,
      style: {
        width: 132,
        padding: "10px 12px",
        fontSize: 13,
        borderRadius: "8px 999px 999px 8px", // a kennel tag, like the state tags
        color: status === "error" ? "#c42b3e" : status === "skipped" ? "#8b95a3" : "#1a2338",
        background: status === "error" ? "#f9dfe3" : lit ? kind.soft : "#ffffff",
        border: `1.5px ${status === "skipped" ? "dashed" : "solid"} ${lit ? kind.color : "#d5dbd3"}`,
        boxShadow: status === "running" ? `0 0 0 4px ${kind.soft}` : "none",
      },
    };
  });
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

  return (
    <div className="h-52 w-full sm:h-60">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        fitView
        fitViewOptions={{ padding: 0.04 }}
        nodesConnectable={false}
        elementsSelectable={false}
        zoomOnScroll={false}
        panOnDrag={false}
        onNodeClick={(_, node) => onSelect(node.id as NodeId)}
      >
        <Background gap={28} size={1.5} color="#dfe5dd" />
      </ReactFlow>
    </div>
  );
}
