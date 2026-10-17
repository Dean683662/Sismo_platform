export interface DatasetVersion {
	id: string;
	name: string;
	version: number;
	query_spec: Record<string, string | number | null>;
	period_start: string | null;
	period_end: string | null;
	row_count: number;
	quality_report: {
		rows_seen: number;
		rows_valid: number;
		rows_removed: number;
		duplicates: number;
		invalid_rows: number;
		missing_by_field: Record<string, number>;
	};
	created_at: string;
}

export interface Experiment {
	id: string;
	name: string;
	task_type: string;
	algorithm: string;
	dataset_id: string;
	feature_spec: string[];
	target_name: string;
	params: Record<string, number | null>;
	metrics: Record<string, number>;
	validation_spec: {
		strategy: string;
		train_period: [string, string];
		evaluation_period: [string, string];
		row_count: number;
	};
	status: string;
	limitations: string;
	created_at: string;
}