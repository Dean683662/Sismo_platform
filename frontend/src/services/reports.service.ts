import { apiDownload, apiRequest } from "./api.client";

export type ReportType = "events" | "models" | "sources" | "alerts" | "quality";
export interface ReportRun {
	id: string;
	report_type: ReportType;
	filters: Record<string, string | number | null>;
	row_count: number;
	requested_by: string | null;
	created_at: string;
}

export interface ReportFilters {
	report_type: ReportType;
	start_date?: string;
	end_date?: string;
	min_magnitude?: number;
	max_magnitude?: number;
	source_key?: string;
	limit: number;
}

export function listReports(): Promise<ReportRun[]> {
	return apiRequest<ReportRun[]>("/reports?limit=100");
}

export function createReport(filters: ReportFilters): Promise<ReportRun> {
	return apiRequest<ReportRun>("/reports", { method: "POST", body: JSON.stringify(filters) });
}

export async function downloadReport(report: ReportRun, format: "csv" | "json" | "xlsx" | "pdf"): Promise<void> {
	const blob = await apiDownload(`/reports/${report.id}/export?format=${format}`);
	const url = URL.createObjectURL(blob);
	const link = document.createElement("a");
	link.href = url;
	link.download = `reporte-${report.report_type}-${report.id}.${format}`;
	document.body.append(link);
	link.click();
	link.remove();
	window.setTimeout(() => URL.revokeObjectURL(url), 0);
}
