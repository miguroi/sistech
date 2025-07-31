from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional, Union, Any
import pandas as pd
import json
import numpy as np
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from career_processor import CareerProcessor
from roadmap_generator import RoadmapGenerator
from assessment_questions import AssessmentGenerator
from course_recommender import CourseRecommender, UserProfile as CourseUserProfile
from database import get_db, init_db, User, SavedCourse, UserCareerChoice, UserProfile, AssessmentResult, UserLearningPath, RecommendationResult
from auth import (
    UserCreate, UserLogin, UserResponse, Token, SavedCourseCreate, SavedCourseResponse,
    CareerChoiceCreate, CareerChoiceResponse, UserProfileCreate, UserProfileResponse,
    AssessmentResultResponse, UserLearningPathResponse, RecommendationResultResponse,
    create_access_token, authenticate_user, create_user, get_user_by_email,
    get_current_user, ACCESS_TOKEN_EXPIRE_MINUTES
)

def convert_numpy_types(obj: Any) -> Any:
    """Convert numpy types to native Python types for JSON serialization"""
    if isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    elif pd.isna(obj):
        return None
    return obj

class AssessmentAnswer(BaseModel):
    question_id: int
    answer: str

class AssessmentRequest(BaseModel):
    answers: List[AssessmentAnswer]
    user_id: str

class ApiResponse(BaseModel):
    status: str
    message: Optional[str] = None

class UserProfileRequest(BaseModel):
    user_id: str
    preferred_skills: List[str]
    difficulty_preference: str = "beginner"
    time_availability: str = "moderate"
    budget_preference: str = "mixed"
    learning_style: str = "visual"
    career_goals: List[str]

class SkillBasedRequest(BaseModel):
    skills: List[str]
    limit: Optional[int] = 20

app = FastAPI(
    title="Career Path API",
    description="API for career assessment and course recommendations",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables for our processors
career_processor = None
roadmap_generator = None
assessment_generator = None
course_recommender = None

@app.on_event("startup")
async def startup_event():
    """Initialize database and processors on startup"""
    # Initialize database first
    init_db()
    
    # Then initialize ML processors
    global career_processor, roadmap_generator, assessment_generator, course_recommender
    
    try:
        # Download required NLTK data
        import nltk
        import ssl
        try:
            _create_unverified_https_context = ssl._create_unverified_context
        except AttributeError:
            pass
        else:
            ssl._create_default_https_context = _create_unverified_https_context
            
        nltk.download('punkt', quiet=True)
        nltk.download('stopwords', quiet=True)
        print("✅ NLTK data downloaded successfully")
        import os
        
        # Get the base directory (career-path folder)
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Define file paths relative to base directory
        career_data_path = os.path.join(base_dir, 'data', 'career_dataset.csv')
        courses_data_path = os.path.join(base_dir, 'data', 'coursera_courses_processed.csv')
        
        # Fallback paths if the above don't work
        if not os.path.exists(courses_data_path):
            courses_data_path = os.path.join(base_dir, '..', 'data', 'csv', 'coursera_courses_processed.csv')
        if not os.path.exists(courses_data_path):
            courses_data_path = '../data/coursera_courses_processed.csv'
        
        print(f"📂 Career data path: {career_data_path}")
        print(f"📂 Courses data path: {courses_data_path}")
        print(f"📂 Career data exists: {os.path.exists(career_data_path)}")
        print(f"📂 Courses data exists: {os.path.exists(courses_data_path)}")
        
        # Initialize processors with data files
        career_processor = CareerProcessor(
            career_data_path,
            courses_data_path
        )
        roadmap_generator = RoadmapGenerator(career_processor)
        assessment_generator = AssessmentGenerator(career_processor)
        
        # Try to initialize course recommender if course data is available
        try:
            course_recommender = CourseRecommender(
                courses_data_path=courses_data_path,
                career_processor=career_processor
            )
            career_processor.course_recommender = course_recommender
            print("✅ Course recommender initialized")
        except Exception as course_error:
            print(f"⚠️  Course recommender not available: {course_error}")
            course_recommender = None
        
        print("✅ API server initialized successfully")
        print("✅ Database initialized successfully")
        
    except Exception as e:
        print(f"❌ Failed to initialize API server: {e}")
        import traceback
        traceback.print_exc()
        print(f"📂 Current working directory: {os.getcwd()}")
        print(f"📂 Files in current directory: {os.listdir('.')}")
        if os.path.exists('data'):
            print(f"📂 Files in data directory: {os.listdir('data')}")
        raise

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "Career Path API is running",
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/careers")
async def get_careers():
   """Get all available careers for dropdown selection"""
   try:
       careers_df = career_processor.career_df
       unique_careers = careers_df['role'].unique()
       
       careers_list = []
       for career in unique_careers:
           career_id = career.lower().replace(' ', '_')
           
           # Use ML-based clustering to automatically discover career categories
           category = career_processor.get_dynamic_career_category(career)
           
           careers_list.append({
               'career_id': career_id,
               'career_name': career,
               'category': category
           })
       
       # Sort by category then by name
       careers_list.sort(key=lambda x: (x['category'], x['career_name']))
       
       return {
           'status': 'success',
           'careers': careers_list,
           'total_careers': len(careers_list)
       }
       
   except Exception as e:
       raise HTTPException(
           status_code=500,
           detail={
               'status': 'error',
               'error_code': 'SERVICE_UNAVAILABLE',
               'message': 'Career data temporarily unavailable',
               'details': str(e)
           }
       )

@app.post("/api/assess-career")
async def assess_career(
    request: AssessmentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
   """Process career assessment and return recommendation"""
   try:
       # Validate minimum number of answers
       if len(request.answers) < 5:
           raise HTTPException(
               status_code=400,
               detail={
                   'status': 'error',
                   'error_code': 'INCOMPLETE_ASSESSMENT',
                   'message': 'Assessment requires at least 5 answered questions',
                   'details': {
                       'questions_answered': len(request.answers),
                       'questions_required': 5
                   }
               }
           )
       
       # Convert to format expected by assessment processor
       user_responses = {
           'answers': [
               {
                   'question_id': answer.question_id,
                   'answer': answer.answer
               }
               for answer in request.answers
           ]
       }
       
       # Process assessment
       result = assessment_generator.process_assessment(user_responses)
       
       if result['status'] == 'error':
           raise HTTPException(status_code=400, detail=result)
       
       # Convert numpy types to native Python types for JSON serialization
       result = convert_numpy_types(result)
       
       # Save assessment result to database for authenticated user
       try:
           assessment_result = AssessmentResult(
               user_id=current_user.id,
               recommended_career=result.get('career_recommendation', {}).get('career_name', ''),
               confidence_score=str(result.get('confidence_score', '')),
               assessment_data=json.dumps(result),
               match_percentage=str(result.get('career_recommendation', {}).get('match_percentage', ''))
           )
           db.add(assessment_result)
           db.commit()
       except Exception as save_error:
           print(f"Warning: Failed to save assessment result: {save_error}")
       
       return result
       
   except HTTPException:
       raise
   except Exception as e:
       raise HTTPException(
           status_code=500,
           detail={
               'status': 'error',
               'error_code': 'ASSESSMENT_FAILED',
               'message': 'Failed to process career assessment',
               'details': str(e)
           }
       )

@app.get("/api/roadmap/{career_id}")
async def get_roadmap(career_id: str):
   """Generate learning roadmap for specified career"""
   try:
       # Convert career_id back to career name
       career_name = career_id.replace('_', ' ').title()
       
       # Check if career exists
       available_careers = career_processor.career_df['role'].unique()
       if career_name not in available_careers:
           # Try to find closest match
           career_matches = [c for c in available_careers if career_id.lower() in c.lower().replace(' ', '_')]
           if career_matches:
               career_name = career_matches[0]
           else:
               raise HTTPException(
                   status_code=404,
                   detail={
                       'status': 'error',
                       'error_code': 'CAREER_NOT_FOUND',
                       'message': f'Career ID "{career_id}" not found',
                       'available_careers': [c.lower().replace(' ', '_') for c in available_careers[:10]]
                   }
               )
       
       # Generate roadmap
       roadmap = roadmap_generator.generate_roadmap(career_name)
       
       # Get career description
       career_data = career_processor.career_df[
           career_processor.career_df['role'] == career_name
       ]
       
       description = ""
       if not career_data.empty:
           # Get description from first relevant answer
           for answer in career_data['answer'].values:
               if len(answer) > 50:  # Get a substantial description
                   description = answer
                   break
       
       return {
           'status': 'success',
           'career_info': {
               'career_id': roadmap.career_id,
               'career_name': roadmap.career_name,
               'description': description,
               'qa_count': len(career_data)
           },
           'roadmap': {
               'total_checkpoints': roadmap.total_checkpoints,
               'estimated_duration': roadmap.estimated_duration,
               'checkpoints': [
                   {
                       'checkpoint_id': cp.checkpoint_id,
                       'title': cp.title,
                       'description': cp.description,
                       'skills_derived': cp.skills_derived,
                       'estimated_time': cp.estimated_time,
                       'is_completed': False,
                       'skills_source': cp.skills_source
                   }
                   for cp in roadmap.checkpoints
               ]
           }
       }
       
   except HTTPException:
       raise
   except Exception as e:
       raise HTTPException(
           status_code=500,
           detail={
               'status': 'error',
               'error_code': 'ROADMAP_GENERATION_FAILED',
               'message': 'Failed to generate roadmap',
               'details': str(e)
           }
       )

@app.get("/api/courses/career/{career_id}")
async def get_courses_by_career(
   career_id: str,
   difficulty: Optional[str] = Query(None, regex="^(beginner|intermediate|advanced)$"),
   limit: int = Query(20, ge=1, le=100),
   offset: int = Query(0, ge=0),
   current_user: User = Depends(get_current_user),
   db: Session = Depends(get_db)
):
   """Get courses filtered by career and optional difficulty"""
   try:
       # Convert career_id to career name
       career_name = career_id.replace('_', ' ').title()
       
       # Get related courses
       related_courses = career_processor.get_related_courses(career_name, top_n=200)
       
       if related_courses.empty:
           return {
               'status': 'success',
               'career_info': {
                   'career_id': career_id,
                   'career_name': career_name
               },
               'courses': [],
               'pagination': {
                   'total_courses': 0,
                   'current_page': 1,
                   'total_pages': 0,
                   'has_next': False
               }
           }
       
       # Apply difficulty filter if specified
       if difficulty:
           difficulty_map = {
               'beginner': 'Beginner',
               'intermediate': 'Intermediate', 
               'advanced': 'Advanced'
           }
           related_courses = related_courses[
               related_courses['difficulty'] == difficulty_map[difficulty]
           ]
       
       # Apply pagination
       total_courses = len(related_courses)
       start_idx = offset
       end_idx = start_idx + limit
       paginated_courses = related_courses.iloc[start_idx:end_idx]
       
       # Format courses for response
       courses_list = []
       for _, course in paginated_courses.iterrows():
           # Parse skills
           skills_list = []
           if pd.notna(course['skills']):
               skills_text = str(course['skills'])
               skills_list = [skill.strip() for skill in skills_text.split() if len(skill.strip()) > 2]
           
           course_data = {
               'course_id': course['course_id'],
               'title': course['title_original'],
               'organization': course['organization'],
               'rating': course['rating'] if pd.notna(course['rating']) else None,
               'review_count': int(course['review_count']) if pd.notna(course['review_count']) else 0,
               'difficulty': course['difficulty'],
               'course_type': course['course_type'],
               'duration': course['duration_readable'],
               'skills': skills_list[:10],  # Limit skills shown
               'url': course['url'],
               'is_free': course['is_free'],
               'relevance_score': round(course['similarity_score'], 3) if 'similarity_score' in course else 0.5
           }
           courses_list.append(convert_numpy_types(course_data))
       
       # Pagination info
       current_page = (offset // limit) + 1
       total_pages = (total_courses + limit - 1) // limit
       has_next = end_idx < total_courses
       
       result = {
           'status': 'success',
           'career_info': {
               'career_id': career_id,
               'career_name': career_name
           },
           'courses': courses_list,
           'pagination': {
               'total_courses': total_courses,
               'current_page': current_page,
               'total_pages': total_pages,
               'has_next': has_next
           }
       }
       
       # Save recommendation result to database
       try:
           query_data = {
               'career_id': career_id,
               'career_name': career_name,
               'difficulty': difficulty,
               'limit': limit,
               'offset': offset
           }
           
           recommendation_result = RecommendationResult(
               user_id=current_user.id,
               recommendation_type='career_specific',
               query_data=json.dumps(query_data),
               recommendation_data=json.dumps(courses_list),
               total_recommendations=len(courses_list)
           )
           db.add(recommendation_result)
           db.commit()
       except Exception as save_error:
           print(f"Warning: Failed to save recommendation result: {save_error}")
       
       return result
       
   except Exception as e:
       raise HTTPException(
           status_code=500,
           detail={
               'status': 'error',
               'error_code': 'COURSE_FETCH_FAILED',
               'message': 'Failed to fetch courses',
               'details': str(e)
           }
       )

@app.get("/api/courses/filter")
async def filter_courses(
   difficulty: Optional[str] = Query(None, regex="^(beginner|intermediate|advanced)$"),
   course_type: Optional[str] = Query(None),
   organization: Optional[str] = Query(None),
   is_free: Optional[bool] = Query(None),
   min_rating: Optional[float] = Query(None, ge=0, le=5),
   sort_by: str = Query("relevance", regex="^(rating|review_count|relevance)$"),
   sort_order: str = Query("desc", regex="^(asc|desc)$"),
   limit: int = Query(20, ge=1, le=100),
   offset: int = Query(0, ge=0)
):
   """Filter and sort courses with various criteria"""
   try:
       courses_df = career_processor.courses_df.copy()
       
       # Apply filters
       if difficulty:
           difficulty_map = {
               'beginner': 'Beginner',
               'intermediate': 'Intermediate',
               'advanced': 'Advanced'
           }
           courses_df = courses_df[courses_df['difficulty'] == difficulty_map[difficulty]]
       
       if course_type:
           courses_df = courses_df[
               courses_df['course_type'].str.lower().str.contains(course_type.lower(), na=False)
           ]
       
       if organization:
           courses_df = courses_df[
               courses_df['organization'].str.lower().str.contains(organization.lower(), na=False)
           ]
       
       if is_free is not None:
           courses_df = courses_df[courses_df['is_free'] == is_free]
       
       if min_rating is not None:
           courses_df = courses_df[
               (courses_df['rating'] >= min_rating) | courses_df['rating'].isna()
           ]
       
       # Apply sorting
       if sort_by in ['rating', 'review_count']:
           ascending = (sort_order == 'asc')
           courses_df = courses_df.sort_values(sort_by, ascending=ascending, na_position='last')
       else:  # relevance - use rating as proxy
           ascending = (sort_order == 'asc')
           courses_df = courses_df.sort_values('rating', ascending=ascending, na_position='last')
       
       # Apply pagination
       total_courses = len(courses_df)
       start_idx = offset
       end_idx = start_idx + limit
       paginated_courses = courses_df.iloc[start_idx:end_idx]
       
       # Format response
       courses_list = []
       for _, course in paginated_courses.iterrows():
           skills_list = []
           if pd.notna(course['skills']):
               skills_text = str(course['skills'])
               skills_list = [skill.strip() for skill in skills_text.split() if len(skill.strip()) > 2]
           
           course_data = {
               'course_id': course['course_id'],
               'title': course['title_original'],
               'organization': course['organization'],
               'rating': course['rating'] if pd.notna(course['rating']) else None,
               'review_count': int(course['review_count']) if pd.notna(course['review_count']) else 0,
               'difficulty': course['difficulty'],
               'course_type': course['course_type'],
               'duration': course['duration_readable'],
               'skills': skills_list[:10],
               'url': course['url'],
               'is_free': course['is_free'],
               'relevance_score': round(course['rating'] / 5, 3) if pd.notna(course['rating']) else 0.5
           }
           courses_list.append(convert_numpy_types(course_data))
       
       # Pagination info
       current_page = (offset // limit) + 1
       total_pages = (total_courses + limit - 1) // limit
       has_next = end_idx < total_courses
       
       return {
           'status': 'success',
           'filters_applied': {
               'difficulty': difficulty,
               'course_type': course_type,
               'organization': organization,
               'is_free': is_free,
               'min_rating': min_rating,
               'sort_by': sort_by,
               'sort_order': sort_order
           },
           'courses': courses_list,
           'pagination': {
               'total_courses': total_courses,
               'current_page': current_page,
               'total_pages': total_pages,
               'has_next': has_next
           }
       }
       
   except Exception as e:
       raise HTTPException(
           status_code=500,
           detail={
               'status': 'error',
               'error_code': 'FILTER_FAILED',
               'message': 'Failed to filter courses',
               'details': str(e)
           }
       )

@app.get("/api/assessment/questions")
async def get_assessment_questions():
   """Get all assessment questions"""
   try:
       questions = assessment_generator.get_questions()
       return {
           'status': 'success',
           'questions': questions,
           'total_questions': len(questions)
       }
   except Exception as e:
       raise HTTPException(
           status_code=500,
           detail={
               'status': 'error',
               'message': 'Failed to fetch assessment questions',
               'details': str(e)
           }
       )

@app.post("/api/courses/personalized")
async def get_personalized_courses(
    request: UserProfileRequest = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
   """Get personalized course recommendations based on user profile"""
   try:
       if not course_recommender:
           raise HTTPException(
               status_code=503,
               detail={
                   'status': 'error',
                   'error_code': 'SERVICE_UNAVAILABLE',
                   'message': 'Course recommendation service not available'
               }
           )
       
       # Get or create user profile
       user_profile_db = db.query(UserProfile).filter(
           UserProfile.user_id == current_user.id
       ).first()
       
       if request and request.user_id:
           # If request provided, update/create profile with new data
           if user_profile_db:
               # Update existing profile
               user_profile_db.preferred_skills = ','.join(request.preferred_skills) if request.preferred_skills else None
               user_profile_db.difficulty_preference = request.difficulty_preference
               user_profile_db.time_availability = request.time_availability
               user_profile_db.budget_preference = request.budget_preference
               user_profile_db.learning_style = request.learning_style
               user_profile_db.career_goals = ','.join(request.career_goals) if request.career_goals else None
               user_profile_db.updated_at = datetime.utcnow()
               db.commit()
           else:
               # Create new profile
               user_profile_db = UserProfile(
                   user_id=current_user.id,
                   preferred_skills=','.join(request.preferred_skills) if request.preferred_skills else None,
                   difficulty_preference=request.difficulty_preference,
                   time_availability=request.time_availability,
                   budget_preference=request.budget_preference,
                   learning_style=request.learning_style,
                   career_goals=','.join(request.career_goals) if request.career_goals else None
               )
               db.add(user_profile_db)
               db.commit()
               db.refresh(user_profile_db)
       
       # If no stored profile exists and no request data, use defaults
       if not user_profile_db:
           user_profile_db = UserProfile(
               user_id=current_user.id,
               preferred_skills=None,
               difficulty_preference="beginner",
               time_availability="moderate",
               budget_preference="mixed",
               learning_style="visual",
               career_goals=None
           )
           db.add(user_profile_db)
           db.commit()
           db.refresh(user_profile_db)
       
       # Create user profile for course recommender
       user_profile = CourseUserProfile(
           user_id=str(current_user.id),
           preferred_skills=user_profile_db.preferred_skills.split(',') if user_profile_db.preferred_skills else [],
           difficulty_preference=user_profile_db.difficulty_preference,
           time_availability=user_profile_db.time_availability,
           budget_preference=user_profile_db.budget_preference,
           learning_style=user_profile_db.learning_style,
           career_goals=user_profile_db.career_goals.split(',') if user_profile_db.career_goals else []
       )
       
       # Get personalized recommendations
       recommendations = course_recommender.get_personalized_recommendations(user_profile, top_n=15)
       
       # Format response
       courses_list = []
       for rec in recommendations:
           course_data = {
               'course_id': rec.course_id,
               'title': rec.title,
               'organization': rec.organization,
               'rating': rec.rating,
               'review_count': rec.review_count,
               'difficulty': rec.difficulty,
               'course_type': rec.course_type,
               'duration': rec.duration,
               'skills': rec.skills,
               'url': rec.url,
               'is_free': rec.is_free,
               'relevance_score': rec.relevance_score,
               'match_reasons': rec.match_reasons
           }
           courses_list.append(convert_numpy_types(course_data))
       
       result = {
           'status': 'success',
           'user_profile': {
               'user_id': current_user.id,
               'career_goals': user_profile_db.career_goals.split(',') if user_profile_db.career_goals else [],
               'difficulty_preference': user_profile_db.difficulty_preference
           },
           'recommendations': courses_list,
           'total_recommendations': len(courses_list)
       }
       
       # Save recommendation result to database
       try:
           query_data = {
               'preferred_skills': user_profile.preferred_skills,
               'difficulty_preference': user_profile.difficulty_preference,
               'career_goals': user_profile.career_goals
           }
           
           recommendation_result = RecommendationResult(
               user_id=current_user.id,
               recommendation_type='personalized',
               query_data=json.dumps(query_data),
               recommendation_data=json.dumps(courses_list),
               total_recommendations=len(courses_list)
           )
           db.add(recommendation_result)
           db.commit()
       except Exception as save_error:
           print(f"Warning: Failed to save recommendation result: {save_error}")
       
       return result
       
   except HTTPException:
       raise
   except Exception as e:
       raise HTTPException(
           status_code=500,
           detail={
               'status': 'error',
               'error_code': 'PERSONALIZATION_FAILED',
               'message': 'Failed to generate personalized recommendations',
               'details': str(e)
           }
       )

@app.post("/api/courses/skills")
async def get_courses_by_skills(
    request: SkillBasedRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
   """Get course recommendations based on specific skills"""
   try:
       if not course_recommender:
           raise HTTPException(
               status_code=503,
               detail={
                   'status': 'error',
                   'error_code': 'SERVICE_UNAVAILABLE',
                   'message': 'Course recommendation service not available'
               }
           )
       
       recommendations = course_recommender.get_skill_based_recommendations(
           request.skills, 
           top_n=request.limit
       )
       
       # Format response
       courses_list = []
       for rec in recommendations:
           course_data = {
               'course_id': rec.course_id,
               'title': rec.title,
               'organization': rec.organization,
               'rating': rec.rating,
               'review_count': rec.review_count,
               'difficulty': rec.difficulty,
               'course_type': rec.course_type,
               'duration': rec.duration,
               'skills': rec.skills,
               'url': rec.url,
               'is_free': rec.is_free,
               'relevance_score': rec.relevance_score,
               'match_reasons': rec.match_reasons
           }
           courses_list.append(convert_numpy_types(course_data))
       
       result = {
           'status': 'success',
           'target_skills': request.skills,
           'recommendations': courses_list,
           'total_recommendations': len(courses_list)
       }
       
       # Save recommendation result to database
       try:
           query_data = {
               'skills': request.skills,
               'limit': request.limit
           }
           
           recommendation_result = RecommendationResult(
               user_id=current_user.id,
               recommendation_type='skill_based',
               query_data=json.dumps(query_data),
               recommendation_data=json.dumps(courses_list),
               total_recommendations=len(courses_list)
           )
           db.add(recommendation_result)
           db.commit()
       except Exception as save_error:
           print(f"Warning: Failed to save recommendation result: {save_error}")
       
       return result
       
   except HTTPException:
       raise
   except Exception as e:
       raise HTTPException(
           status_code=500,
           detail={
               'status': 'error',
               'error_code': 'SKILL_MATCHING_FAILED',
               'message': 'Failed to find courses for specified skills',
               'details': str(e)
           }
       )

@app.get("/api/courses/trending")
async def get_trending_courses(
   min_rating: float = Query(4.0, ge=0, le=5),
   limit: int = Query(20, ge=1, le=100),
   current_user: User = Depends(get_current_user),
   db: Session = Depends(get_db)
):
   """Get trending courses based on ratings and popularity"""
   try:
       if not course_recommender:
           raise HTTPException(
               status_code=503,
               detail={
                   'status': 'error',
                   'error_code': 'SERVICE_UNAVAILABLE',
                   'message': 'Course recommendation service not available'
               }
           )
       
       recommendations = course_recommender.get_trending_courses(
           top_n=limit,
           min_rating=min_rating
       )
       
       # Format response
       courses_list = []
       for rec in recommendations:
           course_data = {
               'course_id': rec.course_id,
               'title': rec.title,
               'organization': rec.organization,
               'rating': rec.rating,
               'review_count': rec.review_count,
               'difficulty': rec.difficulty,
               'course_type': rec.course_type,
               'duration': rec.duration,
               'skills': rec.skills,
               'url': rec.url,
               'is_free': rec.is_free,
               'relevance_score': rec.relevance_score,
               'match_reasons': rec.match_reasons
           }
           courses_list.append(convert_numpy_types(course_data))
       
       result = {
           'status': 'success',
           'filters': {
               'min_rating': min_rating,
               'limit': limit
           },
           'recommendations': courses_list,
           'total_recommendations': len(courses_list)
       }
       
       # Save recommendation result to database
       try:
           query_data = {
               'min_rating': min_rating,
               'limit': limit
           }
           
           recommendation_result = RecommendationResult(
               user_id=current_user.id,
               recommendation_type='trending',
               query_data=json.dumps(query_data),
               recommendation_data=json.dumps(courses_list),
               total_recommendations=len(courses_list)
           )
           db.add(recommendation_result)
           db.commit()
       except Exception as save_error:
           print(f"Warning: Failed to save recommendation result: {save_error}")
       
       return result
       
   except HTTPException:
       raise
   except Exception as e:
       raise HTTPException(
           status_code=500,
           detail={
               'status': 'error',
               'error_code': 'TRENDING_FETCH_FAILED',
               'message': 'Failed to fetch trending courses',
               'details': str(e)
           }
       )

@app.get("/api/learning-path/{career_id}")
async def get_learning_path(
   career_id: str,
   skill_level: str = Query("beginner", regex="^(beginner|intermediate|advanced)$"),
   current_user: User = Depends(get_current_user),
   db: Session = Depends(get_db)
):
   """Generate a structured learning path for a specific career"""
   try:
       if not course_recommender:
           raise HTTPException(
               status_code=503,
               detail={
                   'status': 'error',
                   'error_code': 'SERVICE_UNAVAILABLE',
                   'message': 'Course recommendation service not available'
               }
           )
       
       # Convert career_id to career name
       career_name = career_id.replace('_', ' ').title()
       
       # Generate learning path
       learning_path = course_recommender.get_learning_path(career_name, skill_level)
       
       # Convert numpy types to native Python types for JSON serialization
       result = {
           'status': 'success',
           'career_info': {
               'career_id': career_id,
               'career_name': career_name,
               'skill_level': skill_level
           },
           'learning_path': learning_path
       }
       result = convert_numpy_types(result)
       
       # Save learning path to database for authenticated user
       try:
           # Check if user already has this learning path
           existing_path = db.query(UserLearningPath).filter(
               UserLearningPath.user_id == current_user.id,
               UserLearningPath.career_path == career_name,
               UserLearningPath.skill_level == skill_level
           ).first()
           
           path_data_str = str(learning_path) if learning_path else None
           total_checkpoints = len(learning_path.get('phases', [])) if isinstance(learning_path, dict) and 'phases' in learning_path else None
           estimated_duration = learning_path.get('estimated_total_duration', '') if isinstance(learning_path, dict) else None
           
           if existing_path:
               # Update existing path
               existing_path.path_data = path_data_str
               existing_path.total_checkpoints = total_checkpoints
               existing_path.estimated_duration = estimated_duration
               db.commit()
           else:
               # Create new path
               user_learning_path = UserLearningPath(
                   user_id=current_user.id,
                   career_path=career_name,
                   skill_level=skill_level,
                   path_data=path_data_str,
                   total_checkpoints=total_checkpoints,
                   estimated_duration=estimated_duration
               )
               db.add(user_learning_path)
               db.commit()
       except Exception as save_error:
           print(f"Warning: Failed to save learning path: {save_error}")
       
       return result
       
   except HTTPException:
       raise
   except Exception as e:
       raise HTTPException(
           status_code=500,
           detail={
               'status': 'error',
               'error_code': 'LEARNING_PATH_FAILED',
               'message': 'Failed to generate learning path',
               'details': str(e)
           }
       )

@app.post("/api/auth/register", response_model=UserResponse)
async def register_user(user: UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    try:
        # Check if user already exists
        existing_user = get_user_by_email(db, user.email)
        if existing_user:
            raise HTTPException(
                status_code=400,
                detail={
                    'status': 'error',
                    'error_code': 'USER_EXISTS',
                    'message': 'Email already registered'
                }
            )
        
        # Create new user
        db_user = create_user(db, user)
        return UserResponse.model_validate(db_user)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                'status': 'error',
                'error_code': 'REGISTRATION_FAILED',
                'message': 'Failed to register user',
                'details': str(e)
            }
        )

@app.post("/api/auth/login", response_model=Token)
async def login_user(user_data: UserLogin, db: Session = Depends(get_db)):
    """Login user and return JWT token"""
    try:
        # Authenticate user
        user = authenticate_user(db, user_data.email, user_data.password)
        if not user:
            raise HTTPException(
                status_code=401,
                detail={
                    'status': 'error',
                    'error_code': 'INVALID_CREDENTIALS',
                    'message': 'Invalid email or password'
                }
            )
        
        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(user.id)}, 
            expires_delta=access_token_expires
        )
        
        return Token(
            access_token=access_token,
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                'status': 'error',
                'error_code': 'LOGIN_FAILED',
                'message': 'Failed to login user',
                'details': str(e)
            }
        )

@app.get("/api/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return UserResponse.model_validate(current_user)

@app.post("/api/courses/save", response_model=SavedCourseResponse)
async def save_course(
    course_data: SavedCourseCreate, 
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Save a course for the current user"""
    try:
        # Check if course is already saved
        existing_saved = db.query(SavedCourse).filter(
            SavedCourse.user_id == current_user.id,
            SavedCourse.course_id == course_data.course_id
        ).first()
        
        if existing_saved:
            raise HTTPException(
                status_code=400,
                detail={
                    'status': 'error',
                    'error_code': 'COURSE_ALREADY_SAVED',
                    'message': 'Course is already saved'
                }
            )
        
        # Create saved course
        saved_course = SavedCourse(
            user_id=current_user.id,
            course_id=course_data.course_id,
            course_title=course_data.course_title,
            course_url=course_data.course_url
        )
        
        db.add(saved_course)
        db.commit()
        db.refresh(saved_course)
        
        return SavedCourseResponse.model_validate(saved_course)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                'status': 'error',
                'error_code': 'SAVE_COURSE_FAILED',
                'message': 'Failed to save course',
                'details': str(e)
            }
        )

@app.get("/api/courses/saved", response_model=List[SavedCourseResponse])
async def get_saved_courses(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all saved courses for the current user"""
    try:
        saved_courses = db.query(SavedCourse).filter(
            SavedCourse.user_id == current_user.id
        ).order_by(SavedCourse.saved_at.desc()).all()
        
        return [SavedCourseResponse.model_validate(course) for course in saved_courses]
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                'status': 'error',
                'error_code': 'GET_SAVED_COURSES_FAILED',
                'message': 'Failed to get saved courses',
                'details': str(e)
            }
        )

@app.delete("/api/courses/save/{course_id}")
async def unsave_course(
    course_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove a saved course"""
    try:
        saved_course = db.query(SavedCourse).filter(
            SavedCourse.user_id == current_user.id,
            SavedCourse.course_id == course_id
        ).first()
        
        if not saved_course:
            raise HTTPException(
                status_code=404,
                detail={
                    'status': 'error',
                    'error_code': 'COURSE_NOT_FOUND',
                    'message': 'Saved course not found'
                }
            )
        
        db.delete(saved_course)
        db.commit()
        
        return {
            'status': 'success',
            'message': 'Course removed from saved list'
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                'status': 'error',
                'error_code': 'UNSAVE_COURSE_FAILED',
                'message': 'Failed to remove saved course',
                'details': str(e)
            }
        )

@app.post("/api/career/save", response_model=CareerChoiceResponse)
async def save_user_career(
    career_data: CareerChoiceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Save or update user's chosen career path"""
    try:
        # Check if user already has a career choice
        existing_choice = db.query(UserCareerChoice).filter(
            UserCareerChoice.user_id == current_user.id
        ).first()
        
        if existing_choice:
            # Update existing choice
            existing_choice.career_path = career_data.career_path
            existing_choice.assessment_result = career_data.assessment_result
            existing_choice.confidence_score = career_data.confidence_score
            existing_choice.updated_at = datetime.utcnow()
            
            db.commit()
            db.refresh(existing_choice)
            return CareerChoiceResponse.model_validate(existing_choice)
        else:
            # Create new choice
            career_choice = UserCareerChoice(
                user_id=current_user.id,
                career_path=career_data.career_path,
                assessment_result=career_data.assessment_result,
                confidence_score=career_data.confidence_score
            )
            
            db.add(career_choice)
            db.commit()
            db.refresh(career_choice)
            return CareerChoiceResponse.model_validate(career_choice)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                'status': 'error',
                'error_code': 'SAVE_CAREER_FAILED',
                'message': 'Failed to save career choice',
                'details': str(e)
            }
        )

@app.get("/api/career/current", response_model=CareerChoiceResponse)
async def get_user_career(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's current career choice"""
    try:
        career_choice = db.query(UserCareerChoice).filter(
            UserCareerChoice.user_id == current_user.id
        ).first()
        
        if not career_choice:
            raise HTTPException(
                status_code=404,
                detail={
                    'status': 'error',
                    'error_code': 'NO_CAREER_FOUND',
                    'message': 'User has not selected a career path yet'
                }
            )
        
        return CareerChoiceResponse.model_validate(career_choice)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                'status': 'error',
                'error_code': 'GET_CAREER_FAILED',
                'message': 'Failed to get career choice',
                'details': str(e)
            }
        )

@app.post("/api/profile", response_model=UserProfileResponse)
async def create_or_update_profile(
    profile_data: UserProfileCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create or update user profile"""
    try:
        existing_profile = db.query(UserProfile).filter(
            UserProfile.user_id == current_user.id
        ).first()
        
        if existing_profile:
            # Update existing profile
            existing_profile.preferred_skills = profile_data.preferred_skills
            existing_profile.difficulty_preference = profile_data.difficulty_preference
            existing_profile.time_availability = profile_data.time_availability
            existing_profile.budget_preference = profile_data.budget_preference
            existing_profile.learning_style = profile_data.learning_style
            existing_profile.career_goals = profile_data.career_goals
            existing_profile.updated_at = datetime.utcnow()
            
            db.commit()
            db.refresh(existing_profile)
            return UserProfileResponse.model_validate(existing_profile)
        else:
            # Create new profile
            user_profile = UserProfile(
                user_id=current_user.id,
                preferred_skills=profile_data.preferred_skills,
                difficulty_preference=profile_data.difficulty_preference,
                time_availability=profile_data.time_availability,
                budget_preference=profile_data.budget_preference,
                learning_style=profile_data.learning_style,
                career_goals=profile_data.career_goals
            )
            
            db.add(user_profile)
            db.commit()
            db.refresh(user_profile)
            return UserProfileResponse.model_validate(user_profile)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                'status': 'error',
                'error_code': 'PROFILE_SAVE_FAILED',
                'message': 'Failed to save user profile',
                'details': str(e)
            }
        )

@app.get("/api/profile", response_model=UserProfileResponse)
async def get_user_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user profile"""
    try:
        user_profile = db.query(UserProfile).filter(
            UserProfile.user_id == current_user.id
        ).first()
        
        if not user_profile:
            raise HTTPException(
                status_code=404,
                detail={
                    'status': 'error',
                    'error_code': 'PROFILE_NOT_FOUND',
                    'message': 'User profile not found'
                }
            )
        
        return UserProfileResponse.model_validate(user_profile)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                'status': 'error',
                'error_code': 'GET_PROFILE_FAILED',  
                'message': 'Failed to get user profile',
                'details': str(e)
            }
        )

@app.get("/api/assessments/history")
async def get_assessment_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(10, ge=1, le=50)
):
    """Get user's assessment history"""
    try:
        assessments = db.query(AssessmentResult).filter(
            AssessmentResult.user_id == current_user.id
        ).order_by(AssessmentResult.created_at.desc()).limit(limit).all()
        
        assessment_list = [AssessmentResultResponse.model_validate(assessment) for assessment in assessments]
        
        return {
            'status': 'success',
            'assessments': assessment_list,
            'total_assessments': len(assessment_list)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                'status': 'error',
                'error_code': 'GET_ASSESSMENTS_FAILED',
                'message': 'Failed to get assessment history',
                'details': str(e)
            }
        )

@app.get("/api/learning-paths/saved")
async def get_saved_learning_paths(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's saved learning paths"""
    try:
        learning_paths = db.query(UserLearningPath).filter(
            UserLearningPath.user_id == current_user.id
        ).order_by(UserLearningPath.created_at.desc()).all()
        
        paths_list = [UserLearningPathResponse.model_validate(path) for path in learning_paths]
        
        return {
            'status': 'success',
            'learning_paths': paths_list,
            'total_paths': len(paths_list)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                'status': 'error',
                'error_code': 'GET_LEARNING_PATHS_FAILED',
                'message': 'Failed to get saved learning paths',
                'details': str(e)
            }
        )

@app.get("/api/recommendations/history")
async def get_recommendation_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    recommendation_type: Optional[str] = Query(None, regex="^(personalized|skill_based|trending|career_specific)$"),
    limit: int = Query(10, ge=1, le=50)
):
    """Get user's recommendation history"""
    try:
        query = db.query(RecommendationResult).filter(
            RecommendationResult.user_id == current_user.id
        )
        
        if recommendation_type:
            query = query.filter(RecommendationResult.recommendation_type == recommendation_type)
        
        recommendations = query.order_by(RecommendationResult.created_at.desc()).limit(limit).all()
        
        recommendation_list = [RecommendationResultResponse.model_validate(rec) for rec in recommendations]
        
        return {
            'status': 'success',
            'recommendations': recommendation_list,
            'total_recommendations': len(recommendation_list),
            'filter': {
                'recommendation_type': recommendation_type,
                'limit': limit
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                'status': 'error',
                'error_code': 'GET_RECOMMENDATIONS_FAILED',
                'message': 'Failed to get recommendation history',
                'details': str(e)
            }
        )

if __name__ == "__main__":
   import uvicorn
   import os
   
   port = int(os.environ.get("PORT", 8000))
   host = os.environ.get("HOST", "0.0.0.0")
   
   uvicorn.run(app, host=host, port=port)
