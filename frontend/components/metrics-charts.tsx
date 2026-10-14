"use client";

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { formatCost } from "@/lib/format";
import type { Metrics } from "@/lib/types";

import { Panel, stateLabel } from "./ui";

// Model steps as the desk would name them.
const STEP_NAMES: Record<string, string> = {
  "intake.extract": "Reading the message",
  "intake.repair": "Fixing a reading",
  "records.extract": "Reading the certificate",
  "records.repair": "Fixing a certificate reading",
  "resolver.turn": "Finding options",
  "reply.extract": "Writing the reply",
  "reply.repair": "Fixing the reply",
};

export function MetricsCharts({ metrics }: { metrics: Metrics }) {
  const steps = metrics.model_steps.map((s) => ({
    name: STEP_NAMES[s.name] ?? s.name,
    cost: Number(s.cost_usd),
    seconds: s.average_seconds ?? 0,
  }));
  const states = Object.entries(metrics.requests_by_state).map(([state, count]) => ({
    name: stateLabel(state),
    count,
  }));

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <Panel title="Cost by model step">
        <Chart data={steps} y="cost" color="#5847c2" format={(v) => formatCost(v)} />
      </Panel>
      <Panel title="Average time per model step">
        <Chart data={steps} y="seconds" color="#2d5da8" format={(v) => `${v.toFixed(1)} s`} />
      </Panel>
      <Panel title="Requests by state" className="lg:col-span-2">
        <Chart data={states} y="count" color="#1f6f55" format={(v) => String(v)} />
      </Panel>
    </div>
  );
}

type Row = Record<string, string | number>;

function Chart({
  data,
  y,
  color,
  format,
}: {
  data: Row[];
  y: string;
  color: string;
  format: (value: number) => string;
}) {
  if (data.length === 0) return <p className="text-muted">No runs yet.</p>;
  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ left: 8, right: 24 }}>
          <CartesianGrid horizontal={false} stroke="#e3e8e1" />
          <XAxis type="number" tick={{ fontSize: 12, fill: "#5f6b7a" }} tickFormatter={(v: number) => format(v)} axisLine={false} tickLine={false} />
          <YAxis type="category" dataKey="name" width={170} tick={{ fontSize: 13, fill: "#1a2338" }} axisLine={false} tickLine={false} />
          <Tooltip formatter={(v) => format(Number(v))} cursor={{ fill: "#f6f8f5" }} />
          <Bar dataKey={y} fill={color} radius={[0, 6, 6, 0]} barSize={18} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
