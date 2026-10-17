import { lazy, Suspense } from "react";
import { ArrowUpRight, Construction } from "lucide-react";
import { Link, Route, Routes, useLocation } from "react-router-dom";

import { useAuth } from "../hooks/useAuth";
import AuditoriaView from "../modules/auditoria/AuditoriaView";
import DashboardView from "../modules/dashboard/DashboardView";
import EventosView from "../modules/eventos/EventosView";
import FuentesView from "../modules/fuentes-datos/FuentesView";
import UsuariosView from "../modules/usuarios-roles/UsuariosView";

const AnalisisView = lazy(() => import("../modules/analisis/AnalisisView"));
const MapView = lazy(() => import("../modules/mapa-sismico/MapView"));
const ModelosMLView = lazy(() => import("../modules/modelos-ml/ModelosMLView"));

function LazyModule({ children }: { children: React.ReactNode }) {
	return <Suspense fallback={<div className="auth-loading" role="status">Cargando módulo…</div>}>{children}</Suspense>;
}

const modules: Record<string, { title: string; group: string; description: string; permission?: string }> = {
	"/eventos": { title: "Eventos sísmicos", group: "Operación", description: "Catálogo de eventos reportados, con procedencia, filtros y detalle.", permission: "events:read" },
	"/mapa": { title: "Mapa sísmico", group: "Operación", description: "Exploración geográfica de eventos observados y sus metadatos.", permission: "events:read" },
	"/analisis": { title: "Análisis estadístico", group: "Análisis", description: "Series históricas, distribuciones y métricas descriptivas.", permission: "analytics:read" },
	"/modelos": { title: "Modelos ML", group: "Análisis", description: "Registro y evaluación reproducible de experimentos supervisados.", permission: "models:read" },
	"/estimaciones": { title: "Estimaciones experimentales", group: "Análisis", description: "Resultados exploratorios con incertidumbre y versión del modelo.", permission: "estimates:read" },
	"/reportes": { title: "Reportes", group: "Análisis", description: "Informes operativos y analíticos con filtros y fecha de corte.", permission: "reports:read" },
	"/alertas": { title: "Centro de alertas", group: "Plataforma", description: "Seguimiento de reglas, aprobaciones y entregas verificables.", permission: "alerts:read" },
	"/fuentes": { title: "Fuentes de datos", group: "Plataforma", description: "Conectores, licencias y estado de sincronización de proveedores.", permission: "sources:read" },
	"/configuracion": { title: "Configuración", group: "Plataforma", description: "Parámetros generales del entorno y operación.", permission: "settings:manage" },
};

function ModulePlaceholder() {
	const { pathname } = useLocation();
	const { hasPermission } = useAuth();
	const module = modules[pathname];

	if (!module) return <DashboardView />;
	if (module.permission && !hasPermission(module.permission)) {
		return <section className="module-placeholder"><div className="page-eyebrow">ACCESO RESTRINGIDO</div><h1>Permiso insuficiente</h1><p className="page-lede">Tu rol no permite consultar este módulo.</p></section>;
	}

	return (
		<section className="module-placeholder">
			<div className="page-eyebrow">{module.group} <span>·</span> MÓDULO PREPARADO</div>
			<h1>{module.title}</h1>
			<p className="page-lede">{module.description}</p>
			<div className="placeholder-panel">
				<span className="placeholder-icon"><Construction size={21} /></span>
				<div>
					<h2>Vista pendiente de implementación</h2>
					<p>La navegación está preparada. Este módulo se habilitará cuando se completen sus dependencias de datos y las fases correspondientes.</p>
					{pathname === "/fuentes" && <p className="source-note">Antes de conectar una fuente, se deben confirmar sus canales oficiales, licencia y condiciones de uso.</p>}
				</div>
				<Link className="text-link" to="/"><span>Volver al resumen</span><ArrowUpRight size={16} /></Link>
			</div>
		</section>
	);
}

export default function Router() {
	return (
		<Routes>
			<Route path="/" element={<DashboardView />} />
			<Route path="/eventos" element={<ProtectedModule permission="events:read"><EventosView /></ProtectedModule>} />
			<Route path="/mapa" element={<ProtectedModule permission="events:read"><LazyModule><MapView /></LazyModule></ProtectedModule>} />
			<Route path="/analisis" element={<ProtectedModule permission="analytics:read"><LazyModule><AnalisisView /></LazyModule></ProtectedModule>} />
			<Route path="/modelos" element={<ProtectedModule permission="models:read"><LazyModule><ModelosMLView /></LazyModule></ProtectedModule>} />
			<Route path="/fuentes" element={<ProtectedModule permission="sources:read"><FuentesView /></ProtectedModule>} />
			<Route path="/usuarios" element={<ProtectedModule permission="users:read"><UsuariosView /></ProtectedModule>} />
			<Route path="/auditoria" element={<ProtectedModule permission="audit:read"><AuditoriaView /></ProtectedModule>} />
			<Route path="*" element={<ModulePlaceholder />} />
		</Routes>
	);
}

function ProtectedModule({ permission, children }: { permission: string; children: React.ReactNode }) {
	const { hasPermission } = useAuth();
	if (!hasPermission(permission)) {
		return <section className="module-placeholder"><div className="page-eyebrow">ACCESO RESTRINGIDO</div><h1>Permiso insuficiente</h1><p className="page-lede">Tu rol no permite consultar este módulo.</p></section>;
	}
	return children;
}