"""ML model registry endpoints."""

import psycopg
from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_db
from app.schemas.ml import MLModelCreate, MLModelRead
from app.services.ml_registry_service import deploy_model, list_models, register_model
from app.utils.security import require_roles

router = APIRouter(prefix="/models", tags=["models"])


@router.get("", response_model=list[MLModelRead])
def get_models(connection=Depends(get_db), _user=Depends(require_roles("investigator", "administrator"))) -> list[MLModelRead]:
    return [MLModelRead.model_validate(row) for row in list_models(connection)]


@router.post("", response_model=MLModelRead, status_code=201)
def create_model(
    request: MLModelCreate,
    connection=Depends(get_db),
    user=Depends(require_roles("administrator")),
) -> MLModelRead:
    try:
        row = register_model(connection, request, user["user_id"])
        connection.commit()
        return MLModelRead.model_validate(row)
    except psycopg.Error as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{model_id}/deploy", response_model=MLModelRead)
def deploy_model_endpoint(
    model_id: int,
    connection=Depends(get_db),
    user=Depends(require_roles("administrator")),
) -> MLModelRead:
    try:
        row = deploy_model(connection, model_id, user["user_id"])
        connection.commit()
        return MLModelRead.model_validate(row)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except psycopg.Error as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
