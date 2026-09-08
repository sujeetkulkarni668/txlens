"""Policy CRUD endpoints (product spec section 7 / 18).

Auth note: gated behind get_current_user_id, which is currently a
placeholder (see app/api/v1/dependencies.py docstring) — not yet real
authentication. Not build/run-verified in this environment (no
FastAPI/SQLAlchemy/Postgres available here); syntax-checked only.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_current_user_id
from app.db.session import get_db
from app.models.policy import Policy
from app.schemas.policy import PolicyCreate, PolicyResponse, PolicyUpdate

router = APIRouter(prefix="/policies", tags=["policies"])


@router.get("", response_model=list[PolicyResponse])
async def list_policies(
    db: AsyncSession = Depends(get_db), user_id: str = Depends(get_current_user_id)
) -> list[Policy]:
    result = await db.execute(select(Policy).where(Policy.owner_id == user_id))
    return list(result.scalars().all())


@router.post("", response_model=PolicyResponse, status_code=201)
async def create_policy(
    body: PolicyCreate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> Policy:
    policy = Policy(
        owner_id=user_id,
        name=body.name,
        rule_type=body.rule_type.value,
        parameters=body.parameters,
        is_active=body.is_active,
    )
    db.add(policy)
    await db.commit()
    await db.refresh(policy)
    return policy


@router.get("/{policy_id}", response_model=PolicyResponse)
async def get_policy(
    policy_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> Policy:
    policy = await db.get(Policy, policy_id)
    if policy is None or str(policy.owner_id) != str(user_id):
        raise HTTPException(status_code=404, detail="policy not found")
    return policy


@router.put("/{policy_id}", response_model=PolicyResponse)
async def update_policy(
    policy_id: uuid.UUID,
    body: PolicyUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> Policy:
    policy = await db.get(Policy, policy_id)
    if policy is None or str(policy.owner_id) != str(user_id):
        raise HTTPException(status_code=404, detail="policy not found")

    if body.name is not None:
        policy.name = body.name
    if body.rule_type is not None:
        policy.rule_type = body.rule_type.value
    if body.parameters is not None:
        policy.parameters = body.parameters
    if body.is_active is not None:
        policy.is_active = body.is_active

    await db.commit()
    await db.refresh(policy)
    return policy


@router.delete("/{policy_id}", status_code=204)
async def delete_policy(
    policy_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> None:
    policy = await db.get(Policy, policy_id)
    if policy is None or str(policy.owner_id) != str(user_id):
        raise HTTPException(status_code=404, detail="policy not found")
    await db.delete(policy)
    await db.commit()
