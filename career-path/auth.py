from datetime import datetime, timedelta
from typing import Optional
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, validator, ConfigDict
from sqlalchemy.orm import Session
from decouple import config
import re

from database import get_db, User

SECRET_KEY = config("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = config("ACCESS_TOKEN_EXPIRE_MINUTES", default=30, cast=int)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r'[A-Za-z]', v):
            raise ValueError('Password must contain at least one letter')
        if not re.search(r'[0-9]', v):
            raise ValueError('Password must contain at least one number')
        return v
    
    @validator('full_name')
    def validate_full_name(cls, v):
        if v and len(v.strip()) < 2:
            raise ValueError('Full name must be at least 2 characters long')
        return v.strip() if v else None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    is_active: bool
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class SavedCourseCreate(BaseModel):
    course_id: str
    course_title: str
    course_url: Optional[str] = None

class SavedCourseResponse(BaseModel):
    id: int
    course_id: str
    course_title: str
    course_url: Optional[str]
    saved_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class CareerChoiceCreate(BaseModel):
    career_path: str
    assessment_result: Optional[str] = None
    confidence_score: Optional[str] = None

class CareerChoiceResponse(BaseModel):
    id: int
    career_path: str
    assessment_result: Optional[str]
    confidence_score: Optional[str]
    selected_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class UserProfileCreate(BaseModel):
    preferred_skills: Optional[str] = None
    difficulty_preference: str = "beginner"
    time_availability: str = "moderate"
    budget_preference: str = "mixed"
    learning_style: str = "visual"
    career_goals: Optional[str] = None

class UserProfileResponse(BaseModel):
    id: int
    preferred_skills: Optional[str]
    difficulty_preference: str
    time_availability: str
    budget_preference: str
    learning_style: str
    career_goals: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class AssessmentResultResponse(BaseModel):
    id: int
    recommended_career: str
    confidence_score: Optional[str]
    assessment_data: Optional[str]
    match_percentage: Optional[str]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class UserLearningPathResponse(BaseModel):
    id: int
    career_path: str
    skill_level: str
    path_data: Optional[str]
    total_checkpoints: Optional[int]
    estimated_duration: Optional[str]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class RecommendationResultResponse(BaseModel):
    id: int
    recommendation_type: str
    query_data: Optional[str]
    recommendation_data: str
    total_recommendations: Optional[int]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials) -> str:
    """Verify JWT token and return user_id"""
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return int(user_id)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Get user by email"""
    return db.query(User).filter(User.email == email).first()

def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """Get user by ID"""
    return db.query(User).filter(User.id == user_id).first()

def create_user(db: Session, user: UserCreate) -> User:
    """Create a new user"""
    hashed_password = get_password_hash(user.password)
    db_user = User(
        email=user.email,
        hashed_password=hashed_password,
        full_name=user.full_name
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """Authenticate user credentials"""
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user"""
    user_id = verify_token(credentials)
    user = get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return user
