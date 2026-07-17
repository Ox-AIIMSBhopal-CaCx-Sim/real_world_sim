"""Username/password register and login (prototype identity only)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services import users as user_store

router = APIRouter()


class AuthRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=4, max_length=128)


class AuthResponse(BaseModel):
    username: str
    message: str


@router.post("/register", response_model=AuthResponse)
def register(body: AuthRequest) -> AuthResponse:
    try:
        username = user_store.register_user(body.username, body.password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return AuthResponse(username=username, message="Account created.")


@router.post("/login", response_model=AuthResponse)
def login(body: AuthRequest) -> AuthResponse:
    try:
        username = user_store.authenticate_user(body.username, body.password)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return AuthResponse(username=username, message="Logged in.")
