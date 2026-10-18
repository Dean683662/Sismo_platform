import { apiRequest } from "./api.client";
import type { DataSource, IngestionRun } from "../types/event.types";

export function listDataSources(): Promise<DataSource[]> {
	return apiRequest<DataSource[]>("/sources");
}

export function syncDataSource(sourceId: string): Promise<IngestionRun & { source_id: string }> {
	return apiRequest<IngestionRun & { source_id: string }>(`/sources/${sourceId}/sync`, { method: "POST" });
}

export function importHistoricalCatalog(sourceId: string): Promise<IngestionRun & { source_id: string }> {
	return apiRequest<IngestionRun & { source_id: string }>(`/sources/${sourceId}/backfill`, { method: "POST" });
}