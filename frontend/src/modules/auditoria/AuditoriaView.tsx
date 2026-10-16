import { useEffect, useState } from "react";
import { ScrollText } from "lucide-react";

import SkeletonLoader from "../../components/SkeletonLoader";
import { listAuditLogs } from "../../services/admin.service";
import type { AuditEntry } from "../../types/user.types";

function summarize(value: Record<string, unknown> | null): string {
	if (!value) return "—";
	return Object.entries(value).map(([key, entry]) => `${key}: ${Array.isArray(entry) ? entry.join(", ") : String(entry)}`).join(" · ");
}

export default function AuditoriaView() {
	const [entries, setEntries] = useState<AuditEntry[]>([]);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState("");

	useEffect(() => {
		let active = true;
		listAuditLogs()
			.then((result) => { if (active) setEntries(result); })
			.catch(() => { if (active) setError("No se pudo consultar la bitácora."); })
			.finally(() => { if (active) setLoading(false); });
		return () => { active = false; };
	}, []);

	return (
		<div className="admin-page">
			<section className="admin-heading"><div><div className="page-eyebrow">PLATAFORMA <span>·</span> TRAZABILIDAD</div><h1>Auditoría</h1><p className="page-lede">Registro de autenticación y cambios administrativos. Las credenciales no se almacenan en esta bitácora.</p></div></section>
			{error && <div className="admin-error" role="alert">{error}</div>}
			<section className="content-panel admin-table-panel">
				<div className="panel-heading"><div><div className="panel-kicker">REGISTRO INMUTABLE POR API</div><h2>Actividad reciente</h2></div><span className="table-count"><ScrollText size={14} /> {entries.length}</span></div>
				{loading ? <div className="admin-loading"><SkeletonLoader lines={5} /></div> : entries.length === 0 ? <p className="admin-empty">Todavía no hay acciones registradas.</p> : (
					<div className="table-scroll"><table className="admin-table audit-table"><thead><tr><th>Fecha UTC</th><th>Acción</th><th>Entidad</th><th>Actor</th><th>Cambios</th></tr></thead><tbody>
						{entries.map((entry) => <tr key={entry.id}>
							<td>{new Date(entry.occurred_at).toLocaleString("es-PE", { timeZone: "UTC", dateStyle: "medium", timeStyle: "short" })}</td>
							<td><strong>{entry.action}</strong></td>
							<td>{entry.entity_type}{entry.entity_id ? <span>{entry.entity_id.slice(0, 8)}</span> : null}</td>
							<td>{entry.actor_id ? entry.actor_id.slice(0, 8) : "Sistema"}</td>
							<td><span>{summarize(entry.before_json)}</span>{entry.after_json && <span>{summarize(entry.after_json)}</span>}</td>
						</tr>)}
					</tbody></table></div>
				)}
			</section>
		</div>
	);
}