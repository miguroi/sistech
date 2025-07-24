from typing import Dict, List, Optional
from dataclasses import dataclass
import pandas as pd
import json
import os
import logging
import random

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class AssessmentQuestion:
    question_id: int
    question_text: str
    question_type: str  # 'interests', 'skills', 'preferences', 'experience'
    category: str
    options: Optional[List[str]] = None  # Multiple choice options
    is_required: bool = True
    weight: float = 1.0  # Weight for scoring

class AssessmentGenerator:
    def __init__(self, career_processor, config_path="data/assessment_questions_data.json"):
        self.career_processor = career_processor
        self.config_path = config_path
        self.questions = self._load_questions()

    def _load_questions(self) -> List[AssessmentQuestion]:
        """Load all assessment questions from configuration file"""
        
        try:
            if not os.path.exists(self.config_path):
                logger.error(f"Assessment config file {self.config_path} not found")
                raise FileNotFoundError(f"Config file {self.config_path} is required")
            
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            
            questions = []
            for q_data in config.get('core_questions', []):
                question = AssessmentQuestion(
                    question_id=q_data['question_id'],
                    question_text=q_data['question_text'],
                    question_type=q_data['question_type'],
                    category=q_data['category'],
                    options=q_data.get('options'),
                    is_required=q_data.get('is_required', True),
                    weight=q_data.get('weight', 1.0)
                )
                questions.append(question)
            
            # Optional: Randomize question order for variety (keeping required questions first)
            required_questions = [q for q in questions if q.is_required]
            optional_questions = [q for q in questions if not q.is_required]
            random.shuffle(optional_questions)
            
            final_questions = required_questions + optional_questions
            
            logger.info(f"Loaded {len(final_questions)} questions from config ({len(required_questions)} required, {len(optional_questions)} optional)")
            return final_questions
            
        except Exception as e:
            logger.error(f"Error loading assessment questions: {e}")
            raise RuntimeError(f"Failed to load assessment questions: {e}")
    def get_questions_by_type(self, question_type: str) -> List[AssessmentQuestion]:
        """Get questions filtered by type (interests, skills, preferences, experience)"""
        return [q for q in self.questions if q.question_type == question_type]
    
    def get_required_questions(self) -> List[AssessmentQuestion]:
        """Get only required questions"""
        return [q for q in self.questions if q.is_required]
    
    def get_questions_by_category(self, category: str) -> List[AssessmentQuestion]:
        """Get questions filtered by category"""
        return [q for q in self.questions if q.category == category]
    
    def validate_user_responses(self, user_responses: Dict) -> Dict:
        """Validate that user responses meet minimum requirements"""
        answers = user_responses.get('answers', [])
        answer_ids = {answer.get('question_id') for answer in answers}
        
        required_questions = self.get_required_questions()
        required_ids = {q.question_id for q in required_questions}
        
        missing_required = required_ids - answer_ids
        
        return {
            'is_valid': len(missing_required) == 0,
            'missing_required_questions': list(missing_required),
            'total_answered': len(answers),
            'required_answered': len(required_ids & answer_ids),
            'total_required': len(required_ids)
        }
    
    def get_questions(self) -> List[Dict]:
        """Get all assessment questions as dictionaries for API response"""
        return [
            {
                'question_id': q.question_id,
                'question_text': q.question_text,
                'question_type': q.question_type,
                'category': q.category,
                'options': q.options,
                'is_required': q.is_required,
                'weight': q.weight
            }
            for q in self.questions
        ]
    
    def process_assessment(self, user_responses: Dict) -> Dict:
        """Process user responses and return career recommendation"""
        
        try:
            # Validate responses first
            validation = self.validate_user_responses(user_responses)
            if not validation['is_valid']:
                return {
                    'status': 'error',
                    'error_code': 'INCOMPLETE_ASSESSMENT',
                    'message': 'Assessment incomplete - missing required questions',
                    'validation_details': validation
                }
            
            # Process assessment through career processor
            matches = self.career_processor.assess_career_match(user_responses)
            
            if not matches:
                return {
                    'status': 'error',
                    'error_code': 'NO_MATCHES',
                    'message': 'Unable to find career matches based on responses'
                }
            
            top_match = matches[0]
            
            # Get additional details for top match
            career_data = self.career_processor.career_df[
                self.career_processor.career_df['role'] == top_match.career_name
            ]
            
            description = ""
            if not career_data.empty:
                # Get the first answer that describes what the role does
                for answer in career_data['answer'].values:
                    if 'does' in answer.lower() or 'responsibilities' in answer.lower():
                        description = answer
                        break
                if not description and len(career_data) > 0:
                    description = career_data['answer'].iloc[0]
            
            # Get course recommendations for the top career match
            recommended_courses = self._get_assessment_based_courses(
                top_match.career_name, 
                user_responses, 
                top_n=8
            )
            
            return {
                'status': 'success',
                'assessment_summary': {
                    'questions_answered': validation['total_answered'],
                    'required_questions_answered': validation['required_answered'],
                    'assessment_completeness': round((validation['required_answered'] / validation['total_required']) * 100, 1)
                },
                'career_recommendation': {
                    'career_id': top_match.career_id,
                    'career_name': top_match.career_name,
                    'match_percentage': round(top_match.match_score * 100, 1),
                    'description': description,
                    'key_skills_mentioned': top_match.matching_skills[:5],
                    'related_qa_count': len(career_data)
                },
                'course_recommendations': recommended_courses,
                'confidence_score': top_match.match_score,
                'alternatives': [
                    {
                        'career_id': match.career_id,
                        'career_name': match.career_name,
                        'match_percentage': round(match.match_score * 100, 1)
                    }
                    for match in matches[1:4]
                ]
            }
            
        except Exception as e:
            logger.error(f"Error processing assessment: {e}")
            return {
                'status': 'error',
                'error_code': 'PROCESSING_FAILED',
                'message': 'Failed to process assessment',
                'details': str(e)
            }
    
    def _get_assessment_based_courses(self, career_name: str, user_responses: Dict, top_n: int = 8) -> List[Dict]:
        """Get course recommendations based on assessment responses"""
        try:
            # Try to get courses from career processor if available
            if hasattr(self.career_processor, 'get_course_recommendations'):
                recommendations = self.career_processor.get_course_recommendations(
                    career_name, top_n=top_n
                )
                
                # Convert to dictionary format if recommendations are objects
                course_list = []
                for rec in recommendations:
                    if hasattr(rec, 'course_id'):  # CourseRecommendation object
                        course_list.append({
                            'course_id': rec.course_id,
                            'title': rec.title,
                            'organization': rec.organization,
                            'rating': rec.rating,
                            'difficulty': rec.difficulty,
                            'duration': rec.duration,
                            'skills': rec.skills,
                            'is_free': rec.is_free,
                            'relevance_score': rec.relevance_score
                        })
                    else:  # DataFrame row or dictionary
                        course_list.append(rec)
                
                return course_list[:top_n]
            
            # Fallback: get related courses from career processor
            elif hasattr(self.career_processor, 'get_related_courses'):
                courses_df = self.career_processor.get_related_courses(career_name, top_n=top_n)
                
                if not courses_df.empty:
                    return courses_df.head(top_n).to_dict('records')
            
            return []
            
        except Exception as e:
            logger.error(f"Error getting assessment-based courses: {e}")
            return []
