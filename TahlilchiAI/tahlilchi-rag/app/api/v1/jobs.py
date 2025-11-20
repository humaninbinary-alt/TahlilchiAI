"""API endpoints for job status tracking."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.auth import get_current_user
from app.models.job import Job
from app.models.user import User
from app.schemas.job import JobResult, JobStatus

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}/status", response_model=JobStatus)
async def get_job_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JobStatus:
    """
    Get current job status and progress.

    Args:
        job_id: Job identifier (Celery task ID)
        db: Database session

    Returns:
        Current job status

    Raises:
        HTTPException: 404 if job not found
    """
    query = select(Job).where(
        Job.id == job_id,
        Job.tenant_id == current_user.tenant_id,
    )
    result = await db.execute(query)
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    return JobStatus.model_validate(job)


@router.get("/{job_id}/result", response_model=JobResult)
async def get_job_result(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JobResult:
    """
    Get job result when completed.

    Args:
        job_id: Job identifier (Celery task ID)
        db: Database session

    Returns:
        Job result with output data

    Raises:
        HTTPException: 404 if job not found, 425 if still processing
    """
    query = select(Job).where(
        Job.id == job_id,
        Job.tenant_id == current_user.tenant_id,
    )
    result = await db.execute(query)
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    if job.status in ["pending", "processing"]:
        raise HTTPException(
            status_code=425,
            detail=f"Job still {job.status}. Current progress: {job.progress}%",
        )

    return JobResult.model_validate(job)
