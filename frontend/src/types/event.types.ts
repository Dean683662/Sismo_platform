export interface SeismicEvent {
	id: string;
	external_id: string;
	source_key: string;
	occurred_at: string;
	latitude: number;
	longitude: number;
	magnitude: number;
	magnitude_type: string | null;
	depth_km: number;
	place: string;
	source_url: string | null;
	received_at: string;
	review_status: string;
}

export interface EventPage {
	items: SeismicEvent[];
	total: number;
	limit: number;
	offset: number;
}

export interface EventFilters {
	start_date?: string;
	end_date?: string;
	min_magnitude?: string;
	max_magnitude?: string;
	source_key?: string;
}

export interface IngestionRun {
	id: string;
	started_at: string;
	finished_at: string | null;
	status: "running" | "succeeded" | "failed";
	records_seen: number;
	records_inserted: number;
	records_updated: number;
	records_duplicated: number;
	records_skipped: number;
	error_summary: string | null;
}

export interface DataSource {
	id: string;
	provider_key: string;
	name: string;
	organization: string;
	base_url: string;
	source_type: string;
	is_verified: boolean;
	status: string;
	last_sync_at: string | null;
	last_success_at: string | null;
	last_run: IngestionRun | null;
}