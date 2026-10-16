import { useEffect, useState } from "react";
import {
	Activity,
	Bell,
	ClipboardList,
	Database,
	Gauge,
	Layers3,
	MapPinned,
	Microscope,
	LogOut,
	ScrollText,
	Settings2,
	ShieldCheck,
	UsersRound,
	Waves,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { NavLink, useLocation } from "react-router-dom";

import { useAuth } from "../hooks/useAuth";
import Router from "./Router";
import { checkApiHealth } from "../services/api.client";

type NavItem = { to: string; label: string; icon: LucideIcon; permission?: string };
type NavGroup = { label: string; links: NavItem[] };

const groups: NavGroup[] = [
	{
		label: "Operación",
		links: [
			{ to: "/", label: "Resumen", icon: Gauge },
			{ to: "/eventos", label: "Eventos sísmicos", icon: Activity, permission: "events:read" },
			{ to: "/mapa", label: "Mapa sísmico", icon: MapPinned, permission: "events:read" },
		],
	},
	{
		label: "Análisis",
		links: [
			{ to: "/analisis", label: "Análisis estadístico", icon: Layers3, permission: "analytics:read" },
			{ to: "/modelos", label: "Modelos ML", icon: Microscope, permission: "models:read" },
			{ to: "/estimaciones", label: "Estimaciones", icon: Waves, permission: "estimates:read" },
			{ to: "/reportes", label: "Reportes", icon: ClipboardList, permission: "reports:read" },
		],
	},
	{
		label: "Plataforma",
		links: [
			{ to: "/alertas", label: "Centro de alertas", icon: Bell, permission: "alerts:read" },
			{ to: "/fuentes", label: "Fuentes de datos", icon: Database, permission: "sources:read" },
			{ to: "/usuarios", label: "Usuarios y roles", icon: UsersRound, permission: "users:read" },
			{ to: "/auditoria", label: "Auditoría", icon: ScrollText, permission: "audit:read" },
			{ to: "/configuracion", label: "Configuración", icon: Settings2, permission: "settings:manage" },
		],
	},
];

type ApiStatus = "checking" | "online" | "offline";

export default function Layout() {
	const [apiStatus, setApiStatus] = useState<ApiStatus>("checking");
	const [logoutError, setLogoutError] = useState(false);
	const location = useLocation();
	const { user, logout, hasPermission } = useAuth();
	const currentLink = groups.flatMap((group) => group.links).find((link) => link.to === location.pathname);
	const visibleGroups = groups
		.map((group) => ({ ...group, links: group.links.filter((link) => !link.permission || hasPermission(link.permission)) }))
		.filter((group) => group.links.length > 0);
	const initials = user?.fullName.split(/\s+/).slice(0, 2).map((part) => part[0]).join("").toUpperCase() ?? "U";

	useEffect(() => {
		const controller = new AbortController();
		checkApiHealth(controller.signal)
			.then((isOnline) => setApiStatus(isOnline ? "online" : "offline"))
			.catch(() => setApiStatus("offline"));
		return () => controller.abort();
	}, []);

	return (
		<div className="app-shell">
			<aside className="sidebar">
				<NavLink to="/" className="brand" aria-label="Sismo, ir al resumen">
					<span className="brand-mark"><Activity size={20} strokeWidth={2.4} /></span>
					<span className="brand-name">sismo<span>.</span><small>OBSERVATORIO</small></span>
				</NavLink>

				<div className="workspace-label">PLATAFORMA DE MONITOREO</div>
				<nav className="primary-nav" aria-label="Navegación principal">
					{visibleGroups.map((group) => (
						<section className="nav-group" key={group.label}>
							<h2>{group.label}</h2>
							{group.links.map(({ to, label, icon: Icon }) => (
								<NavLink key={to} to={to} end={to === "/"} className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}>
									<Icon size={17} strokeWidth={1.8} aria-hidden="true" />
									<span>{label}</span>
								</NavLink>
							))}
						</section>
					))}
				</nav>

				<div className="sidebar-footer">
					<div className="sidebar-footer-icon"><ShieldCheck size={17} /></div>
					<div><strong>Sesión protegida</strong><span>{user?.roles.map((role) => role.replaceAll("_", " ")).join(", ")}</span></div>
					<span className="status-dot connection-online-dot" aria-label="Autenticado" />
				</div>
			</aside>

			<div className="main-column">
				<header className="topbar">
					<div className="breadcrumb"><span>Plataforma</span><span className="breadcrumb-divider">/</span><strong>{currentLink?.label ?? "Módulo"}</strong></div>
					<div className="topbar-right">
						<div className={`connection-status connection-${apiStatus}`}>
							<span className="status-dot" />
							<span>{apiStatus === "online" ? "API conectada" : apiStatus === "checking" ? "Verificando API" : "API sin conexión"}</span>
						</div>
						<div className="environment-tag">DESARROLLO</div>
						<div className="user-chip"><span className="user-avatar">{initials}</span><span>{user?.fullName}</span><button aria-label="Cerrar sesión" className="logout-button" onClick={() => void logout().then(() => setLogoutError(false)).catch(() => setLogoutError(true))} title="Cerrar sesión" type="button"><LogOut size={15} /></button></div>
					</div>
				</header>
				{logoutError && <div className="logout-error" role="alert">No se pudo cerrar la sesión. Intenta nuevamente.</div>}
				<main className="page-content"><Router /></main>
				<footer className="app-footer"><span>SISMO · Plataforma de monitoreo sísmico</span><span>Control de acceso · Fase 2</span></footer>
			</div>
		</div>
	);
}