"use client";

import "@xyflow/react/dist/style.css";

import { Background, type Edge, type Node, Position, ReactFlow } from "@xyflow/react";

import { EDGES, NODES, type NodeId, type NodeStatus } from "@/lib/graph";

import { KIND_STYLE, NODE_STATUS_STYLE } from "./ui";

const POSITION: Record<NodeId, { x: number; y: number }> = {
  intake: { x: 0, y: 0 },
  records: { x: 0, y: 110 },
  compliance: { x: 210, y: 55 },
  capacity: { x: 420, y: 55 },
  route: { x: 630, y: 55 },
  resolver: { x: 840, y: 0 },
  reply: { x: 1050, y: 55 },
  review: { x: 1260, y: 0 },
  send: { x: 1470, y: 55 },
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
        width: 150,
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
    <div className="h-64 w-full">
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
