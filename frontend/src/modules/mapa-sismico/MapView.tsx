import { useEffect, useState, type FormEvent } from "react";
import { CircleMarker, MapContainer, Popup, TileLayer } from "react-leaflet";
import { ExternalLink, MapPinned, RefreshCw } from "lucide-react";
import "leaflet/dist/leaflet.css";

import { getEventGeoJson } from "../../services/analytics.service";
import type { EventFeature } from "../../types/analytics.types";

interface MapFilters {
	startDate: string;
	endDate: string;
	minMagnitude: string;
	maxMagnitude: string;
	minLatitude: string;
	maxLatitude: string;
	minLongitude: string;
	maxLongitude: string;
}

const emptyFilters: MapFilters = {
	startDate: "",
	endDate: "",
	minMagnitude: "",
	maxMagnitude: "",
	minLatitude: "",
	maxLatitude: "",
	minLongitude: "",
	maxLongitude: "",
};

function utcBoundary(value: string, endOfDay = false): string | undefined {
	if (!value) return undefined;
	return `${value}T${endOfDay ? "23:59:59.999" : "00:00:00"}Z`;
}

export default function MapView() {
	const [events, setEvents] = useState<EventFeature[]>([]);
	const [error, setError] = useState("");
	const [loading, setLoading] = useState(true);
	const [filters, setFilters] = useState<MapFilters>(emptyFilters);
	const [appliedFilters, setAppliedFilters] = useState<MapFilters>(emptyFilters);
	const [refreshKey, setRefreshKey] = useState(0);

	useEffect(() => {
		let active = true;
		setLoading(true);
		const optionalNumber = (value: string) => value ? Number(value) : undefined;
		getEventGeoJson({
			startDate: utcBoundary(appliedFilters.startDate),
			endDate: utcBoundary(appliedFilters.endDate, true),
			minMagnitude: optionalNumber(appliedFilters.minMagnitude),
			maxMagnitude: optionalNumber(appliedFilters.maxMagnitude),
			minLatitude: optionalNumber(appliedFilters.minLatitude),
			maxLatitude: optionalNumber(appliedFilters.maxLatitude),
			minLongitude: optionalNumber(appliedFilters.minLongitude),
			maxLongitude: optionalNumber(appliedFilters.maxLongitude),
		})
			.then((result) => { if (active) { setEvents(result.features); setError(""); } })
			.catch(() => { if (active) setError("No se pudo consultar la ubicación de los eventos."); })
			.finally(() => { if (active) setLoading(false); });
		return () => { active = false; };
	}, [appliedFilters, refreshKey]);

	function applyFilters(event: FormEvent<HTMLFormElement>) {
		event.preventDefault();
		const bounds = [filters.minLatitude, filters.maxLatitude, filters.minLongitude, filters.maxLongitude];
		if (bounds.some(Boolean) && bounds.some((value) => !value)) {
			setError("Para filtrar por zona, completa los cuatro límites geográficos.");
			return;
		}
		if (filters.startDate && filters.endDate && filters.startDate > filters.endDate) {
			setError("La fecha inicial no puede ser posterior a la fecha final.");
			return;
		}
		if (filters.minMagnitude && filters.maxMagnitude && Number(filters.minMagnitude) > Number(filters.maxMagnitude)) {
			setError("La magnitud mínima no puede superar la máxima.");
			return;
		}
		if (bounds.every(Boolean) && (Number(filters.minLatitude) >= Number(filters.maxLatitude) || Number(filters.minLongitude) >= Number(filters.maxLongitude))) {
			setError("Los límites mínimos de latitud y longitud deben ser menores que los máximos.");
			return;
		}
		setError("");
		setAppliedFilters({ ...filters });
	}

	return (
		<div className="map-page">
			<section className="admin-heading"><div><div className="page-eyebrow">OPERACIÓN <span>·</span> UBICACIÓN REPORTADA</div><h1>Mapa sísmico</h1><p className="page-lede">Eventos observados y su procedencia. El mapa no representa zonas de impacto.</p></div><div className="map-heading-actions"><span className="map-count"><MapPinned size={15} /> {loading ? "Consultando…" : `${events.length.toLocaleString("es-PE")} puntos`}</span><button aria-label="Actualizar mapa" className="icon-button" onClick={() => setRefreshKey((value) => value + 1)} title="Actualizar mapa" type="button"><RefreshCw size={15} /></button></div></section>
			<form className="content-panel map-filter-form" onSubmit={applyFilters}>
				<label>Desde (UTC)<input aria-label="Fecha inicial UTC" max={filters.endDate || undefined} onChange={(event) => setFilters({ ...filters, startDate: event.target.value })} type="date" value={filters.startDate} /></label>
				<label>Hasta (UTC)<input aria-label="Fecha final UTC" min={filters.startDate || undefined} onChange={(event) => setFilters({ ...filters, endDate: event.target.value })} type="date" value={filters.endDate} /></label>
				<label>Magnitud mínima<input aria-label="Magnitud mínima" max={10} min={0} onChange={(event) => setFilters({ ...filters, minMagnitude: event.target.value })} step="0.1" type="number" value={filters.minMagnitude} /></label>
				<label>Magnitud máxima<input aria-label="Magnitud máxima" max={10} min={0} onChange={(event) => setFilters({ ...filters, maxMagnitude: event.target.value })} step="0.1" type="number" value={filters.maxMagnitude} /></label>
				<label>Latitud mínima<input aria-label="Latitud mínima" max={90} min={-90} onChange={(event) => setFilters({ ...filters, minLatitude: event.target.value })} step="any" type="number" value={filters.minLatitude} /></label>
				<label>Latitud máxima<input aria-label="Latitud máxima" max={90} min={-90} onChange={(event) => setFilters({ ...filters, maxLatitude: event.target.value })} step="any" type="number" value={filters.maxLatitude} /></label>
				<label>Longitud mínima<input aria-label="Longitud mínima" max={180} min={-180} onChange={(event) => setFilters({ ...filters, minLongitude: event.target.value })} step="any" type="number" value={filters.minLongitude} /></label>
				<label>Longitud máxima<input aria-label="Longitud máxima" max={180} min={-180} onChange={(event) => setFilters({ ...filters, maxLongitude: event.target.value })} step="any" type="number" value={filters.maxLongitude} /></label>
				<div className="map-filter-actions"><span>Hasta 5.000 eventos · UTC</span><button className="primary-action" type="submit">Aplicar filtros</button></div>
			</form>
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