import { useState, type FormEvent } from "react";
import { Plus, RadioTower } from "lucide-react";

import Button from "../../components/Button";
import type { DataSource } from "../../types/event.types";
import { createAlertRule } from "../../services/alerts.service";

const defaultTemplate = "Sismo de magnitud {magnitude} en {place} (fuente: {source_name}).";

export default function RuleBuilder({ sources, onCreated }: { sources: DataSource[]; onCreated: () => void }) {
	const [busy, setBusy] = useState(false);
	const [error, setError] = useState("");

	async function submitRule(event: FormEvent<HTMLFormElement>) {
		event.preventDefault();
		const formElement = event.currentTarget;
		const form = new FormData(formElement);
		const boundsFields = ["min_latitude", "max_latitude", "min_longitude", "max_longitude"];
		const rawBounds = boundsFields.map((key) => String(form.get(key) ?? "").trim());
		const hasPartialBounds = rawBounds.some(Boolean) && rawBounds.some((value) => !value);
		if (hasPartialBounds) {
			setError("Completa los cuatro límites geográficos o déjalos todos vacíos.");
			return;
		}
		setBusy(true);
		setError("");
		try {
			await createAlertRule({
				name: String(form.get("name")),
				is_enabled: true,
				min_magnitude: Number(form.get("min_magnitude")),
				min_depth_km: form.get("min_depth_km") ? Number(form.get("min_depth_km")) : null,
				region_bounds: rawBounds.every(Boolean)
					? Object.fromEntries(boundsFields.map((key, index) => [key, Number(rawBounds[index])]))
					: null,
				source_ids: form.getAll("source_ids").map(String),
				channel: String(form.get("channel")) as "in_app" | "webhook",
				requires_approval: form.get("requires_approval") === "on",
				template: String(form.get("template")),
			});
			formElement.reset();
			onCreated();
		} catch (requestError) {
			setError(requestError instanceof Error ? requestError.message : "No se pudo guardar la regla.");
		} finally {
			setBusy(false);
		}
	}

	const activeSources = sources.filter((source) => source.is_verified);

	return (
		<section className="content-panel alert-builder">
			<div className="panel-heading">
				<div><div className="panel-kicker">REGLAS OPERATIVAS</div><h2>Crear regla de alerta</h2></div>
				<RadioTower size={18} aria-hidden="true" />
			</div>
			<form className="alert-form" onSubmit={(event) => void submitRule(event)}>
				{error && <p className="admin-error" role="alert">{error}</p>}
				<div className="alert-form-grid">
					<label>Nombre de la regla<input maxLength={120} minLength={2} name="name" required /></label>
					<label>Magnitud mínima<input max={10} min={0} name="min_magnitude" required step="0.1" type="number" /></label>
					<label>Profundidad mínima (km)<input max={1000} min={0} name="min_depth_km" step="1" type="number" /></label>
					<label>Canal de entrega<select defaultValue="in_app" name="channel"><option value="in_app">Bandeja interna</option><option value="webhook">Webhook configurado en el servidor</option></select></label>
					<fieldset className="alert-source-options">
						<legend>Fuentes verificadas</legend>
						{activeSources.length === 0 ? <span>No hay fuentes verificadas disponibles.</span> : activeSources.map((source) => (
							<label key={source.id}><input name="source_ids" type="checkbox" value={source.id} /><span>{source.name}</span></label>
						))}
						<small>Si no seleccionas ninguna, aplicará a todas las fuentes verificadas activas.</small>
					</fieldset>
					<fieldset className="alert-region-options">
						<legend>Zona geográfica (opcional, rectángulo)</legend>
						<label>Latitud mínima<input max={90} min={-90} name="min_latitude" step="any" type="number" /></label>
						<label>Latitud máxima<input max={90} min={-90} name="max_latitude" step="any" type="number" /></label>
						<label>Longitud mínima<input max={180} min={-180} name="min_longitude" step="any" type="number" /></label>
						<label>Longitud máxima<input max={180} min={-180} name="max_longitude" step="any" type="number" /></label>
					</fieldset>
					<label className="alert-template">Plantilla del mensaje<textarea defaultValue={defaultTemplate} maxLength={500} name="template" required rows={2} /><small>Campos permitidos: {"{magnitude}"}, {"{place}"}, {"{occurred_at}"}, {"{source_name}"}.</small></label>
					<label className="alert-approval"><input name="requires_approval" type="checkbox" /><span>Requerir aprobación humana antes de entregar</span></label>
				</div>
				<div className="alert-form-footer">
					<p>Webhook: la URL se configura de forma privada en el servidor y recibe el evento con clave de idempotencia.</p>
					<Button disabled={busy || activeSources.length === 0} icon={<Plus size={15} />} type="submit">{busy ? "Guardando…" : "Guardar regla"}</Button>
				</div>
			</form>
		</section>
	);
}