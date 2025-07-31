from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from datetime import datetime
from decouple import config
import os

DATABASE_URL = config("DATABASE_URL", default="sqlite:///./career_path.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    saved_courses = relationship("SavedCourse", back_populates="user")
    career_choice = relationship("UserCareerChoice", back_populates="user", uselist=False)
    user_profile = relationship("UserProfile", back_populates="user", uselist=False)
    assessment_results = relationship("AssessmentResult", back_populates="user")
    learning_paths = relationship("UserLearningPath", back_populates="user")
    recommendation_results = relationship("RecommendationResult", back_populates="user")

class SavedCourse(Base):
    __tablename__ = "saved_courses"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    course_id = Column(String(255), nullable=False)
    course_title = Column(String(500), nullable=False)
    course_url = Column(Text, nullable=True)
    saved_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship with user
    user = relationship("User", back_populates="saved_courses")

class UserCareerChoice(Base):
    __tablename__ = "user_career_choices"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    career_path = Column(String(255), nullable=False)
    assessment_result = Column(Text, nullable=True)
    confidence_score = Column(String(50), nullable=True)
    selected_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship with user
    user = relationship("User", back_populates="career_choice")

class UserProfile(Base):
    __tablename__ = "user_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    preferred_skills = Column(Text, nullable=True)
    difficulty_preference = Column(String(50), default="beginner")
    time_availability = Column(String(50), default="moderate")
    budget_preference = Column(String(50), default="mixed")
    learning_style = Column(String(50), default="visual")
    career_goals = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship with user
    user = relationship("User", back_populates="user_profile")

class AssessmentResult(Base):
    __tablename__ = "assessment_results"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    recommended_career = Column(String(255), nullable=False)
    confidence_score = Column(String(50), nullable=True)
    assessment_data = Column(Text, nullable=True)
    match_percentage = Column(String(10), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship with user
    user = relationship("User", back_populates="assessment_results")

class UserLearningPath(Base):
    __tablename__ = "user_learning_paths"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    career_path = Column(String(255), nullable=False)
    skill_level = Column(String(50), nullable=False)
    path_data = Column(Text, nullable=True)
    total_checkpoints = Column(Integer, nullable=True)
    estimated_duration = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship with user
    user = relationship("User", back_populates="learning_paths")

class RecommendationResult(Base):
    __tablename__ = "recommendation_results"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    recommendation_type = Column(String(50), nullable=False)  # 'personalized', 'skill_based', 'trending', 'career_specific'
    query_data = Column(Text, nullable=True)  # Store the request parameters
    recommendation_data = Column(Text, nullable=False)  # Store the full recommendation results as JSON
    total_recommendations = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship with user
    user = relationship("User", back_populates="recommendation_results")

def create_tables():
    """Create all tables"""
    Base.metadata.create_all(bind=engine)

def get_db() -> Session:
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database on startup"""
    create_tables()
    print("✅ Database initialized successfully")
