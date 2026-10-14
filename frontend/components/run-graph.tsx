"use client";

import "@xyflow/react/dist/style.css";

import { Background, type Edge, type Node, Position, ReactFlow } from "@xyflow/react";

import { EDGES, NODES, type NodeId, type NodeStatus } from "@/lib/graph";

import { KIND_STYLE, NODE_STATUS_STYLE } from "./ui";

const POSITION: Record<NodeId, { x: number; y: number }> = {
  intake: { x: 0, y: 0 },
  records: { x: 0, y: 90 },
  compliance: { x: 165, y: 45 },
  capacity: { x: 330, y: 45 },
  route: { x: 495, y: 45 },
  resolver: { x: 660, y: 0 },
  reply: { x: 825, y: 45 },
  review: { x: 990, y: 0 },
  send: { x: 1155, y: 45 },
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
    const look = NODE_STATUS_STYLE[status];
    return {
      id: node.id,
      position: POSITION[node.id],
      sourcePosition: Position.Right,
      targetPosition: Position.Left,
      draggable: false,
      data: {
        label: (
          <div className="leading-tight">
            <div className="font-semibold">{node.label}</div>
            <div className="text-[10px] uppercase tracking-wide">
              {KIND_STYLE[node.kind].label} · {status}
            </div>
          </div>
        ),
      },
      className: status === "running" ? "animate-pulse" : undefined,
      style: {
        background: look.fill,
        color: look.text,
        border: `2px ${status === "skipped" ? "dashed" : "solid"} ${KIND_STYLE[node.kind].border}`,
        borderRadius: 10,
        width: 135,
        fontSize: 12,
        opacity: status === "skipped" ? 0.6 : 1,
      },
    };
  });
  const edges: Edge[] = EDGES.map(([source, target]) => ({
    id: `${source}-${target}`,
    source,
    target,
    animated: statuses[target] === "running",
    style: { stroke: "#a1a1aa" },
  }));

  return (
    <div className="h-56 w-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        fitView
        nodesConnectable={false}
        elementsSelectable={false}
        zoomOnScroll={false}
        panOnDrag={false}
        onNodeClick={(_, node) => onSelect(node.id as NodeId)}
      >
        <Background gap={24} color="#e4e4e7" />
      </ReactFlow>
    </div>
  );
}
