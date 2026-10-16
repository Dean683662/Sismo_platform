const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "";

export class ApiError extends Error {
	constructor(message: string, readonly status: number) {
		super(message);
	}
}

function csrfToken(): string {
	const match = document.cookie.match(/(?:^|; )sismo_csrf=([^;]*)/);
	return match ? decodeURIComponent(match[1]) : "";
}

export async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
	const method = (init.method ?? "GET").toUpperCase();
	const headers = new Headers(init.headers);
	if (init.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
	if (!new Set(["GET", "HEAD", "OPTIONS"]).has(method)) headers.set("X-CSRF-Token", csrfToken());

	const response = await fetch(`${apiBaseUrl}/api/v1${path}`, {
		...init,
		method,
		headers,
		credentials: "include",
	});
	if (!response.ok) {
		let message = "No se pudo completar la solicitud.";
		try {
			const body = await response.json();
			if (typeof body.detail === "string") message = body.detail;
		} catch {
			// Keep the generic error when the server does not return JSON.
		}
		throw new ApiError(message, response.status);
	}
	if (response.status === 204) return undefined as T;
	return response.json() as Promise<T>;
}

export async function checkApiHealth(signal?: AbortSignal): Promise<boolean> {
	const response = await fetch(`${apiBaseUrl}/health`, { signal });
	return response.ok;
}