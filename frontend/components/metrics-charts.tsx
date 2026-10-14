"use client";

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { formatCost } from "@/lib/format";
import type { Metrics } from "@/lib/types";

import { Card } from "./ui";

export function MetricsCharts({ metrics }: { metrics: Metrics }) {
  const steps = metrics.model_steps.map((s) => ({
    name: s.name,
    cost: Number(s.cost_usd),
    calls: s.calls,
    seconds: s.average_seconds ?? 0,
  }));
  const states = Object.entries(metrics.requests_by_state).map(([state, count]) => ({
    state: state.replace("_", " "),
    count,
  }));

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <Card title="Model cost per step (all requests)">
        <Chart data={steps} x="name" y="cost" color="#8b5cf6" format={(v) => formatCost(v)} />
      </Card>
      <Card title="Average model call duration per step (s)">
        <Chart data={steps} x="name" y="seconds" color="#0ea5e9" format={(v) => `${v.toFixed(2)} s`} />
      </Card>
      <Card title="Model calls per step">
        <Chart data={steps} x="name" y="calls" color="#f59e0b" format={(v) => String(v)} />
      </Card>
      <Card title="Requests by state">
        <Chart data={states} x="state" y="count" color="#10b981" format={(v) => String(v)} />
      </Card>
    </div>
  );
}

type Row = Record<string, string | number>;

function Chart({
  data,
  x,
  y,
  color,
  format,
}: {
  data: Row[];
  x: string;
  y: string;
  color: string;
  format: (value: number) => string;
}) {
  if (data.length === 0) return <p className="text-sm text-zinc-500">No data yet.</p>;
  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ left: 8, right: 8 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey={x} tick={{ fontSize: 11 }} interval={0} />
          <YAxis tick={{ fontSize: 11 }} tickFormatter={(v: number) => format(v)} width={80} />
          <Tooltip formatter={(v) => format(Number(v))} />
          <Bar dataKey={y} fill={color} radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
