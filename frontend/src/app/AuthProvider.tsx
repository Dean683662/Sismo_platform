import { createContext, useEffect, useState, type ReactNode } from "react";

import { ApiError } from "../services/api.client";
import { getCurrentUser, login as signIn, logout as signOut } from "../services/auth.service";
import type { AppUser } from "../types/user.types";

export interface AuthContextValue {
	user: AppUser | null;
	isLoading: boolean;
	login: (email: string, password: string) => Promise<void>;
	logout: () => Promise<void>;
	hasPermission: (permission: string) => boolean;
	hasRole: (role: string) => boolean;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

export default function AuthProvider({ children }: { children: ReactNode }) {
	const [user, setUser] = useState<AppUser | null>(null);
	const [isLoading, setIsLoading] = useState(true);

	useEffect(() => {
		let active = true;
		getCurrentUser()
			.then((currentUser) => {
				if (active) setUser(currentUser);
			})
			.catch((error: unknown) => {
				if (active && !(error instanceof ApiError && error.status === 401)) setUser(null);
			})
			.finally(() => {
				if (active) setIsLoading(false);
			});
		return () => { active = false; };
	}, []);

	async function login(email: string, password: string) {
		setUser(await signIn(email, password));
	}

	async function logout() {
		await signOut();
		setUser(null);
	}

	const value: AuthContextValue = {
		user,
		isLoading,
		login,
		logout,
		hasPermission: (permission) => user?.permissions.includes(permission) ?? false,
		hasRole: (role) => user?.roles.includes(role as AppUser["roles"][number]) ?? false,
	};

	return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}