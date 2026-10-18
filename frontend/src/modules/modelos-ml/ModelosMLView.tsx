import { useEffect, useState, type FormEvent } from "react";
import { Database, FlaskConical, Play, Plus, RefreshCw } from "lucide-react";

import { useAuth } from "../../hooks/useAuth";
import { createDataset, createExperiment, listDatasets, listExperiments } from "../../services/ml.service";
import type { DatasetVersion, Experiment } from "../../types/ml.types";

function formatPeriod(period: [string, string]): string {
	const format = (date: string) => new Date(date).toLocaleDateString("es-PE", { dateStyle: "medium", timeZone: "UTC" });
	return `${format(period[0])} – ${format(period[1])}`;
}

export default function ModelosMLView() {
	const { hasPermission } = useAuth();
	const canManage = hasPermission("models:manage");
	const [datasets, setDatasets] = useState<DatasetVersion[]>([]);
	const [experiments, setExperiments] = useState<Experiment[]>([]);
	const [datasetName, setDatasetName] = useState("Eventos observados");
	const [experimentName, setExperimentName] = useState("Baseline magnitud");
	const [taskType, setTaskType] = useState<"regression" | "classification">("regression");
	const [selectedDataset, setSelectedDataset] = useState("");
	const [loading, setLoading] = useState(true);
	const [busy, setBusy] = useState(false);
	const [error, setError] = useState("");
	const [notice, setNotice] = useState("");

	async function refresh() {
		const [datasetResult, experimentResult] = await Promise.all([listDatasets(), listExperiments()]);
		setDatasets(datasetResult);
		setExperiments(experimentResult);
		setSelectedDataset((current) => current || datasetResult[0]?.id || "");
	}

	useEffect(() => {
		let active = true;
		Promise.all([listDatasets(), listExperiments()])
			.then(([datasetResult, experimentResult]) => {
				if (!active) return;
				setDatasets(datasetResult);
				setExperiments(experimentResult);
				setSelectedDataset(datasetResult[0]?.id ?? "");
			})
			.catch(() => { if (active) setError("No se pudo cargar el registro de datasets y experimentos."); })
			.finally(() => { if (active) setLoading(false); });
		return () => { active = false; };
	}, []);

	async function handleCreateDataset(event: FormEvent<HTMLFormElement>) {
		event.preventDefault();
		setBusy(true);
		setError("");
		setNotice("");
		try {
			const dataset = await createDataset(datasetName.trim());
			await refresh();
			setSelectedDataset(dataset.id);
			setNotice(`Dataset ${dataset.name} v${dataset.version} guardado con ${dataset.row_count} eventos válidos.`);
		} catch (requestError) {
			setError(requestError instanceof Error ? requestError.message : "No se pudo crear el dataset.");
		} finally {
			setBusy(false);
		}
	}

	async function handleCreateExperiment(event: FormEvent<HTMLFormElement>) {
		event.preventDefault();
		if (!selectedDataset) return;
		setBusy(true);
		setError("");
		setNotice("");
		try {
			const experiment = await createExperiment(experimentName.trim(), selectedDataset, taskType);
			await refresh();
			const metric = taskType === "regression" ? experiment.metrics.rmse : experiment.metrics.f1_macro;
			const metricName = taskType === "regression" ? "RMSE" : "F1 macro";
			setNotice(`Experimento terminado. ${metricName} ${metric.toFixed(3)} · ${experiment.validation_spec.row_count} eventos.`);
		} catch (requestError) {
			setError(requestError instanceof Error ? requestError.message : "No se pudo ejecutar el experimento.");
		} finally {
			setBusy(false);
		}
	}

	return (
		<div className="ml-page">
			<section className="admin-heading"><div><div className="page-eyebrow">ANÁLISIS <span>·</span> LABORATORIO EXPERIMENTAL</div><h1>Modelos ML</h1><p className="page-lede">Datasets versionados y experimentos reproducibles sobre eventos ya reportados.</p></div><button aria-label="Actualizar registro" className="icon-button refresh-icon-button" onClick={() => { setLoading(true); void refresh().catch(() => setError("No se pudo actualizar el registro.")).finally(() => setLoading(false)); }} title="Actualizar" type="button"><RefreshCw size={16} /></button></section>
			<div className="ml-disclaimer"><FlaskConical size={17} /><p><strong>Alcance científico.</strong> La regresión estima magnitudes ya reportadas y la clasificación agrupa esos registros en bandas descriptivas. Ninguno predice terremotos futuros ni constituye una alerta oficial.</p></div>
			{error && <p className="admin-error" role="alert">{error}</p>}
			{notice && <p className="sync-notice" role="status">{notice}</p>}
			{canManage && <div className="ml-workbench">
				<form className="content-panel ml-form-panel" onSubmit={(event) => void handleCreateDataset(event)}>
					<div className="panel-heading"><div><div className="panel-kicker">FASE 5 · CALIDAD DE DATOS</div><h2>Crear snapshot</h2></div><Database size={16} /></div>
					<div className="ml-form-body"><label>Nombre del dataset<input maxLength={160} minLength={2} onChange={(event) => setDatasetName(event.target.value)} required value={datasetName} /></label><p>Captura eventos reportados en este momento; cada versión conserva los datos usados por el experimento.</p><button className="button button-secondary" disabled={busy} type="submit"><Plus size={15} /> Crear dataset</button></div>
				</form>
				<form className="content-panel ml-form-panel" onSubmit={(event) => void handleCreateExperiment(event)}>
					<div className="panel-heading"><div><div className="panel-kicker">FASE 6 · EVALUACIÓN TEMPORAL</div><h2>Entrenar baseline</h2></div><Play size={16} /></div>
					<div className="ml-form-body"><label>Nombre del experimento<input maxLength={160} minLength={2} onChange={(event) => setExperimentName(event.target.value)} required value={experimentName} /></label><label>Tipo de tarea<select onChange={(event) => setTaskType(event.target.value as "regression" | "classification")} value={taskType}><option value="regression">Regresión de magnitud</option><option value="classification">Clasificación de bandas de magnitud</option></select></label><label>Dataset<select onChange={(event) => setSelectedDataset(event.target.value)} required value={selectedDataset}><option value="">Seleccionar versión</option>{datasets.map((dataset) => <option key={dataset.id} value={dataset.id}>{dataset.name} · v{dataset.version} · {dataset.row_count} filas</option>)}</select></label><button className="button button-primary" disabled={busy || !selectedDataset} type="submit"><Play size={15} /> Ejecutar evaluación temporal</button></div>
				</form>
			</div>}
			<section className="content-panel ml-table-panel">
				<div className="panel-heading"><div><div className="panel-kicker">FASE 5 · SNAPSHOTS</div><h2>Datasets</h2></div><span className="table-count">{datasets.length} versiones</span></div>
				{loading ? <p className="admin-empty">Cargando datasets…</p> : datasets.length === 0 ? <p className="admin-empty">Todavía no hay snapshots. Crea uno para revisar el tamaño y la calidad de la muestra.</p> : <div className="table-scroll"><table className="admin-table ml-table"><thead><tr><th>Dataset</th><th>Periodo observado</th><th>Filas</th><th>Duplicados</th><th>Inválidas</th><th>Creado UTC</th></tr></thead><tbody>{datasets.map((dataset) => <tr key={dataset.id}><td><strong>{dataset.name} · v{dataset.version}</strong><span>Snapshot inmutable</span></td><td>{dataset.period_start && dataset.period_end ? formatPeriod([dataset.period_start, dataset.period_end]) : "Sin periodo"}</td><td>{dataset.row_count}</td><td>{dataset.quality_report.duplicates}</td><td>{dataset.quality_report.invalid_rows}</td><td>{new Date(dataset.created_at).toLocaleString("es-PE", { timeZone: "UTC" })}</td></tr>)}</tbody></table></div>}
			</section>
			<section className="content-panel ml-table-panel">
				<div className="panel-heading"><div><div className="panel-kicker">EXPERIMENTOS REGISTRADOS</div><h2>Evaluaciones</h2></div><span className="table-count">{experiments.length} experimentos</span></div>
				{loading ? <p className="admin-empty">Cargando evaluaciones…</p> : experiments.length === 0 ? <p className="admin-empty">No hay modelos evaluados todavía.</p> : <div className="table-scroll"><table className="admin-table ml-table"><thead><tr><th>Experimento</th><th>Objetivo</th><th>Features</th><th>Métrica principal</th><th>Métrica secundaria</th><th>Baseline</th><th>Validación temporal</th></tr></thead><tbody>{experiments.map((experiment) => {
					const classification = experiment.task_type === "classification";
					const primary = classification ? experiment.metrics.f1_macro : experiment.metrics.mae;
					const secondary = classification ? experiment.metrics.accuracy : experiment.metrics.rmse;
					const baseline = classification ? experiment.metrics.baseline_f1_macro : experiment.metrics.mean_baseline_rmse;
					return <tr key={experiment.id}><td><strong>{experiment.name}</strong><span>{experiment.algorithm} · {experiment.status}</span></td><td>{experiment.target_name}</td><td>{experiment.feature_spec.join(", ")}</td><td>{classification ? "F1 macro" : "MAE"} · {primary.toFixed(3)}</td><td>{classification ? "Accuracy" : "RMSE"} · {secondary.toFixed(3)}</td><td>{typeof baseline === "number" ? baseline.toFixed(3) : "No registrado"}</td><td>{formatPeriod(experiment.validation_spec.evaluation_period)}<span>{experiment.validation_spec.row_count} eventos · corte cronológico</span>{experiment.validation_spec.confusion_matrix && <details><summary>Matriz de confusión</summary><pre>{JSON.stringify(experiment.validation_spec.confusion_matrix)}</pre></details>}</td></tr>;
				})}</tbody></table></div>}
			</section>
			<p className="source-disclaimer">Las métricas solo son interpretables con suficiente cobertura histórica y una variable objetivo válida. El feed actual del IGP informa el último evento, no un catálogo histórico.</p>
		</div>
	);
}