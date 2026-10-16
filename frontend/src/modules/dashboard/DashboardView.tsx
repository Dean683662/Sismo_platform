import {
	Activity,
	ArrowRight,
	Check,
	CircleDashed,
	Database,
	FileCheck2,
	GitBranch,
	MapPinned,
	Radio,
} from "lucide-react";
import { Link } from "react-router-dom";

const foundation = [
	{ title: "API de negocio", detail: "FastAPI · rutas versionadas", status: "listo", icon: Radio },
	{ title: "Interfaz modular", detail: "React + TypeScript · navegación", status: "listo", icon: GitBranch },
	{ title: "Persistencia", detail: "PostgreSQL · migración inicial", status: "listo", icon: Database },
	{ title: "Identidad y roles", detail: "Sesiones · permisos · auditoría", status: "listo", icon: FileCheck2 },
];

export default function DashboardView() {
	return (
		<div className="dashboard-page">
			<section className="dashboard-heading">
				<div>
					<div className="page-eyebrow"><span className="live-mark" /> VISTA GENERAL <span>·</span> ENTORNO DE DESARROLLO</div>
					<h1>Monitoreo sísmico</h1>
					<p className="page-lede">Centro de operación para eventos observados, análisis y fuentes verificables.</p>
				</div>
				<Link to="/fuentes" className="primary-action"><Database size={16} /><span>Configurar fuentes</span><ArrowRight size={16} /></Link>
			</section>

			<section className="notice-strip" aria-label="Estado de los datos">
				<span className="notice-icon"><Activity size={17} /></span>
				<div><strong>Sin datos sísmicos conectados</strong><span>Los indicadores aparecerán cuando se habilite una fuente y se implemente la ingesta.</span></div>
				<span className="notice-state">ESPERANDO FUENTE</span>
			</section>

			<section className="metric-grid" aria-label="Indicadores del sistema">
				<article className="metric-panel">
					<div className="metric-top"><span>Eventos registrados</span><Activity size={17} /></div>
					<strong className="metric-value">—</strong>
					<span className="metric-foot">Sin ingesta conectada</span>
				</article>
				<article className="metric-panel">
					<div className="metric-top"><span>Fuentes activas</span><Database size={17} /></div>
					<strong className="metric-value">—</strong>
					<span className="metric-foot">Proveedor por definir</span>
				</article>
				<article className="metric-panel">
					<div className="metric-top"><span>Última sincronización</span><Radio size={17} /></div>
					<strong className="metric-value metric-value-text">Sin actividad</strong>
					<span className="metric-foot">No hay procesos de ingesta</span>
				</article>
				<article className="metric-panel metric-panel-accent">
					<div className="metric-top"><span>Estado del proyecto</span><MapPinned size={17} /></div>
					<strong className="metric-value metric-value-text">Fase 1</strong>
					<span className="metric-foot">Base técnica y diseño UX</span>
				</article>
			</section>

			<div className="dashboard-columns">
				<section className="content-panel data-panel">
					<div className="panel-heading">
						<div><div className="panel-kicker">MONITOREO EN TIEMPO REAL</div><h2>Actividad sísmica</h2></div>
						<Link to="/eventos" className="quiet-link">Ver eventos <ArrowRight size={15} /></Link>
					</div>
					<div className="empty-chart">
						<div className="chart-grid-lines"><span /><span /><span /><span /></div>
						<div className="empty-chart-center"><span className="empty-chart-icon"><Activity size={23} /></span><strong>Sin actividad para mostrar</strong><span>Conecta una fuente de datos para iniciar el monitoreo.</span><Link to="/fuentes" className="inline-link">Revisar fuentes de datos <ArrowRight size={14} /></Link></div>
						<div className="chart-axis"><span>Hace 24 h</span><span>Ahora</span></div>
					</div>
				</section>

				<section className="content-panel foundation-panel">
					<div className="panel-heading">
						<div><div className="panel-kicker">BASE TÉCNICA</div><h2>Preparación de plataforma</h2></div>
							<span className="completion-count">4 <span>/ 4</span></span>
					</div>
					<div className="foundation-list">
						{foundation.map(({ title, detail, status, icon: Icon }) => (
							<div className="foundation-row" key={title}>
								<span className={`foundation-icon foundation-${status}`}><Icon size={16} /></span>
								<div className="foundation-copy"><strong>{title}</strong><span>{detail}</span></div>
								<span className={`foundation-status foundation-status-${status}`}>{status === "listo" ? <><Check size={13} /> LISTO</> : status === "siguiente" ? <><CircleDashed size={13} /> FASE 2</> : <><CircleDashed size={13} /> PENDIENTE</>}</span>
							</div>
						))}
					</div>
					<div className="foundation-foot"><span>Sin fuentes reales todavía</span><Link to="/fuentes">Ver dependencias <ArrowRight size={14} /></Link></div>
				</section>
			</div>

			<section className="bottom-note">
				<span className="note-mark">i</span>
				<p>El sistema diferencia los eventos reportados, las estimaciones experimentales y las alertas oficiales. Esta interfaz no predice terremotos.</p>
				<Link to="/analisis">Principios de análisis <ArrowRight size={14} /></Link>
			</section>
		</div>
	);
}