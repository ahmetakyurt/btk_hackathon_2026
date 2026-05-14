"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import { type PricingLog } from "@/lib/api";

const PLATFORM_COLORS: Record<string, string> = {
  trendyol: "#f97316",
  amazon: "#eab308",
  own_site: "#3b82f6",
};

const DECISION_DOT: Record<string, string> = {
  price_updated: "#16a34a",
  floor_hit: "#dc2626",
  no_action: "#a1a1aa",
};

const DECISION_LABEL: Record<string, string> = {
  price_updated: "Fiyat Guncellendi",
  floor_hit: "Taban Fiyat",
  no_action: "Islem Yok",
  buybox: "Buybox",
};

interface ChartPoint {
  time: string;
  price: number;
  decision: string;
  timestamp: number;
}

function buildPoints(logs: PricingLog[]): ChartPoint[] {
  return logs
    .filter((l) => l.new_price != null)
    .map((l) => ({
      time: new Date(l.created_at).toLocaleTimeString("tr-TR", {
        hour: "2-digit",
        minute: "2-digit",
      }),
      price: Number(l.new_price),
      decision: l.decision,
      timestamp: new Date(l.created_at).getTime(),
    }))
    .reverse();
}

interface Props {
  logs: PricingLog[];
  platformCode: string;
  floorPrice?: number | null;
}

export default function PriceHistoryChart({ logs, platformCode, floorPrice }: Props) {
  const points = buildPoints(logs);

  if (points.length === 0) {
    return (
      <div className="px-4 pb-3">
        <p className="text-xs text-zinc-400 mb-1">Fiyat Gecmisi</p>
        <p className="text-[11px] text-zinc-400">Henuz fiyat gecmisi yok.</p>
      </div>
    );
  }

  const color = PLATFORM_COLORS[platformCode] ?? "#a1a1aa";
  const minPrice = Math.min(...points.map((p) => p.price));
  const maxPrice = Math.max(...points.map((p) => p.price));
  const padding = Math.max((maxPrice - minPrice) * 0.2, 5);

  return (
    <div className="px-4 pb-3">
      <p className="text-xs text-zinc-400 mb-1">Fiyat Gecmisi</p>
      <ResponsiveContainer width="100%" height={180}>
        <LineChart data={points} margin={{ top: 4, right: 4, left: 4, bottom: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e4e4e7" />
          <XAxis dataKey="time" tick={{ fontSize: 10, fill: "#a1a1aa" }} />
          <YAxis
            domain={[minPrice - padding, maxPrice + padding]}
            tick={{ fontSize: 10, fill: "#a1a1aa" }}
            tickFormatter={(v: number) => `${v.toFixed(0)} ₺`}
            width={50}
          />
          <Tooltip
            formatter={(value: number) => [`${value.toFixed(2)} ₺`, "Fiyat"]}
            labelFormatter={(label: string) => `Saat: ${label}`}
            contentStyle={{ fontSize: 11, borderRadius: 6, border: "1px solid #e4e4e7" }}
          />
          <Line
            type="monotone"
            dataKey="price"
            stroke={color}
            strokeWidth={2}
            dot={(props: { cx?: number; cy?: number; payload?: { decision: string } }) => {
              if (props.cx == null || props.cy == null || !props.payload) return null;
              const dotColor = DECISION_DOT[props.payload.decision] ?? "#a1a1aa";
              return (
                <circle
                  cx={props.cx}
                  cy={props.cy}
                  r={4}
                  fill={dotColor}
                  stroke="#fff"
                  strokeWidth={1}
                />
              );
            }}
            activeDot={{ r: 5 }}
          />
          {floorPrice != null && (
            <ReferenceLine
              y={floorPrice}
              stroke="#f97316"
              strokeDasharray="4 4"
              strokeWidth={1}
              label={{
                value: `Taban: ${Number(floorPrice).toFixed(0)} ₺`,
                fontSize: 9,
                fill: "#f97316",
                position: "insideBottomRight",
              }}
            />
          )}
        </LineChart>
      </ResponsiveContainer>
      {/* Legend */}
      <div className="flex gap-3 mt-1 flex-wrap">
        {(["price_updated", "floor_hit", "no_action"] as const).map((d) => (
          <span key={d} className="inline-flex items-center gap-1 text-[10px] text-zinc-500">
            <span
              className="inline-block w-2 h-2 rounded-full"
              style={{ backgroundColor: DECISION_DOT[d] }}
            />
            {DECISION_LABEL[d]}
          </span>
        ))}
      </div>
    </div>
  );
}
