import { apiRequest } from "./api.client";
import type { AppUser, RoleName } from "../types/user.types";

interface UserResponse {
	id: string;
	full_name: string;
	email: string;
	is_active: boolean;
	roles: RoleName[];
	permissions: string[];
}

interface SessionResponse {
	user: UserResponse;
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

export async function login(email: string, password: string): Promise<AppUser> {
	const response = await apiRequest<SessionResponse>("/auth/login", {
		method: "POST",
		body: JSON.stringify({ email, password }),
	});
	return mapUser(response.user);
}

export async function getCurrentUser(): Promise<AppUser> {
	const response = await apiRequest<SessionResponse>("/auth/me");
	return mapUser(response.user);
}

export function logout(): Promise<void> {
	return apiRequest<void>("/auth/logout", { method: "POST" });
}