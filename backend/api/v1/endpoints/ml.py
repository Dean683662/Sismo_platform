"""Train and inspect reproducible experimental ML baselines."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.api.v1.schemas import ExperimentCreateRequest, ExperimentResponse
from backend.core.database import get_db
from backend.core.security import require_csrf, require_permissions
from backend.database.models import Dataset, MLExperiment, User
from backend.ml.training import train_magnitude_baseline, train_magnitude_classification_baseline
import numpy
import pandas
import sklearn


router = APIRouter(prefix="/ml", tags=["machine-learning"])
LIMITATIONS = (
	"Experimento didáctico sobre magnitudes de eventos ya reportados. "
	"No predice terremotos futuros ni constituye una alerta oficial."
)


def _experiment_response(experiment: MLExperiment) -> ExperimentResponse:
	return ExperimentResponse(
		id=str(experiment.id), name=experiment.name, task_type=experiment.task_type,
		algorithm=experiment.algorithm, dataset_id=str(experiment.dataset_id),
		feature_spec=experiment.feature_spec, target_name=experiment.target_name,
		params=experiment.params, metrics=experiment.metrics,
		validation_spec=experiment.validation_spec, status=experiment.status,
		limitations=experiment.limitations, created_at=experiment.created_at,
	)


@router.post("/experiments", response_model=ExperimentResponse, status_code=status.HTTP_201_CREATED)
def create_experiment(
	request: ExperimentCreateRequest,
	db: Session = Depends(get_db),
	_: None = Depends(require_csrf),
	user: User = Depends(require_permissions("models:manage")),
) -> ExperimentResponse:
	try:
		dataset_id = UUID(request.dataset_id)
	except ValueError:
		raise HTTPException(status_code=422, detail="Invalid dataset_id") from None
	dataset = db.get(Dataset, dataset_id)
	if dataset is None:
		raise HTTPException(status_code=404, detail="Dataset not found")
	try:
		if request.task_type == "classification":
			result = train_magnitude_classification_baseline(dataset.records_json, request.test_fraction)
		else:
			result = train_magnitude_baseline(dataset.records_json, request.test_fraction)
	except ValueError as error:
		raise HTTPException(status_code=422, detail=str(error)) from error

	experiment = MLExperiment(
		name=request.name,
		task_type=request.task_type,
		algorithm=result.algorithm,
		dataset_id=dataset.id,
		feature_spec=result.feature_names,
		target_name=result.target_name,
		params={
			"test_fraction": request.test_fraction,
			"random_seed": 42 if request.task_type == "classification" else None,
			"library_versions": {
				"numpy": numpy.__version__,
				"pandas": pandas.__version__,
				"scikit_learn": sklearn.__version__,
			},
		},
		metrics=result.metrics,
		validation_spec={
			"strategy": "chronological_holdout",
			"train_period": list(result.train_period),
			"evaluation_period": list(result.evaluation_period),
			"row_count": result.row_count,
			**result.validation_details,
		},
		status="completed",
		limitations=LIMITATIONS,
		created_by=user.id,
	)
	db.add(experiment)
	db.commit()
	db.refresh(experiment)
	return _experiment_response(experiment)


@router.get("/experiments", response_model=list[ExperimentResponse])
def list_experiments(
	db: Session = Depends(get_db),
	_: User = Depends(require_permissions("models:read")),
) -> list[ExperimentResponse]:
	experiments = db.scalars(select(MLExperiment).order_by(MLExperiment.created_at.desc()).limit(100)).all()
	return [_experiment_response(experiment) for experiment in experiments]


@router.get("/experiments/{experiment_id}", response_model=ExperimentResponse)
def get_experiment(
	experiment_id: UUID,
	db: Session = Depends(get_db),
	_: User = Depends(require_permissions("models:read")),
) -> ExperimentResponse:
	experiment = db.get(MLExperiment, experiment_id)
	if experiment is None:
		raise HTTPException(status_code=404, detail="Experiment not found")
	return _experiment_response(experiment)