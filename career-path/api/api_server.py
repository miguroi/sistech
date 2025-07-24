from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional, Union, Any
import pandas as pd
import json
import numpy as np
from datetime import datetime

from career_processor import CareerProcessor
from roadmap_generator import RoadmapGenerator
from assessment_questions import AssessmentGenerator
from course_recommender import CourseRecommender, UserProfile

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

# Initialize FastAPI app
app = FastAPI(
   title="Career Platform API",
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
   """Initialize processors on startup"""
   global career_processor, roadmap_generator, assessment_generator, course_recommender
   
   try:
       import os
       
       # Get the base directory (career-path folder)
       base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
       
       # Define file paths relative to base directory
       career_data_path = os.path.join(base_dir, 'data', 'career_dataset.csv')
       courses_data_path = os.path.join(os.path.dirname(base_dir), 'data', 'csv', 'coursera_courses_cleaned.csv')
       
       # Fallback paths if the above don't work
       if not os.path.exists(courses_data_path):
           courses_data_path = os.path.join(base_dir, '..', 'data', 'csv', 'coursera_courses_cleaned.csv')
       if not os.path.exists(courses_data_path):
           courses_data_path = '../data/csv/coursera_courses_cleaned.csv'
       
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
       "message": "Career Platform API is running",
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
async def assess_career(request: AssessmentRequest):
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
   offset: int = Query(0, ge=0)
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
               'title': course['title'],
               'organization': course['organization'],
               'rating': course['rating'] if pd.notna(course['rating']) else None,
               'review_count': int(course['review_count']) if pd.notna(course['review_count']) else 0,
               'difficulty': course['difficulty'],
               'course_type': course['course_type'],
               'duration': course['duration'],
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
       
       return {
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
               'title': course['title'],
               'organization': course['organization'],
               'rating': course['rating'] if pd.notna(course['rating']) else None,
               'review_count': int(course['review_count']) if pd.notna(course['review_count']) else 0,
               'difficulty': course['difficulty'],
               'course_type': course['course_type'],
               'duration': course['duration'],
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
async def get_personalized_courses(request: UserProfileRequest):
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
       
       # Create user profile
       user_profile = UserProfile(
           user_id=request.user_id,
           preferred_skills=request.preferred_skills,
           difficulty_preference=request.difficulty_preference,
           time_availability=request.time_availability,
           budget_preference=request.budget_preference,
           learning_style=request.learning_style,
           career_goals=request.career_goals
       )
       
       # Get personalized recommendations
       recommendations = course_recommender.get_personalized_recommendations(user_profile, top_n=15)
       
       # Format response
       courses_list = []
       for rec in recommendations:
           courses_list.append({
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
           })
       
       return {
           'status': 'success',
           'user_profile': {
               'user_id': request.user_id,
               'career_goals': request.career_goals,
               'difficulty_preference': request.difficulty_preference
           },
           'recommendations': courses_list,
           'total_recommendations': len(courses_list)
       }
       
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
async def get_courses_by_skills(request: SkillBasedRequest):
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
           courses_list.append({
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
           })
       
       return {
           'status': 'success',
           'target_skills': request.skills,
           'recommendations': courses_list,
           'total_recommendations': len(courses_list)
       }
       
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
   limit: int = Query(20, ge=1, le=100)
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
           courses_list.append({
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
           })
       
       return {
           'status': 'success',
           'filters': {
               'min_rating': min_rating,
               'limit': limit
           },
           'recommendations': courses_list,
           'total_recommendations': len(courses_list)
       }
       
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
   skill_level: str = Query("beginner", regex="^(beginner|intermediate|advanced)$")
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
       
       return {
           'status': 'success',
           'career_info': {
               'career_id': career_id,
               'career_name': career_name,
               'skill_level': skill_level
           },
           'learning_path': learning_path
       }
       
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

if __name__ == "__main__":
   import uvicorn
   import os
   
   port = int(os.environ.get("PORT", 8000))
   host = os.environ.get("HOST", "0.0.0.0")
   
   uvicorn.run(app, host=host, port=port)
