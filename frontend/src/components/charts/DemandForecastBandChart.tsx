"use client";

import React from "react";
import {
  ResponsiveContainer,
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  Tooltip,
} from "recharts";
import { ServiceDemandForecast } from "@/types/ml";

interface DemandForecastBandChartProps {
  data: ServiceDemandForecast[];
}

export function DemandForecastBandChart({ data }: DemandForecastBandChartProps) {
  // Sort by date ascending
  const chartData = [...data]
    .sort((a, b) => new Date(a.forecast_date).getTime() - new Date(b.forecast_date).getTime())
    .map((item) => {
      const pred = item.predicted_volume ?? 0;
      const lower = item.lower_bound_80 ?? 0;
      const upper = item.upper_bound_80 ?? 0;
      return {
        date: String(item.forecast_date).split("T")[0],
        predicted: pred,
        lower: lower,
        upper: upper,
        band: [lower, upper],
        is_surge: Boolean(item.is_surge),
        dealer_id: item.dealer_id,
      };
    });

  return (
    <div className="h-72 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={chartData} margin={{ top: 10, right: 20, left: -20, bottom: 0 }}>
          <XAxis
            dataKey="date"
            stroke="#64748b"
            fontSize={11}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            stroke="#64748b"
            fontSize={11}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip
            content={({ active, payload }) => {
              if (active && payload && payload.length) {
                const item = payload[0].payload;
                return (
                  <div className="rounded-xl border border-slate-800 bg-slate-900 p-3 shadow-xl text-xs space-y-1">
                    <div className="font-semibold text-slate-200">
                      Date: {item.date} ({item.dealer_id})
                    </div>
                    <div className="text-blue-400 font-medium">
                      Forecast Demand: <strong>{item.predicted.toFixed(1)}</strong> units
                    </div>
                    <div className="text-slate-400 text-[11px]">
                      80% Confidence Interval: [{item.lower.toFixed(1)} — {item.upper.toFixed(1)}]
                    </div>
                    {item.is_surge && (
                      <div className="mt-1 rounded bg-rose-950/80 px-2 py-0.5 text-[10px] font-bold text-rose-300 border border-rose-800">
                        SURGE ALERT: Exceeds proposed capacity threshold
                      </div>
                    )}
                  </div>
                );
              }
              return null;
            }}
          />
          {/* 80% confidence interval band */}
          <Area
            type="monotone"
            dataKey="band"
            fill="#3b82f6"
            fillOpacity={0.15}
            stroke="#60a5fa"
            strokeDasharray="3 3"
          />
          {/* Main forecast prediction line */}
          <Line
            type="monotone"
            dataKey="predicted"
            stroke="#3b82f6"
            strokeWidth={2.5}
            dot={{ r: 3, fill: "#3b82f6" }}
            activeDot={{ r: 5, fill: "#60a5fa" }}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
