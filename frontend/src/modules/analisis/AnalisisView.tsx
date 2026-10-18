import { useEffect, useMemo, useState } from "react";
import { Activity, BarChart3, RefreshCw } from "lucide-react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis } from "recharts";

import { getEventGeoJson, getTimeSeries } from "../../services/analytics.service";
import type { EventFeature, TimeSeriesPoint } from "../../types/analytics.types";

function dateValue(daysAgo: number): string {
	return new Date(Date.now() - daysAgo * 86400000).toISOString().slice(0, 10);
}

function utcBoundary(value: string, endOfDay = false): string {
	return `${value}T${endOfDay ? "23:59:59" : "00:00:00"}Z`;
}

export default function AnalisisView() {
	const [startDate, setStartDate] = useState(dateValue(365));
	const [endDate, setEndDate] = useState(dateValue(0));
	const [series, setSeries] = useState<TimeSeriesPoint[]>([]);
	const [events, setEvents] = useState<EventFeature[]>([]);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState("");
	const [refresh, setRefresh] = useState(0);

	useEffect(() => {
		let active = true;
		setLoading(true);
		Promise.all([
			getTimeSeries(utcBoundary(startDate), utcBoundary(endDate, true), "week"),
			getEventGeoJson({ startDate: utcBoundary(startDate), endDate: utcBoundary(endDate, true) }),
		])
			.then(([timeSeries, geoJson]) => {
				if (!active) return;
				setSeries(timeSeries.items);
				setEvents(geoJson.features);
				setError("");
			})
			.catch(() => { if (active) setError("No se pudo cargar el análisis del periodo seleccionado."); })
			.finally(() => { if (active) setLoading(false); });
		return () => { active = false; };
	}, [startDate, endDate, refresh]);

	const magnitudeDistribution = useMemo(() => {
		const bins = new Map<number, number>();
		for (const event of events) {
			const bin = Math.floor(event.properties.magnitude);
			bins.set(bin, (bins.get(bin) ?? 0) + 1);
		}
		return [...bins.entries()].sort(([left], [right]) => left - right).map(([magnitude, count]) => ({
			interval: `${magnitude}.0–${magnitude + 0.9}`,
			count,
		}));
	}, [events]);
	const depthMagnitude = events.map(({ properties }) => ({ depth: properties.depth_km, magnitude: properties.magnitude }));

	return (
		<div className="analysis-page">
			<section className="admin-heading">
				<div><div className="page-eyebrow">ANÁLISIS <span>·</span> DATOS OBSERVADOS</div><h1>Análisis estadístico</h1><p className="page-lede">Distribuciones y series descriptivas de los eventos reportados.</p></div>
				<button aria-label="Actualizar análisis" className="icon-button refresh-icon-button" onClick={() => setRefresh((value) => value + 1)} title="Actualizar" type="button"><RefreshCw size={16} /></button>
			</section>
			<form className="event-filters analysis-filters" onSubmit={(event) => { event.preventDefault(); setRefresh((value) => value + 1); }}>
				<div className="filter-heading"><Activity size={15} /><span>Periodo UTC</span></div>
				<label>Desde<input max={endDate} onChange={(event) => setStartDate(event.target.value)} type="date" value={startDate} /></label>
				<label>Hasta<input min={startDate} onChange={(event) => setEndDate(event.target.value)} type="date" value={endDate} /></label>
				<span className="sample-size">{loading ? "Consultando…" : `${events.length.toLocaleString("es-PE")} eventos en gráficas`}</span>
			</form>
			{error && <p className="admin-error" role="alert">{error}</p>}
			<div className="analysis-grid">
				<section className="content-panel analysis-panel analysis-panel-wide">
					<div className="panel-heading"><div><div className="panel-kicker">CONTEO SEMANAL</div><h2>Eventos a lo largo del tiempo</h2></div><span className="table-count">UTC · {series.length} periodos</span></div>
					<div className="analysis-chart">{series.length ? <ResponsiveContainer width="100%" height="100%"><BarChart data={series} margin={{ top: 15, right: 15, left: -18, bottom: 4 }}><CartesianGrid stroke="#e8efec" strokeDasharray="3 5" vertical={false} /><XAxis dataKey="period_start" tickFormatter={(value: string) => new Date(value).toLocaleDateString("es-PE", { month: "short", day: "numeric", timeZone: "UTC" })} tick={{ fill: "#829291", fontSize: 9 }} axisLine={false} tickLine={false} minTickGap={28} /><YAxis allowDecimals={false} tick={{ fill: "#829291", fontSize: 9 }} axisLine={false} tickLine={false} /><Tooltip labelFormatter={(value) => new Date(String(value)).toLocaleDateString("es-PE", { dateStyle: "medium", timeZone: "UTC" })} formatter={(value) => [value, "Eventos"]} /><Bar dataKey="event_count" fill="#148679" radius={[3, 3, 0, 0]} maxBarSize={24} /></BarChart></ResponsiveContainer> : <div className="chart-empty-state"><BarChart3 size={23} /><strong>{loading ? "Cargando datos" : "Sin eventos en este periodo"}</strong><span>El tamaño de muestra se limita a eventos recibidos.</span></div>}</div>
				</section>
				<section className="content-panel analysis-panel">
					<div className="panel-heading"><div><div className="panel-kicker">MUESTRA GEOJSON</div><h2>Distribución por magnitud</h2></div><span className="table-count">{events.length} registros</span></div>
					<div className="analysis-chart">{magnitudeDistribution.length ? <ResponsiveContainer width="100%" height="100%"><BarChart data={magnitudeDistribution} margin={{ top: 15, right: 13, left: -21, bottom: 5 }}><CartesianGrid stroke="#e8efec" strokeDasharray="3 5" vertical={false} /><XAxis dataKey="interval" tick={{ fill: "#829291", fontSize: 9 }} axisLine={false} tickLine={false} /><YAxis allowDecimals={false} tick={{ fill: "#829291", fontSize: 9 }} axisLine={false} tickLine={false} /><Tooltip formatter={(value) => [value, "Eventos"]} /><Bar dataKey="count" fill="#c58a35" radius={[3, 3, 0, 0]} maxBarSize={38} /></BarChart></ResponsiveContainer> : <div className="chart-empty-state"><BarChart3 size={23} /><strong>Sin muestra disponible</strong><span>Cuando existan eventos, se agruparán por magnitud.</span></div>}</div>
				</section>
				<section className="content-panel analysis-panel">
					<div className="panel-heading"><div><div className="panel-kicker">SIN INFERENCIA CAUSAL</div><h2>Magnitud y profundidad</h2></div><span className="table-count">km · magnitud</span></div>
					<div className="analysis-chart">{depthMagnitude.length ? <ResponsiveContainer width="100%" height="100%"><ScatterChart margin={{ top: 15, right: 15, left: -12, bottom: 5 }}><CartesianGrid stroke="#e8efec" strokeDasharray="3 5" /><XAxis type="number" dataKey="depth" name="Profundidad" unit=" km" tick={{ fill: "#829291", fontSize: 9 }} axisLine={false} tickLine={false} /><YAxis type="number" dataKey="magnitude" name="Magnitud" tick={{ fill: "#829291", fontSize: 9 }} axisLine={false} tickLine={false} /><Tooltip cursor={{ strokeDasharray: "3 3" }} /><Scatter data={depthMagnitude} fill="#168276" /></ScatterChart></ResponsiveContainer> : <div className="chart-empty-state"><BarChart3 size={23} /><strong>Sin muestra disponible</strong><span>Se representará cada evento recibido como un punto.</span></div>}</div>
				</section>
			</div>
			<p className="source-disclaimer">Las gráficas usan hasta 2.000 eventos para distribuciones y muestran el periodo, unidad y tamaño de muestra. No representan causalidad ni peligro oficial.</p>
		</div>
	);
}