import { apiRequest } from "./api.client";

export interface AlertRule {
	id: string;
	name: string;
	is_enabled: boolean;
	min_magnitude: number;
	min_depth_km: number | null;
	region_bounds: Record<string, number> | null;
	source_ids: string[];
	channel: "in_app" | "webhook";
	requires_approval: boolean;
	template: string;
	created_at: string;
	updated_at: string;
}

export interface AlertDelivery {
	id: string;
	rule_id: string;
	rule_name: string;
	event_id: string;
	source_name: string;
	source_url: string | null;
	event_magnitude: number;
	event_place: string;
	event_occurred_at: string;
	status: "pending_approval" | "queued" | "delivered" | "rejected" | "failed";
	channel: "in_app" | "webhook";
	message: string;
	is_test: boolean;
	attempt_count: number;
	last_error: string | null;
	created_at: string;
	delivered_at: string | null;
	reviewed_at: string | null;
}

export type AlertRuleInput = Omit<AlertRule, "id" | "created_at" | "updated_at">;

export function listAlertRules(): Promise<AlertRule[]> {
	return apiRequest<AlertRule[]>("/alerts/rules");
}

export function listAlertDeliveries(): Promise<AlertDelivery[]> {
	return apiRequest<AlertDelivery[]>("/alerts/deliveries?limit=200");
}

export function createAlertRule(input: AlertRuleInput): Promise<AlertRule> {
	return apiRequest<AlertRule>("/alerts/rules", { method: "POST", body: JSON.stringify(input) });
}

export function updateAlertRule(id: string, input: Partial<AlertRuleInput>): Promise<AlertRule> {
	return apiRequest<AlertRule>(`/alerts/rules/${id}`, { method: "PATCH", body: JSON.stringify(input) });
}

export function sendTestAlert(ruleId: string): Promise<AlertDelivery> {
	return apiRequest<AlertDelivery>(`/alerts/rules/${ruleId}/test`, { method: "POST", body: JSON.stringify({}) });
}

export function approveAlert(id: string): Promise<AlertDelivery> {
	return apiRequest<AlertDelivery>(`/alerts/deliveries/${id}/approve`, { method: "POST" });
}

export function rejectAlert(id: string): Promise<AlertDelivery> {
	return apiRequest<AlertDelivery>(`/alerts/deliveries/${id}/reject`, { method: "POST" });
}

export function retryAlert(id: string): Promise<AlertDelivery> {
	return apiRequest<AlertDelivery>(`/alerts/deliveries/${id}/retry`, { method: "POST" });
}