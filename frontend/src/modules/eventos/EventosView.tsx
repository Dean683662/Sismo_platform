import { useEffect, useState, type FormEvent } from "react";
import { ChevronLeft, ChevronRight, Filter, RotateCw } from "lucide-react";

import Button from "../../components/Button";
import SkeletonLoader from "../../components/SkeletonLoader";
import { listEvents } from "../../services/events.service";
import type { EventFilters, EventPage, SeismicEvent } from "../../types/event.types";
import EventoDetailModal from "./EventoDetailModal";
import EventosTable from "./EventosTable";

const pageSize = 25;

export default function EventosView() {
	const [filters, setFilters] = useState<EventFilters>({});
	const [draft, setDraft] = useState<EventFilters>({});
	const [page, setPage] = useState<EventPage>({ items: [], total: 0, limit: pageSize, offset: 0 });
	const [offset, setOffset] = useState(0);
	const [selectedEvent, setSelectedEvent] = useState<SeismicEvent | null>(null);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState("");
	const [refreshKey, setRefreshKey] = useState(0);

	useEffect(() => {
		let active = true;
		setLoading(true);
		listEvents(filters, pageSize, offset)
			.then((result) => { if (active) { setPage(result); setError(""); } })
			.catch(() => { if (active) setError("No se pudo consultar el catálogo. Verifica tu acceso o intenta nuevamente."); })
			.finally(() => { if (active) setLoading(false); });
		return () => { active = false; };
	}, [filters, offset, refreshKey]);

	function applyFilters(event: FormEvent<HTMLFormElement>) {
		event.preventDefault();
		const applied: EventFilters = {};
		if (draft.start_date) applied.start_date = `${draft.start_date}T00:00:00Z`;
		if (draft.end_date) applied.end_date = `${draft.end_date}T23:59:59Z`;
		if (draft.min_magnitude) applied.min_magnitude = draft.min_magnitude;
		if (draft.max_magnitude) applied.max_magnitude = draft.max_magnitude;
		setFilters(applied);
		setOffset(0);
	}

	function clearFilters() {
		setDraft({});
		setFilters({});
		setOffset(0);
	}

	const first = page.total === 0 ? 0 : offset + 1;
	const last = Math.min(offset + page.items.length, page.total);

	return (
		<div className="admin-page">
			<section className="admin-heading"><div><div className="page-eyebrow">OPERACIÓN <span>·</span> EVENTOS OBSERVADOS</div><h1>Eventos sísmicos</h1><p className="page-lede">Registros reportados por proveedores, con fecha UTC y procedencia verificable.</p></div><Button icon={<RotateCw size={15} />} onClick={() => setRefreshKey((value) => value + 1)} variant="secondary">Actualizar</Button></section>
			<form className="event-filters" onSubmit={applyFilters}>
				<div className="filter-heading"><Filter size={15} /><span>Filtros</span></div>
				<label>Desde UTC<input onChange={(event) => setDraft({ ...draft, start_date: event.target.value })} type="date" value={draft.start_date ?? ""} /></label>
				<label>Hasta UTC<input onChange={(event) => setDraft({ ...draft, end_date: event.target.value })} type="date" value={draft.end_date ?? ""} /></label>
				<label>Magnitud mín.<input max="10" min="0" onChange={(event) => setDraft({ ...draft, min_magnitude: event.target.value })} step="0.1" type="number" value={draft.min_magnitude ?? ""} /></label>
				<label>Magnitud máx.<input max="10" min="0" onChange={(event) => setDraft({ ...draft, max_magnitude: event.target.value })} step="0.1" type="number" value={draft.max_magnitude ?? ""} /></label>
				<div className="filter-actions"><Button type="submit">Aplicar</Button><Button onClick={clearFilters} variant="quiet">Limpiar</Button></div>
			</form>
			<section className="content-panel admin-table-panel">
				<div className="panel-heading"><div><div className="panel-kicker">CATÁLOGO PAGINADO</div><h2>Eventos registrados</h2></div><span className="table-count">{page.total} registros</span></div>
				{error && <p className="admin-error" role="alert">{error}</p>}
				{loading ? <div className="admin-loading"><SkeletonLoader lines={6} /></div> : page.items.length === 0 ? <p className="admin-empty">No hay eventos que coincidan con los filtros aplicados.</p> : <EventosTable events={page.items} onSelect={setSelectedEvent} />}
				<div className="pagination-bar"><span>{first}–{last} de {page.total}</span><div><button aria-label="Página anterior" disabled={offset === 0 || loading} onClick={() => setOffset(Math.max(0, offset - pageSize))} type="button"><ChevronLeft size={16} /></button><button aria-label="Página siguiente" disabled={offset + pageSize >= page.total || loading} onClick={() => setOffset(offset + pageSize)} type="button"><ChevronRight size={16} /></button></div></div>
			</section>
			<p className="source-disclaimer">El endpoint público verificado del IGP entrega el último evento reportado; no equivale a un catálogo histórico completo.</p>
			<EventoDetailModal event={selectedEvent} onClose={() => setSelectedEvent(null)} />
		</div>
	);
}