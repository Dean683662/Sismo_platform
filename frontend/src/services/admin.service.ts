import { apiRequest } from "./api.client";
import type { AppUser, AuditEntry, RoleDefinition, RoleName } from "../types/user.types";

interface UserResponse {
	id: string;
	full_name: string;
	email: string;
	is_active: boolean;
	roles: RoleName[];
	permissions: string[];
}

function mapUser(user: UserResponse): AppUser {
	return {
		id: user.id,
		fullName: user.full_name,
		email: user.email,
		isActive: user.is_active,
		roles: user.roles,
		permissions: user.permissions,
	};
}

export async function listUsers(): Promise<AppUser[]> {
	const users = await apiRequest<UserResponse[]>("/admin/users");
	return users.map(mapUser);
}

export function listRoles(): Promise<RoleDefinition[]> {
	return apiRequest<RoleDefinition[]>("/admin/roles");
}

export async function createUser(input: {
	full_name: string;
	email: string;
	password: string;
	roles: RoleName[];
}): Promise<AppUser> {
	return mapUser(await apiRequest<UserResponse>("/admin/users", { method: "POST", body: JSON.stringify(input) }));
}

export async function updateUser(
	id: string,
	input: { is_active?: boolean; roles?: RoleName[] },
): Promise<AppUser> {
	return mapUser(await apiRequest<UserResponse>(`/admin/users/${id}`, { method: "PATCH", body: JSON.stringify(input) }));
}

export function listAuditLogs(): Promise<AuditEntry[]> {
	return apiRequest<AuditEntry[]>("/admin/audit-logs?limit=200");
}