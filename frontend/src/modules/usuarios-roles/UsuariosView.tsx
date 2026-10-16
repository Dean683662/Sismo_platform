import { useEffect, useState, type FormEvent } from "react";
import { Plus, ShieldCheck, ShieldOff, UsersRound } from "lucide-react";

import Button from "../../components/Button";
import Modal from "../../components/Modal";
import SkeletonLoader from "../../components/SkeletonLoader";
import { createUser, listRoles, listUsers, updateUser } from "../../services/admin.service";
import type { AppUser, RoleDefinition, RoleName } from "../../types/user.types";

export default function UsuariosView() {
	const [users, setUsers] = useState<AppUser[]>([]);
	const [roles, setRoles] = useState<RoleDefinition[]>([]);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState("");
	const [formError, setFormError] = useState("");
	const [isCreateOpen, setCreateOpen] = useState(false);
	const [refreshKey, setRefreshKey] = useState(0);

	useEffect(() => {
		let active = true;
		Promise.all([listUsers(), listRoles()])
			.then(([userList, roleList]) => {
				if (!active) return;
				setUsers(userList);
				setRoles(roleList);
			})
			.catch(() => { if (active) setError("No se pudo cargar la administración de usuarios."); })
			.finally(() => { if (active) setLoading(false); });
		return () => { active = false; };
	}, [refreshKey]);

	async function handleCreate(event: FormEvent<HTMLFormElement>) {
		event.preventDefault();
		const form = new FormData(event.currentTarget);
		const assignedRoles = form.getAll("roles").map(String) as RoleName[];
		try {
			await createUser({
				full_name: String(form.get("full_name")),
				email: String(form.get("email")),
				password: String(form.get("password")),
				roles: assignedRoles,
			});
			setCreateOpen(false);
			setFormError("");
			setError("");
			setLoading(true);
			setRefreshKey((value) => value + 1);
		} catch (requestError) {
			setFormError(requestError instanceof Error ? requestError.message : "No se pudo crear el usuario.");
		}
	}

	async function toggleUser(user: AppUser) {
		try {
			await updateUser(user.id, { is_active: !user.isActive });
			setError("");
			setLoading(true);
			setRefreshKey((value) => value + 1);
		} catch (requestError) {
			setError(requestError instanceof Error ? requestError.message : "No se pudo actualizar el usuario.");
		}
	}

	return (
		<div className="admin-page">
			<section className="admin-heading">
				<div><div className="page-eyebrow">PLATAFORMA <span>·</span> CONTROL DE ACCESO</div><h1>Usuarios y roles</h1><p className="page-lede">Cuentas internas, estado de acceso y permisos asignados.</p></div>
				<Button icon={<Plus size={16} />} onClick={() => setCreateOpen(true)}>Crear usuario</Button>
			</section>
			{error && <div className="admin-error" role="alert">{error}</div>}
			<section className="content-panel admin-table-panel">
				<div className="panel-heading"><div><div className="panel-kicker">DIRECTORIO</div><h2>Usuarios registrados</h2></div><span className="table-count"><UsersRound size={14} /> {users.length}</span></div>
				{loading ? <div className="admin-loading"><SkeletonLoader lines={5} /></div> : users.length === 0 ? <p className="admin-empty">No hay usuarios registrados.</p> : (
					<div className="table-scroll"><table className="admin-table"><thead><tr><th>Usuario</th><th>Roles</th><th>Estado</th><th><span className="sr-only">Acciones</span></th></tr></thead><tbody>
						{users.map((user) => <tr key={user.id}>
							<td><strong>{user.fullName}</strong><span>{user.email}</span></td>
							<td><div className="role-tags">{user.roles.map((role) => <span className="role-tag" key={role}>{role.replaceAll("_", " ")}</span>)}</div></td>
							<td><span className={`account-state ${user.isActive ? "account-active" : "account-inactive"}`}><i />{user.isActive ? "Activo" : "Desactivado"}</span></td>
							<td className="table-action"><Button aria-label={`${user.isActive ? "Desactivar" : "Activar"} a ${user.fullName}`} disabled={loading} icon={user.isActive ? <ShieldOff size={15} /> : <ShieldCheck size={15} />} onClick={() => void toggleUser(user)} variant="quiet">{user.isActive ? "Desactivar" : "Activar"}</Button></td>
						</tr>)}
					</tbody></table></div>
				)}
			</section>
			<section className="content-panel roles-panel">
				<div className="panel-heading"><div><div className="panel-kicker">MÍNIMO PRIVILEGIO</div><h2>Roles disponibles</h2></div><ShieldCheck size={17} className="roles-heading-icon" /></div>
				<div className="roles-table-wrap"><table className="admin-table roles-table"><thead><tr><th>Rol</th><th>Responsabilidad</th><th>Permisos</th></tr></thead><tbody>
					{roles.map((role) => <tr key={role.name}><td><strong>{role.name.replaceAll("_", " ")}</strong></td><td>{role.description}</td><td>{role.permissions.length}</td></tr>)}
				</tbody></table></div>
			</section>
			<Modal open={isCreateOpen} onClose={() => setCreateOpen(false)} title="Crear usuario">
				<form className="user-form" onSubmit={(event) => void handleCreate(event)}>
					{formError && <p className="form-error" role="alert">{formError}</p>}
					<label>Nombre completo<input autoComplete="name" maxLength={160} minLength={2} name="full_name" required /></label>
					<label>Correo electrónico<input autoComplete="email" name="email" required type="email" /></label>
					<label>Contraseña temporal<input autoComplete="new-password" minLength={12} name="password" required type="password" /><span>Mínimo 12 caracteres. Debe compartirse por un canal seguro.</span></label>
					<fieldset><legend>Roles asignados</legend><div className="role-options">{roles.map((role) => <label key={role.name}><input name="roles" type="checkbox" value={role.name} /><span>{role.name.replaceAll("_", " ")}</span></label>)}</div></fieldset>
					<div className="user-form-actions"><Button onClick={() => setCreateOpen(false)} variant="secondary">Cancelar</Button><Button type="submit">Crear cuenta</Button></div>
				</form>
			</Modal>
		</div>
	);
}