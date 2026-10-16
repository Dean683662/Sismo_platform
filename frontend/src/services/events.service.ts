import { apiRequest } from "./api.client";
import type { EventFilters, EventPage } from "../types/event.types";

export function listEvents(filters: EventFilters, limit: number, offset: number): Promise<EventPage> {
	const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
	for (const [key, value] of Object.entries(filters)) {
		if (value !== undefined && value !== "") params.set(key, value);
	}
	return apiRequest<EventPage>(`/events?${params.toString()}`);
}