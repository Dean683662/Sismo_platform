import { apiRequest } from "./api.client";
import type { DashboardSummary, EventFeatureCollection, TimeSeriesResponse } from "../types/analytics.types";

export function getDashboardSummary(): Promise<DashboardSummary> {
	return apiRequest<DashboardSummary>("/dashboard/summary");
}

export function getTimeSeries(startDate: string, endDate: string, groupBy: "day" | "week" = "day"): Promise<TimeSeriesResponse> {
	const params = new URLSearchParams({ start_date: startDate, end_date: endDate, group_by: groupBy });
	return apiRequest<TimeSeriesResponse>(`/analytics/timeseries?${params}`);
}

export function getEventGeoJson(startDate?: string, endDate?: string): Promise<EventFeatureCollection> {
	const params = new URLSearchParams({ limit: "2000" });
	if (startDate) params.set("start_date", startDate);
	if (endDate) params.set("end_date", endDate);
	return apiRequest<EventFeatureCollection>(`/events/geojson?${params}`);
}