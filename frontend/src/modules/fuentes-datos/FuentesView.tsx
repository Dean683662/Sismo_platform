import { useEffect, useState } from "react";
import { ArrowUpRight, Check, Clock3, Database, RotateCw, TriangleAlert } from "lucide-react";

import Button from "../../components/Button";
import SkeletonLoader from "../../components/SkeletonLoader";
import { useAuth } from "../../hooks/useAuth";
import { listDataSources, syncDataSource } from "../../services/sources.service";
import type { DataSource, IngestionRun } from "../../types/event.types";

function formatDate(value: string | null): string {
	return value ? new Date(value).toLocaleString("es-PE", { timeZone: "UTC", dateStyle: "medium", timeStyle: "short" }) + " UTC" : "Sin sincronización";
}

export default function FuentesView() {
	const { hasPermission } = useAuth();
	const [sources, setSources] = useState<DataSource[]>([]);
	const [loading, setLoading] = useState(true);
	const [syncing, setSyncing] = useState("");
	const [error, setError] = useState("");
	const [notice, setNotice] = useState("");
	const [refreshKey, setRefreshKey] = useState(0);

	useEffect(() => {
		let active = true;
		listDataSources()
			.then((result) => { if (active) setSources(result); })
			.catch(() => { if (active) setError("No se pudo consultar el estado de las fuentes."); })
			.finally(() => { if (active) setLoading(false); });
		return () => { active = false; };
	}, [refreshKey]);

	async function runSync(source: DataSource) {
		setSyncing(source.id);
		setError("");
		setNotice("");
		try {
			const run: IngestionRun = await syncDataSource(source.id);
			setNotice(run.status === "succeeded"
				? `Sincronización finalizada: ${run.records_inserted} nuevos, ${run.records_updated} actualizados, ${run.records_duplicated} duplicados.`
				: run.error_summary ?? "La fuente no pudo completar la sincronización.");
			setRefreshKey((value) => value + 1);
		} catch (requestError) {
			setError(requestError instanceof Error ? requestError.message : "No se pudo iniciar la sincronización.");
		} finally {
			setSyncing("");
		}
	}

	return (
		<div className="admin-page">
			<section className="admin-heading"><div><div className="page-eyebrow">PLATAFORMA <span>·</span> PROCEDENCIA DE DATOS</div><h1>Fuentes de datos</h1><p className="page-lede">Proveedores configurados, última consulta y resultado de ingesta.</p></div><Button icon={<RotateCw size={15} />} onClick={() => setRefreshKey((value) => value + 1)} variant="secondary">Actualizar estado</Button></section>
			{error && <p className="admin-error" role="alert">{error}</p>}{notice && <p className="sync-notice" role="status">{notice}</p>}
			{loading ? <div className="source-loading"><SkeletonLoader lines={5} /></div> : sources.map((source) => <section className="content-panel source-panel" key={source.id}>
				<div className="source-panel-heading"><span className="source-icon"><Database size={19} /></span><div className="source-title"><div className="source-title-row"><h2>{source.name}</h2><span className={`source-status source-status-${source.status}`}>{source.status === "active" ? <><Check size={12} /> Operativa</> : <><TriangleAlert size={12} /> Degradada</>}</span></div><p>{source.organization} · {source.source_type.replaceAll("_", " ")}</p></div>
					{hasPermission("sources:manage") && <Button disabled={Boolean(syncing)} icon={syncing === source.id ? <Clock3 size={15} /> : <RotateCw size={15} />} onClick={() => void runSync(source)}>{syncing === source.id ? "Sincronizando…" : "Sincronizar ahora"}</Button>}
				</div>
				<div className="source-metrics"><div><span>Última consulta</span><strong>{formatDate(source.last_sync_at)}</strong></div><div><span>Último éxito</span><strong>{formatDate(source.last_success_at)}</strong></div><div><span>Última ejecución</span><strong>{source.last_run?.status ?? "Sin ejecuciones"}</strong></div><div><span>Registros nuevos</span><strong>{source.last_run?.records_inserted ?? "—"}</strong></div></div>
				{source.last_run?.error_summary && <p className="source-error"><TriangleAlert size={14} />{source.last_run.error_summary}</p>}
				<div className="source-panel-footer"><span>Esta integración consulta el evento más reciente publicado por el IGP.</span><a href={source.base_url} rel="noreferrer" target="_blank">Endpoint del proveedor <ArrowUpRight size={14} /></a></div>
			</section>)}
			<p className="source-disclaimer">La sincronización inicial no recupera un histórico: el endpoint verificado del IGP entrega el último evento reportado. Debe confirmarse con el proveedor si existe un feed histórico autorizado.</p>
		</div>
	);
}