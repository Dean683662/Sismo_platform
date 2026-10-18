import { apiRequest } from "./api.client";
import type { DashboardSummary, EventFeatureCollection, TimeSeriesResponse } from "../types/analytics.types";

export function getDashboardSummary(): Promise<DashboardSummary> {
	return apiRequest<DashboardSummary>("/dashboard/summary");
}

export function getTimeSeries(startDate: string, endDate: string, groupBy: "day" | "week" = "day"): Promise<TimeSeriesResponse> {
	const params = new URLSearchParams({ start_date: startDate, end_date: endDate, group_by: groupBy });
	return apiRequest<TimeSeriesResponse>(`/analytics/timeseries?${params}`);
}

export interface GeoJsonFilters {
	startDate?: string;
	endDate?: string;
	minMagnitude?: number;
	maxMagnitude?: number;
	minLatitude?: number;
	maxLatitude?: number;
	minLongitude?: number;
	maxLongitude?: number;
	limit?: number;
}

export function getEventGeoJson(filters: GeoJsonFilters = {}): Promise<EventFeatureCollection> {
	const params = new URLSearchParams({ limit: String(filters.limit ?? 2000) });
	if (filters.startDate) params.set("start_date", filters.startDate);
	if (filters.endDate) params.set("end_date", filters.endDate);
	if (filters.minMagnitude !== undefined) params.set("min_magnitude", String(filters.minMagnitude));
	if (filters.maxMagnitude !== undefined) params.set("max_magnitude", String(filters.maxMagnitude));
	if (filters.minLatitude !== undefined) params.set("min_latitude", String(filters.minLatitude));
	if (filters.maxLatitude !== undefined) params.set("max_latitude", String(filters.maxLatitude));
	if (filters.minLongitude !== undefined) params.set("min_longitude", String(filters.minLongitude));
	if (filters.maxLongitude !== undefined) params.set("max_longitude", String(filters.maxLongitude));
	return apiRequest<EventFeatureCollection>(`/events/geojson?${params}`);
}