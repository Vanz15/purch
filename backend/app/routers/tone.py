"""Tone API — get/set the user's conversation tone preference.

Source: backend.get_user_tone / backend.set_user_tone (db/models.py,
re-exported through the bootstrap layer). VALID_TONES is defined in
llm.tone and surfaced via backend.VALID_TONES.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.deps import get_current_user_id
from app.services import bootstrap as backend

logger = logging.getLogger("purch.tone")

router = APIRouter(prefix="/api/tone", tags=["tone"])


class ToneUpdate(BaseModel):
    tone: str


@router.get("")
async def get_tone(user_id: str = Depends(get_current_user_id)):
    backend.bootstrap()
    backend.ensure_user(user_id)
    return {"tone": backend.get_user_tone(user_id)}


@router.post("")
async def set_tone(body: ToneUpdate, user_id: str = Depends(get_current_user_id)):
    if body.tone not in backend.VALID_TONES:
        raise HTTPException(status_code=422, detail=f"Invalid tone. Must be one of {backend.VALID_TONES}")
    backend.bootstrap()
    backend.ensure_user(user_id)
    backend.set_user_tone(user_id, body.tone)
    return {"ok": True}
