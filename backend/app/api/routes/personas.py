from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.models import AgentPersona, User
from app.schemas.persona import (
    AgentPersonaCreateRequest,
    AgentPersonaResponse,
    AgentPersonaUpdateRequest,
)

router = APIRouter()


@router.get("", response_model=list[AgentPersonaResponse])
def list_personas(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[AgentPersonaResponse]:
    personas = (
        db.query(AgentPersona)
        .filter(AgentPersona.user_id == current_user.id)
        .order_by(AgentPersona.created_at.asc())
        .all()
    )
    return [
        AgentPersonaResponse(
            id=p.id,
            user_id=p.user_id,
            name=p.name,
            role_description=p.role_description,
            system_prompt=p.system_prompt,
            model=p.model,
            avatar=p.avatar,
            created_at=p.created_at,
        )
        for p in personas
    ]


@router.post("", response_model=AgentPersonaResponse, status_code=status.HTTP_201_CREATED)
def create_persona(
    req: AgentPersonaCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AgentPersonaResponse:
    persona = AgentPersona(
        user_id=current_user.id,
        name=req.name.strip(),
        role_description=req.role_description.strip(),
        system_prompt=req.system_prompt.strip(),
        model=req.model.strip(),
        avatar=req.avatar.strip() or "🤖",
    )
    db.add(persona)
    db.commit()
    db.refresh(persona)
    return AgentPersonaResponse(
        id=persona.id,
        user_id=persona.user_id,
        name=persona.name,
        role_description=persona.role_description,
        system_prompt=persona.system_prompt,
        model=persona.model,
        avatar=persona.avatar,
        created_at=persona.created_at,
    )


@router.put("/{persona_id}", response_model=AgentPersonaResponse)
def update_persona(
    persona_id: int,
    req: AgentPersonaUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AgentPersonaResponse:
    persona = (
        db.query(AgentPersona)
        .filter(AgentPersona.id == persona_id, AgentPersona.user_id == current_user.id)
        .first()
    )
    if not persona:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent persona not found",
        )

    if req.name is not None:
        persona.name = req.name.strip()
    if req.role_description is not None:
        persona.role_description = req.role_description.strip()
    if req.system_prompt is not None:
        persona.system_prompt = req.system_prompt.strip()
    if req.model is not None:
        persona.model = req.model.strip()
    if req.avatar is not None:
        persona.avatar = req.avatar.strip() or "🤖"

    db.commit()
    db.refresh(persona)
    return AgentPersonaResponse(
        id=persona.id,
        user_id=persona.user_id,
        name=persona.name,
        role_description=persona.role_description,
        system_prompt=persona.system_prompt,
        model=persona.model,
        avatar=persona.avatar,
        created_at=persona.created_at,
    )


@router.delete("/{persona_id}", response_model=dict[str, bool])
def delete_persona(
    persona_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    persona = (
        db.query(AgentPersona)
        .filter(AgentPersona.id == persona_id, AgentPersona.user_id == current_user.id)
        .first()
    )
    if not persona:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent persona not found",
        )

    db.delete(persona)
    db.commit()
    return {"deleted": True}
