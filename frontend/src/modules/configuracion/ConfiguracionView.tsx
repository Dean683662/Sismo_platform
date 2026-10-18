import { useEffect, useState, type FormEvent } from "react";
import { DatabaseBackup, Save, Trash2 } from "lucide-react";

import Button from "../../components/Button";
import SkeletonLoader from "../../components/SkeletonLoader";
import { getPlatformSettings, runRetentionCleanup, updatePlatformSettings, type PlatformSettings } from "../../services/admin.service";

const defaults: PlatformSettings = {
	audit_retention_days: 365,
	alert_history_retention_days: 180,
	report_retention_days: 365,
};

export default function ConfiguracionView() {
	const [settings, setSettings] = useState<PlatformSettings>(defaults);
	const [loading, setLoading] = useState(true);
	const [saving, setSaving] = useState(false);
	const [cleaning, setCleaning] = useState(false);
	const [error, setError] = useState("");
	const [notice, setNotice] = useState("");

	useEffect(() => {
		let active = true;
		getPlatformSettings()
			.then((value) => { if (active) setSettings(value); })
			.catch((requestError: unknown) => {
				if (active) setError(requestError instanceof Error ? requestError.message : "No se pudo consultar la configuración.");
			})
			.finally(() => { if (active) setLoading(false); });
		return () => { active = false; };
	}, []);

	async function saveSettings(event: FormEvent<HTMLFormElement>) {
		event.preventDefault();
		const form = new FormData(event.currentTarget);
		setSaving(true);
		setError("");
		setNotice("");
		try {
			const updated = await updatePlatformSettings({
				audit_retention_days: Number(form.get("audit_retention_days")),
				alert_history_retention_days: Number(form.get("alert_history_retention_days")),
				report_retention_days: Number(form.get("report_retention_days")),
			});
			setSettings(updated);
			setNotice("Configuración de retención guardada.");
		} catch (requestError) {
			setError(requestError instanceof Error ? requestError.message : "No se pudo guardar la configuración.");
		} finally {
			setSaving(false);
		}
	}

	async function cleanupHistory() {
		if (!window.confirm("Se eliminarán los registros de auditoría y las entregas terminales anteriores al periodo configurado. ¿Continuar?")) return;
		setCleaning(true);
		setError("");
		setNotice("");
		try {
			const result = await runRetentionCleanup();
			setNotice(
				`Retención completada: ${result.deleted_audit_logs} auditorías, ${result.deleted_alert_deliveries} entregas y ${result.deleted_report_snapshots} reportes eliminados.`,
			);
		} catch (requestError) {
			setError(requestError instanceof Error ? requestError.message : "No se pudo ejecutar la retención.");
		} finally {
			setCleaning(false);
		}
	}

	return (
		<div className="admin-page">
			<section className="admin-heading"><div><div className="page-eyebrow">PLATAFORMA <span>·</span> ADMINISTRACIÓN</div><h1>Configuración</h1><p className="page-lede">Retención controlada de bitácora y entregas de alertas.</p></div></section>
			{error && <p className="admin-error" role="alert">{error}</p>}
			{notice && <p className="sync-notice" role="status">{notice}</p>}
			{loading ? <section className="content-panel admin-loading"><SkeletonLoader lines={4} /></section> : (
				<section className="content-panel retention-panel">
					<div className="panel-heading"><div><div className="panel-kicker">CICLO DE VIDA DE DATOS</div><h2>Política de retención</h2></div><DatabaseBackup size={18} aria-hidden="true" /></div>
					<form className="retention-form" onSubmit={(event) => void saveSettings(event)}>
						<label>Bitácora de auditoría (días)<input defaultValue={settings.audit_retention_days} max={3650} min={30} name="audit_retention_days" required type="number" /><small>Mínimo 30 días; máximo 10 años.</small></label>
						<label>Historial de alertas (días)<input defaultValue={settings.alert_history_retention_days} max={3650} min={7} name="alert_history_retention_days" required type="number" /><small>Las alertas pendientes de aprobación no se eliminan.</small></label>
						<label>Snapshots de reportes (días)<input defaultValue={settings.report_retention_days} max={3650} min={30} name="report_retention_days" required type="number" /><small>El vencimiento elimina snapshots antiguos al ejecutar la limpieza.</small></label>
						<div className="retention-form-actions"><Button disabled={saving} icon={<Save size={15} />} type="submit">{saving ? "Guardando…" : "Guardar política"}</Button></div>
					</form>
					<div className="retention-warning"><strong>Alcance de la limpieza manual</strong><p>Elimina bitácora, entregas terminales y snapshots de reportes vencidos; conserva eventos sísmicos, datasets y alertas pendientes.</p><Button disabled={cleaning} icon={<Trash2 size={14} />} onClick={() => void cleanupHistory()} variant="danger">{cleaning ? "Ejecutando…" : "Ejecutar retención ahora"}</Button></div>
				</section>
			)}
		</div>
	);
}
