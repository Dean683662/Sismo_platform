import { useEffect, useState } from "react";
import { CircleMarker, MapContainer, Popup, TileLayer } from "react-leaflet";
import { ExternalLink, MapPinned } from "lucide-react";
import "leaflet/dist/leaflet.css";

import { getEventGeoJson } from "../../services/analytics.service";
import type { EventFeature } from "../../types/analytics.types";

export default function MapView() {
	const [events, setEvents] = useState<EventFeature[]>([]);
	const [error, setError] = useState("");

	useEffect(() => {
		let active = true;
		getEventGeoJson()
			.then((result) => { if (active) { setEvents(result.features); setError(""); } })
			.catch(() => { if (active) setError("No se pudo consultar la ubicación de los eventos."); });
		return () => { active = false; };
	}, []);

	return (
		<div className="map-page">
			<section className="admin-heading"><div><div className="page-eyebrow">OPERACIÓN <span>·</span> UBICACIÓN REPORTADA</div><h1>Mapa sísmico</h1><p className="page-lede">Eventos observados y su procedencia. El mapa no representa zonas de impacto.</p></div><span className="map-count"><MapPinned size={15} /> {events.length.toLocaleString("es-PE")} puntos</span></section>
			{error && <p className="admin-error" role="alert">{error}</p>}
			<section className="content-panel map-panel">
				<div className="map-frame">
					<MapContainer center={[-9.19, -75.015]} zoom={4} scrollWheelZoom className="event-map">
						<TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
						{events.map((event) => {
							const [longitude, latitude] = event.geometry.coordinates;
							return <CircleMarker key={event.id} center={[latitude, longitude]} radius={Math.max(5, Math.min(12, 4 + event.properties.magnitude * 1.1))} pathOptions={{ color: "#f8fcfa", weight: 2, fillColor: event.properties.magnitude >= 5 ? "#c26f38" : "#087f78", fillOpacity: 0.9 }}><Popup><strong>{event.properties.place}</strong><br />Magnitud {event.properties.magnitude.toFixed(1)} · {event.properties.depth_km.toFixed(0)} km<br />{new Date(event.properties.occurred_at).toLocaleString("es-PE", { timeZone: "UTC" })} UTC<br />Fuente: {event.properties.source_key}{event.properties.source_url && <><br /><a href={event.properties.source_url} rel="noreferrer" target="_blank">Abrir fuente <ExternalLink size={12} /></a></>}</Popup></CircleMarker>;
						})}
					</MapContainer>
				</div>
				<div className="map-footer"><span><i className="map-legend-dot" /> Evento reportado</span><span>El tamaño y color representan magnitud reportada, no intensidad ni riesgo.</span></div>
			</section>
			<p className="source-disclaimer">Cartografía base © OpenStreetMap contributors. Las coordenadas proceden de la fuente y se muestran sin estimar impacto.</p>
		</div>
	);
}