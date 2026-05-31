from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
import uuid

class UserRegister(BaseModel):
    full_name: str
    email: EmailStr
    phone: str
    member_id: Optional[str] = None
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: uuid.UUID
    full_name: str
    email: str
    phone: str
    member_id: Optional[str]
    role: str
    is_approved: bool
    photo_url: Optional[str]
    created_at: datetime

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

class TeamCreate(BaseModel):
    name: str
    description: Optional[str] = None

class TeamUpdate(BaseModel):
    name: str
    description: Optional[str] = None

class TeamResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str]
    candidate_count: int
    created_at: datetime

class PositionCreate(BaseModel):
    title: str
    display_name: str
    is_combined: bool = False
    team_id: uuid.UUID

class PositionUpdate(BaseModel):
    title: str
    display_name: str
    is_combined: bool = False

class PositionResponse(BaseModel):
    id: uuid.UUID
    title: str
    display_name: str
    is_combined: bool
    team_id: uuid.UUID
    team_name: Optional[str]
    candidate_count: int

class CandidateResponse(BaseModel):
    id: uuid.UUID
    team_id: uuid.UUID
    position_id: uuid.UUID
    full_name: str
    profile_picture: Optional[str]
    party_affiliation: Optional[str]
    previous_leadership: Optional[str]
    letter_of_intent: Optional[str]
    bio: Optional[str]
    running_mate_name: Optional[str]
    running_mate_picture: Optional[str]
    running_mate_party: Optional[str]
    running_mate_previous_leadership: Optional[str]
    running_mate_letter_of_intent: Optional[str]
    running_mate_bio: Optional[str]
    team_name: str
    position_name: str
    position_title: str
    is_combined: bool
    created_at: datetime

class VoteCreate(BaseModel):
    candidate_id: uuid.UUID
    position_id: uuid.UUID
    team_id: uuid.UUID

class SupportRequestCreate(BaseModel):
    subject: str
    message: str

class VerificationLogCreate(BaseModel):
    result: str
    distance: Optional[float] = None
    selfie_image_url: Optional[str] = None
    voter_id: Optional[uuid.UUID] = None

class SupportRequestResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    subject: str
    message: str
    status: str
    created_at: datetime
    updated_at: datetime
    user_email: Optional[str] = None
    user_full_name: Optional[str] = None

class AccessRequestCreate(BaseModel):
    message: str
    voter_id: Optional[uuid.UUID] = None
    voter_name: Optional[str] = None
    voter_email: Optional[str] = None

class AccessRequestUpdate(BaseModel):
    status: str
    reason: Optional[str] = None

class AccessRequestResponse(BaseModel):
    id: uuid.UUID
    voter_id: uuid.UUID
    voter_name: str
    voter_email: str
    message: str
    status: str
    denial_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class AdminContactInfo(BaseModel):
    admin_phone: Optional[str] = ""
    admin_whatsapp: Optional[str] = ""
    admin_hours: Optional[str] = ""

class AdminContactUpdate(BaseModel):
    admin_phone: Optional[str] = None
    admin_whatsapp: Optional[str] = None
    admin_hours: Optional[str] = None

class ElectionSettingsSchema(BaseModel):
    election_name: str
    is_active: bool
    voting_start: Optional[datetime]
    voting_end: Optional[datetime]
    allow_registration: bool

class StatsResponse(BaseModel):
    total_members: int
    approved_members: int
    total_votes: int
    pending_approvals: int
    turnout: float

class ForgotPassword(BaseModel):
    email: EmailStr

class ResetPassword(BaseModel):
    token: str
    password: str


class AdminCreateMember(BaseModel):
    full_name: str
    email: EmailStr
    phone: str
    member_id: Optional[str] = None
    password: Optional[str] = None


class AdminUpdateMember(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    member_id: Optional[str] = None
    is_approved: Optional[bool] = None
    photo_url: Optional[str] = None
