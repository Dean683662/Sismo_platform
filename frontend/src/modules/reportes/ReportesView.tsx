import { useEffect, useState, type FormEvent } from "react";
import { Download, FileBarChart, Plus, RefreshCw } from "lucide-react";

import Button from "../../components/Button";
import SkeletonLoader from "../../components/SkeletonLoader";
import { createReport, downloadReport, listReports, type ReportRun, type ReportType } from "../../services/reports.service";

const reportLabels: Record<ReportType, string> = {
	events: "Eventos",
	models: "Modelos ML",
	sources: "Fuentes de datos",
	alerts: "Alertas y entregas",
	quality: "Calidad de datasets",
};

function dateLabel(value: string): string {
	return `${new Date(value).toLocaleString("es-PE", { timeZone: "UTC", dateStyle: "medium", timeStyle: "short" })} UTC`;
}

export default function ReportesView() {
	const [reports, setReports] = useState<ReportRun[]>([]);
	const [loading, setLoading] = useState(true);
	const [creating, setCreating] = useState(false);
	const [downloadingId, setDownloadingId] = useState("");
	const [error, setError] = useState("");
	const [notice, setNotice] = useState("");
	const [refreshKey, setRefreshKey] = useState(0);

	useEffect(() => {
		let active = true;
		listReports()
			.then((result) => { if (active) setReports(result); })
			.catch((requestError: unknown) => {
				if (active) setError(requestError instanceof Error ? requestError.message : "No se pudo cargar el historial de reportes.");
			})
			.finally(() => { if (active) setLoading(false); });
		return () => { active = false; };
	}, [refreshKey]);

	async function handleCreate(event: FormEvent<HTMLFormElement>) {
		event.preventDefault();
		const form = new FormData(event.currentTarget);
		const reportType = String(form.get("report_type")) as ReportType;
		const startDate = String(form.get("start_date") ?? "");
		const endDate = String(form.get("end_date") ?? "");
		setCreating(true);
		setError("");
		setNotice("");
		try {
			await createReport({
				report_type: reportType,
				start_date: startDate ? `${startDate}T00:00:00Z` : undefined,
				end_date: endDate ? `${endDate}T23:59:59.999Z` : undefined,
				min_magnitude: form.get("min_magnitude") ? Number(form.get("min_magnitude")) : undefined,
				max_magnitude: form.get("max_magnitude") ? Number(form.get("max_magnitude")) : undefined,
				source_key: String(form.get("source_key") ?? "") || undefined,
				limit: 5000,
			});
			setNotice("Reporte guardado como una instantánea inmutable y reproducible.");
			setLoading(true);
			setRefreshKey((value) => value + 1);
		} catch (requestError) {
			setError(requestError instanceof Error ? requestError.message : "No se pudo generar el reporte.");
		} finally {
			setCreating(false);
		}
	}

	async function handleDownload(report: ReportRun, format: "csv" | "json" | "xlsx" | "pdf") {
		setDownloadingId(`${report.id}:${format}`);
		setError("");
		try {
			await downloadReport(report, format);
		} catch (requestError) {
			setError(requestError instanceof Error ? requestError.message : "No se pudo exportar el reporte.");
		} finally {
			setDownloadingId("");
		}
	}

	return (
		<div className="admin-page report-page">
			<section className="admin-heading"><div><div className="page-eyebrow">ANÁLISIS <span>·</span> CONSULTAS REPRODUCIBLES</div><h1>Reportes</h1><p className="page-lede">Cada ejecución conserva filtros, fecha de corte y una instantánea de los registros exportables.</p></div><Button icon={<RefreshCw size={15} />} onClick={() => setRefreshKey((value) => value + 1)} variant="secondary">Actualizar historial</Button></section>
			{error && <p className="admin-error" role="alert">{error}</p>}
			{notice && <p className="sync-notice" role="status">{notice}</p>}
			<section className="content-panel report-builder">
				<div className="panel-heading"><div><div className="panel-kicker">GENERADOR</div><h2>Crear una instantánea</h2></div><FileBarChart size={18} aria-hidden="true" /></div>
				<form className="report-form" onSubmit={(event) => void handleCreate(event)}>
					<label>Tipo de reporte<select name="report_type"><option value="events">Eventos sísmicos</option><option value="models">Experimentos ML</option><option value="sources">Fuentes de datos</option><option value="alerts">Alertas y entregas</option><option value="quality">Calidad de datasets</option></select></label>
					<label>Desde (UTC)<input name="start_date" type="date" /></label>
					<label>Hasta (UTC)<input name="end_date" type="date" /></label>
					<label>Magnitud mínima<input max={10} min={0} name="min_magnitude" step="0.1" type="number" /></label>
					<label>Magnitud máxima<input max={10} min={0} name="max_magnitude" step="0.1" type="number" /></label>
					<label>Clave de fuente<input maxLength={40} name="source_key" placeholder="p. ej., igp" /></label>
					<div className="report-form-footer"><span>Máximo 5.000 filas por instantánea.</span><Button disabled={creating} icon={<Plus size={15} />} type="submit">{creating ? "Generando…" : "Generar reporte"}</Button></div>
				</form>
			</section>
			<section className="content-panel admin-table-panel report-history">
				<div className="panel-heading"><div><div className="panel-kicker">ARCHIVO DE EJECUCIONES</div><h2>Historial reproducible</h2></div><span className="table-count">{reports.length} reportes</span></div>
				{loading ? <div className="admin-loading"><SkeletonLoader lines={5} /></div> : reports.length === 0 ? <p className="admin-empty">Todavía no se han generado reportes.</p> : (
					<div className="table-scroll"><table className="admin-table"><thead><tr><th>Tipo</th><th>Fecha de corte UTC</th><th>Filas</th><th>Filtros</th><th>Exportar</th></tr></thead><tbody>
						{reports.map((report) => <tr key={report.id}>
							<td><strong>{reportLabels[report.report_type]}</strong><span>{report.id.slice(0, 8)}</span></td>
							<td>{dateLabel(String(report.filters.cutoff_at ?? report.created_at))}<span>Solicitante: {report.requested_by ?? "Usuario eliminado"}</span></td>
							<td>{report.row_count.toLocaleString("es-PE")}</td>
							<td>{Object.entries(report.filters).filter(([key, value]) => key !== "cutoff_at" && value !== null && value !== "").map(([key, value]) => `${key}: ${String(value)}`).join(" · ") || "Sin filtros adicionales"}</td>
							<td className="report-download-actions">
								<Button disabled={Boolean(downloadingId)} icon={<Download size={14} />} onClick={() => void handleDownload(report, "csv")} variant="secondary">{downloadingId === `${report.id}:csv` ? "Descargando…" : "CSV"}</Button>
								<Button disabled={Boolean(downloadingId)} onClick={() => void handleDownload(report, "json")} variant="quiet">{downloadingId === `${report.id}:json` ? "Descargando…" : "JSON"}</Button>
								<Button disabled={Boolean(downloadingId)} onClick={() => void handleDownload(report, "xlsx")} variant="quiet">{downloadingId === `${report.id}:xlsx` ? "Descargando…" : "XLSX"}</Button>
								<Button disabled={Boolean(downloadingId)} onClick={() => void handleDownload(report, "pdf")} variant="quiet">{downloadingId === `${report.id}:pdf` ? "Descargando…" : "PDF"}</Button>
							</td>
						</tr>)}
					</tbody></table></div>
				)}
			</section>
		</div>
	);
}