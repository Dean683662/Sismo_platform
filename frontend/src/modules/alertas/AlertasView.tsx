import { useCallback, useEffect, useState } from "react";
import { BellRing, CircleCheck, RotateCw, Send } from "lucide-react";

import Button from "../../components/Button";
import SkeletonLoader from "../../components/SkeletonLoader";
import { useAuth } from "../../hooks/useAuth";
import {
	approveAlert,
	listAlertDeliveries,
	listAlertRules,
	rejectAlert,
	retryAlert,
	sendTestAlert,
	updateAlertRule,
	type AlertDelivery,
	type AlertRule,
} from "../../services/alerts.service";
import { listDataSources } from "../../services/sources.service";
import type { DataSource } from "../../types/event.types";
import AlertHistoryQueue from "./AlertHistoryQueue";
import RuleBuilder from "./RuleBuilder";

export default function AlertasView() {
	const { hasPermission } = useAuth();
	const canManage = hasPermission("alerts:manage");
	const [rules, setRules] = useState<AlertRule[]>([]);
	const [deliveries, setDeliveries] = useState<AlertDelivery[]>([]);
	const [sources, setSources] = useState<DataSource[]>([]);
	const [loading, setLoading] = useState(true);
	const [busyId, setBusyId] = useState("");
	const [error, setError] = useState("");
	const [notice, setNotice] = useState("");
	const [refreshKey, setRefreshKey] = useState(0);

	const refresh = useCallback(() => {
		setLoading(true);
		Promise.all([listAlertRules(), listAlertDeliveries(), listDataSources()])
			.then(([ruleList, deliveryList, sourceList]) => {
				setRules(ruleList);
				setDeliveries(deliveryList);
				setSources(sourceList);
				setError("");
			})
			.catch((requestError: unknown) => {
				setError(requestError instanceof Error ? requestError.message : "No se pudo cargar el centro de alertas.");
			})
			.finally(() => setLoading(false));
	}, []);

	useEffect(() => { refresh(); }, [refresh, refreshKey]);

	async function runAction(id: string, action: () => Promise<unknown>, successMessage: string) {
		setBusyId(id);
		setError("");
		setNotice("");
		try {
			await action();
			setNotice(successMessage);
			setRefreshKey((value) => value + 1);
		} catch (requestError) {
			setError(requestError instanceof Error ? requestError.message : "No se pudo completar la operación.");
		} finally {
			setBusyId("");
		}
	}

	return (
		<div className="admin-page">
			<section className="admin-heading">
				<div><div className="page-eyebrow">PLATAFORMA <span>·</span> CENTRO OPERATIVO</div><h1>Centro de alertas</h1><p className="page-lede">Reglas sobre eventos reportados por fuentes verificadas; cada evaluación queda asociada a su fuente y evento.</p></div>
				<Button icon={<RotateCw size={15} />} onClick={() => setRefreshKey((value) => value + 1)} variant="secondary">Actualizar</Button>
			</section>
			<p className="alert-disclaimer"><BellRing size={15} /> Las alertas pueden enviarse a la bandeja interna o al webhook configurado por el administrador. No son avisos oficiales a la población.</p>
			{error && <p className="admin-error" role="alert">{error}</p>}
			{notice && <p className="sync-notice" role="status">{notice}</p>}
			{canManage && <RuleBuilder onCreated={() => { setNotice("La regla quedó guardada y se evaluará en los próximos eventos recibidos."); setRefreshKey((value) => value + 1); }} sources={sources} />}
			<section className="content-panel alert-rules-panel">
				<div className="panel-heading"><div><div className="panel-kicker">UMBRAL, ZONA Y FUENTE</div><h2>Reglas configuradas</h2></div><span className="table-count">{rules.length} reglas</span></div>
				{loading ? <div className="admin-loading"><SkeletonLoader lines={4} /></div> : rules.length === 0 ? <p className="admin-empty">No hay reglas configuradas.</p> : (
					<div className="alert-rule-list">
						{rules.map((rule) => (
							<article className="alert-rule" key={rule.id}>
								<div className="alert-rule-main">
									<span className={`account-state ${rule.is_enabled ? "account-active" : "account-inactive"}`}><i />{rule.is_enabled ? "Activa" : "Pausada"}</span>
									<div><strong>{rule.name}</strong><span>Magnitud ≥ {rule.min_magnitude.toFixed(1)}{rule.min_depth_km === null ? "" : ` · profundidad ≥ ${rule.min_depth_km} km`}</span>
										<span>{rule.source_ids.length ? `${rule.source_ids.length} fuente(s) seleccionada(s)` : "Todas las fuentes verificadas activas"}{rule.region_bounds ? " · Zona delimitada" : " · Sin restricción geográfica"}</span>
										<span>{rule.requires_approval ? "Requiere aprobación humana" : "Entrega automática"} · {rule.channel === "webhook" ? "Webhook externo" : "Bandeja interna"}</span>
									</div>
								</div>
								{canManage && <div className="alert-rule-actions">
									<Button disabled={Boolean(busyId)} icon={<Send size={14} />} onClick={() => void runAction(rule.id, () => sendTestAlert(rule.id), "Alerta de prueba creada con un evento reciente de una fuente verificada.")} variant="secondary">Probar</Button>
									<Button disabled={Boolean(busyId)} icon={<CircleCheck size={14} />} onClick={() => void runAction(rule.id, () => updateAlertRule(rule.id, { is_enabled: !rule.is_enabled }), rule.is_enabled ? "Regla pausada." : "Regla activada.")} variant="quiet">{rule.is_enabled ? "Pausar" : "Activar"}</Button>
								</div>}
							</article>
						))}
					</div>
				)}
			</section>
			{loading ? <section className="content-panel admin-loading"><SkeletonLoader lines={5} /></section> : (
				<AlertHistoryQueue
					busyId={busyId}
					canManage={canManage}
					deliveries={deliveries}
					onApprove={(delivery) => void runAction(delivery.id, () => approveAlert(delivery.id), "Alerta aprobada; consulta su estado de entrega.")}
					onReject={(delivery) => void runAction(delivery.id, () => rejectAlert(delivery.id), "Alerta rechazada y auditada.")}
					onRetry={(delivery) => void runAction(delivery.id, () => retryAlert(delivery.id), "Entrega reintentada.")}
				/>
			)}
		</div>
	);
}