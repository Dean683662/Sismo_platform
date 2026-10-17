import { Activity } from "lucide-react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import type { TimeSeriesPoint } from "../../types/analytics.types";

function formatDate(value: string): string {
	return new Intl.DateTimeFormat("es-PE", { dateStyle: "medium", timeStyle: "short", timeZone: "UTC" }).format(new Date(value));
}

export default function DashboardTrend({ series, loading }: { series: TimeSeriesPoint[]; loading: boolean }) {
	return (
		<div className="dashboard-chart">
			{series.length ? <ResponsiveContainer width="100%" height="100%"><AreaChart data={series} margin={{ top: 16, right: 17, left: -18, bottom: 3 }}><defs><linearGradient id="event-fill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#148679" stopOpacity={0.24} /><stop offset="95%" stopColor="#148679" stopOpacity={0.02} /></linearGradient></defs><CartesianGrid stroke="#e8efec" strokeDasharray="3 5" vertical={false} /><XAxis dataKey="period_start" tickFormatter={(value: string) => new Date(value).toLocaleDateString("es-PE", { month: "short", day: "numeric", timeZone: "UTC" })} tick={{ fill: "#829291", fontSize: 9 }} axisLine={false} tickLine={false} minTickGap={28} /><YAxis allowDecimals={false} tick={{ fill: "#829291", fontSize: 9 }} axisLine={false} tickLine={false} /><Tooltip labelFormatter={(value) => formatDate(String(value))} formatter={(value) => [value, "Eventos"]} /><Area type="monotone" dataKey="event_count" stroke="#087f78" strokeWidth={2} fill="url(#event-fill)" /></AreaChart></ResponsiveContainer> : <div className="chart-empty-state"><Activity size={24} /><strong>{loading ? "Cargando actividad" : "Sin actividad en el periodo"}</strong><span>La serie se basa únicamente en eventos recibidos.</span></div>}
		</div>
	);
}