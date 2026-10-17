export interface DashboardSummary {
	total_events: number;
	events_last_24h: number;
	latest_event_at: string | null;
	active_sources: number;
	total_sources: number;
	last_sync_at: string | null;
}

export interface TimeSeriesPoint {
	period_start: string;
	event_count: number;
}

export interface TimeSeriesResponse {
	items: TimeSeriesPoint[];
	total_events: number;
	period_start: string;
	period_end: string;
	group_by: "day" | "week";
}

export interface EventFeature {
	id: string;
	geometry: { type: "Point"; coordinates: [number, number] };
	properties: {
		magnitude: number;
		depth_km: number;
		occurred_at: string;
		place: string;
		source_key: string;
		source_url: string | null;
	};
}

export interface EventFeatureCollection {
	type: "FeatureCollection";
	features: EventFeature[];
}