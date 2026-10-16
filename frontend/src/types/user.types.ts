export type RoleName = "administrator" | "analyst" | "alert_operator" | "auditor" | "read_only";

export interface AppUser {
	id: string;
	fullName: string;
	email: string;
	isActive: boolean;
	roles: RoleName[];
	permissions: string[];
}

export interface RoleDefinition {
	name: RoleName;
	description: string;
	permissions: string[];
}

export interface AuditEntry {
	id: string;
	actor_id: string | null;
	action: string;
	entity_type: string;
	entity_id: string | null;
	before_json: Record<string, unknown> | null;
	after_json: Record<string, unknown> | null;
	occurred_at: string;
}