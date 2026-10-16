import { ExternalLink, MapPin } from "lucide-react";

import Modal from "../../components/Modal";
import type { SeismicEvent } from "../../types/event.types";

function formatDate(value: string): string {
	return new Date(value).toLocaleString("es-PE", { timeZone: "UTC", dateStyle: "long", timeStyle: "short" }) + " UTC";
}

export default function EventoDetailModal({ event, onClose }: { event: SeismicEvent | null; onClose: () => void }) {
	return (
		<Modal open={event !== null} onClose={onClose} title="Detalle del evento observado">
			{event && <div className="event-detail">
				<div className="event-detail-place"><MapPin size={18} /><div><strong>{event.place}</strong><span>Reportado por {event.source_key.toUpperCase()} · {event.external_id}</span></div></div>
				<dl className="event-detail-grid">
					<div><dt>Fecha y hora</dt><dd>{formatDate(event.occurred_at)}</dd></div>
					<div><dt>Magnitud</dt><dd>{event.magnitude.toFixed(1)}{event.magnitude_type ? ` ${event.magnitude_type}` : ""}</dd></div>
					<div><dt>Profundidad</dt><dd>{event.depth_km.toFixed(1)} km</dd></div>
					<div><dt>Coordenadas</dt><dd>{event.latitude.toFixed(3)}, {event.longitude.toFixed(3)}</dd></div>
					<div><dt>Estado del registro</dt><dd>Evento reportado</dd></div>
					<div><dt>Recibido por la plataforma</dt><dd>{formatDate(event.received_at)}</dd></div>
				</dl>
				{event.source_url && <a className="source-link" href={event.source_url} rel="noreferrer" target="_blank"><span>Ver referencia del proveedor</span><ExternalLink size={14} /></a>}
			</div>}
		</Modal>
	);
}