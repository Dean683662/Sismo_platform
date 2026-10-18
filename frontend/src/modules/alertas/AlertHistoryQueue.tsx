import { Check, RotateCw, ShieldAlert, X } from "lucide-react";

import Button from "../../components/Button";
import type { AlertDelivery } from "../../services/alerts.service";

const statusLabels: Record<AlertDelivery["status"], string> = {
	pending_approval: "Pendiente de aprobación",
	queued: "En cola",
	delivered: "Entregada",
	rejected: "Rechazada",
	failed: "Fallida",
};

export default function AlertHistoryQueue({
	deliveries,
	canManage,
	busyId,
	onApprove,
	onReject,
	onRetry,
}: {
	deliveries: AlertDelivery[];
	canManage: boolean;
	busyId: string;
	onApprove: (delivery: AlertDelivery) => void;
	onReject: (delivery: AlertDelivery) => void;
	onRetry: (delivery: AlertDelivery) => void;
}) {
	return (
		<section className="content-panel alert-history-panel">
			<div className="panel-heading"><div><div className="panel-kicker">TRAZABILIDAD</div><h2>Historial y cola de aprobaciones</h2></div><span className="table-count">{deliveries.length} registros</span></div>
			{deliveries.length === 0 ? <p className="admin-empty">Todavía no hay alertas. Las reglas evaluarán los nuevos eventos recibidos desde fuentes verificadas.</p> : (
				<div className="alert-delivery-list">
					{deliveries.map((delivery) => (
						<article className="alert-delivery" key={delivery.id}>
							<div className="alert-delivery-status">
								<span className={`alert-state alert-state-${delivery.status}`}><ShieldAlert size={13} />{statusLabels[delivery.status]}</span>
								{delivery.is_test && <span className="alert-test-tag">Prueba</span>}
							</div>
							<div className="alert-delivery-content">
								<strong>{delivery.rule_name} · M{delivery.event_magnitude.toFixed(1)}</strong>
								<p>{delivery.message}</p>
								<span>{delivery.event_place} · {delivery.source_name} · {new Date(delivery.created_at).toLocaleString("es-PE", { timeZone: "UTC", dateStyle: "medium", timeStyle: "short" })} UTC</span>
								{delivery.last_error && <span className="admin-error">{delivery.last_error}</span>}
								<span>Canal {delivery.channel.replaceAll("_", " ")} · intentos {delivery.attempt_count}</span>
							</div>
							{canManage && delivery.status === "pending_approval" && <div className="alert-delivery-actions">
								<Button disabled={busyId === delivery.id} icon={<Check size={14} />} onClick={() => onApprove(delivery)}>Aprobar</Button>
								<Button disabled={busyId === delivery.id} icon={<X size={14} />} onClick={() => onReject(delivery)} variant="secondary">Rechazar</Button>
							</div>}
							{canManage && delivery.status === "failed" && delivery.attempt_count < 3 && <Button disabled={busyId === delivery.id} icon={<RotateCw size={14} />} onClick={() => onRetry(delivery)} variant="secondary">Reintentar</Button>}
						</article>
					))}
				</div>
			)}
		</section>
	);
}