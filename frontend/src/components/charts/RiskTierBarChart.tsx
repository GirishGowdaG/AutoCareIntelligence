"use client";

import React from "react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Cell,
} from "recharts";

interface RiskTierBarChartProps {
  data: { tier: string; count: number }[];
}

const TIER_COLORS: Record<string, string> = {
  CRITICAL: "#f43f5e", // rose-500
  HIGH: "#f59e0b",     // amber-500
  MEDIUM: "#eab308",   // yellow-500
  LOW: "#10b981",      // emerald-500
};

export function RiskTierBarChart({ data }: RiskTierBarChartProps) {
  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
          <XAxis
            dataKey="tier"
            stroke="#64748b"
            fontSize={12}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            stroke="#64748b"
            fontSize={12}
            tickLine={false}
            axisLine={false}
            allowDecimals={false}
          />
          <Tooltip
            cursor={{ fill: "rgba(255, 255, 255, 0.05)" }}
            content={({ active, payload }) => {
              if (active && payload && payload.length) {
                const item = payload[0].payload;
                return (
                  <div className="rounded-lg border border-slate-800 bg-slate-900 p-2.5 shadow-xl text-xs">
                    <span className="font-semibold text-slate-200">{item.tier} Risk</span>
                    <div className="text-slate-400 mt-0.5">
                      Vehicles: <strong className="text-white">{item.count}</strong>
                    </div>
                  </div>
                );
              }
              return null;
            }}
          />
          <Bar dataKey="count" radius={[6, 6, 0, 0]}>
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={TIER_COLORS[entry.tier] || "#3b82f6"} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
