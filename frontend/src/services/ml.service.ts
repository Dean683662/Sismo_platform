import { apiRequest } from "./api.client";
import type { DatasetVersion, Experiment } from "../types/ml.types";

export function listDatasets(): Promise<DatasetVersion[]> {
	return apiRequest<DatasetVersion[]>("/datasets");
}

export function createDataset(name: string): Promise<DatasetVersion> {
	return apiRequest<DatasetVersion>("/datasets", { method: "POST", body: JSON.stringify({ name }) });
}

export function listExperiments(): Promise<Experiment[]> {
	return apiRequest<Experiment[]>("/ml/experiments");
}

export function createExperiment(
	name: string,
	datasetId: string,
	taskType: "regression" | "classification",
): Promise<Experiment> {
	return apiRequest<Experiment>("/ml/experiments", {
		method: "POST",
		body: JSON.stringify({ name, dataset_id: datasetId, test_fraction: 0.2, task_type: taskType }),
	});
}