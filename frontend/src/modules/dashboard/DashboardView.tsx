import { lazy, Suspense, useEffect, useState } from "react";
import { Activity, ArrowRight, Check, Database, GitBranch, MapPinned, Radio } from "lucide-react";
import { Link } from "react-router-dom";

import { getDashboardSummary, getTimeSeries } from "../../services/analytics.service";
import type { DashboardSummary, TimeSeriesPoint } from "../../types/analytics.types";

const DashboardTrend = lazy(() => import("./DashboardTrend"));

const foundation = [
	{ title: "Eventos y procedencia", detail: "Ingesta verificada · catálogo", icon: Radio },
	{ title: "Analítica descriptiva", detail: "Resumen · series · mapa", icon: Activity },
	{ title: "Calidad y datasets", detail: "Snapshots · versionado", icon: Database },
	{ title: "ML experimental", detail: "Regresión · evaluación temporal", icon: GitBranch },
];

function dateDaysAgo(days: number): string {
	return new Date(Date.now() - days * 24 * 60 * 60 * 1000).toISOString();
}

function formatDate(value: string | null): string {
	if (!value) return "Sin sincronización";
	return new Intl.DateTimeFormat("es-PE", { dateStyle: "medium", timeStyle: "short", timeZone: "UTC" }).format(new Date(value));
}

export default function DashboardView() {
	const [summary, setSummary] = useState<DashboardSummary | null>(null);
	const [series, setSeries] = useState<TimeSeriesPoint[]>([]);
	const [error, setError] = useState("");

	useEffect(() => {
		let active = true;
		Promise.all([getDashboardSummary(), getTimeSeries(dateDaysAgo(365), new Date().toISOString(), "week")])
			.then(([summaryResult, seriesResult]) => {
				if (!active) return;
				setSummary(summaryResult);
				setSeries(seriesResult.items);
				setError("");
			})
			.catch(() => { if (active) setError("No fue posible consultar los indicadores. Revisa la conexión con la API."); });
		return () => { active = false; };
	}, []);

	return (
		<div className="dashboard-page">
			<section className="dashboard-heading">
				<div>
					<div className="page-eyebrow"><span className="live-mark" /> VISTA GENERAL <span>·</span> EVENTOS OBSERVADOS</div>
					<h1>Monitoreo sísmico</h1>
					<p className="page-lede">Indicadores operativos, actividad reportada y estado de las fuentes.</p>
				</div>
				<Link to="/eventos" className="primary-action"><Activity size={16} /><span>Consultar eventos</span><ArrowRight size={16} /></Link>
			</section>

			<section className="notice-strip" aria-label="Estado de los datos">
				<span className="notice-icon"><Activity size={17} /></span>
				<div><strong>{summary?.total_events ? `${summary.total_events.toLocaleString("es-PE")} eventos observados` : "Aún no hay eventos registrados"}</strong><span>Los resultados describen reportes recibidos; no son predicciones ni niveles oficiales de peligro.</span></div>
				<span className="notice-state">{summary?.active_sources ? `${summary.active_sources} FUENTE ACTIVA` : "SIN FUENTES ACTIVAS"}</span>
			</section>
			{error && <p className="admin-error" role="alert">{error}</p>}

			<section className="metric-grid" aria-label="Indicadores del sistema">
				<article className="metric-panel">
					<div className="metric-top"><span>Eventos registrados</span><Activity size={17} /></div>
					<strong className="metric-value">{summary?.total_events.toLocaleString("es-PE") ?? "—"}</strong>
					<span className="metric-foot">{summary?.events_last_24h ?? "—"} en las últimas 24 horas</span>
				</article>
				<article className="metric-panel">
					<div className="metric-top"><span>Fuentes activas</span><Database size={17} /></div>
					<strong className="metric-value">{summary ? `${summary.active_sources}/${summary.total_sources}` : "—"}</strong>
					<span className="metric-foot">Proveedores registrados</span>
				</article>
				<article className="metric-panel">
					<div className="metric-top"><span>Última sincronización</span><Radio size={17} /></div>
					<strong className="metric-value metric-value-text">{summary ? formatDate(summary.last_sync_at) : "—"}</strong>
					<span className="metric-foot">Consulta registrada del proveedor</span>
				</article>
				<article className="metric-panel metric-panel-accent">
					<div className="metric-top"><span>Alcance implementado</span><MapPinned size={17} /></div>
					<strong className="metric-value metric-value-text">Fases 1–6</strong>
					<span className="metric-foot">ML experimental, no predictivo</span>
				</article>
			</section>

			<div className="dashboard-columns">
				<section className="content-panel data-panel">
					<div className="panel-heading">
						<div><div className="panel-kicker">ÚLTIMOS 12 MESES</div><h2>Eventos reportados por semana</h2></div>
						<Link to="/eventos" className="quiet-link">Ver eventos <ArrowRight size={15} /></Link>
					</div>
					<Suspense fallback={<div className="dashboard-chart chart-loading" role="status">Cargando gráfica…</div>}><DashboardTrend series={series} loading={!summary} /></Suspense>
				</section>

				<section className="content-panel foundation-panel">
					<div className="panel-heading">
						<div><div className="panel-kicker">CAPACIDADES</div><h2>Flujo analítico</h2></div>
							<span className="completion-count">4 <span>/ 4</span></span>
					</div>
					<div className="foundation-list">
						{foundation.map(({ title, detail, icon: Icon }) => (
							<div className="foundation-row" key={title}>
								<span className="foundation-icon foundation-listo"><Icon size={16} /></span>
								<div className="foundation-copy"><strong>{title}</strong><span>{detail}</span></div>
								<span className="foundation-status foundation-status-listo"><Check size={13} /> API</span>
							</div>
						))}
					</div>
					<div className="foundation-foot"><span>Eventos y experimentos permanecen separados</span><Link to="/modelos">Ver laboratorio <ArrowRight size={14} /></Link></div>
				</section>
			</div>

			<section className="bottom-note">
				<span className="note-mark">i</span>
				<p>El sistema diferencia los eventos reportados, las estimaciones experimentales y las alertas oficiales. Esta interfaz no predice terremotos.</p>
				<Link to="/analisis">Principios de análisis <ArrowRight size={14} /></Link>
			</section>
		</div>
	);
}