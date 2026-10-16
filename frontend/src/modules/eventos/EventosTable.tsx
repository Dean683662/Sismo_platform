import { ArrowUpRight } from "lucide-react";

import type { SeismicEvent } from "../../types/event.types";

function formatDate(value: string): string {
	return new Date(value).toLocaleString("es-PE", { timeZone: "UTC", dateStyle: "medium", timeStyle: "short" });
}

export default function EventosTable({ events, onSelect }: { events: SeismicEvent[]; onSelect: (event: SeismicEvent) => void }) {
	return (
		<div className="table-scroll">
			<table className="admin-table events-table">
				<thead><tr><th>Fecha UTC</th><th>Ubicación reportada</th><th>Magnitud</th><th>Profundidad</th><th>Fuente</th><th><span className="sr-only">Detalle</span></th></tr></thead>
				<tbody>{events.map((event) => <tr key={event.id}>
					<td>{formatDate(event.occurred_at)}</td>
					<td><strong>{event.place}</strong><span>ID externo {event.external_id}</span></td>
					<td><span className="magnitude-value">{event.magnitude.toFixed(1)}</span></td>
					<td>{event.depth_km.toFixed(1)} km</td>
					<td><span className="event-source-label">{event.source_key.toUpperCase()}</span></td>
					<td><button aria-label={`Ver evento ${event.external_id}`} className="event-open-button" onClick={() => onSelect(event)} type="button"><ArrowUpRight size={16} /></button></td>
				</tr>)}</tbody>
			</table>
		</div>
	);
}