import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import KMeans
from collections import Counter
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import re

from career_processor import extract_tokens, create_tfidf_vectorizer, compute_text_similarities

@dataclass
class CourseRecommendation:
    course_id: str
    title: str
    organization: str
    rating: Optional[float]
    review_count: int
    difficulty: str
    course_type: str
    duration: str
    skills: List[str]
    url: str
    is_free: bool
    relevance_score: float
    match_reasons: List[str]

@dataclass
class UserProfile:
    user_id: str
    preferred_skills: List[str]
    difficulty_preference: str
    time_availability: str
    budget_preference: str
    learning_style: str
    career_goals: List[str]

class CourseRecommender:
    def __init__(self, courses_data_path: str, career_processor=None):
        self.courses_df = pd.read_csv(courses_data_path) if courses_data_path else pd.DataFrame()
        self.career_processor = career_processor
        self.course_skills_cache = {}
        self.user_profiles = {}
        self.course_embeddings = None
        self.tfidf_vectorizer = None
        
    def extract_skills_from_course(self, course_title: str, course_description: str = "") -> List[str]:
        """Extract skills from course content using frequency analysis"""
        cache_key = f"{course_title}_{course_description}"
        if cache_key in self.course_skills_cache:
            return self.course_skills_cache[cache_key]
            
        combined_text = f"{course_title} {course_description}"
        meaningful_tokens = extract_tokens(combined_text)
        
        # Get most frequent terms as potential skills
        word_freq = Counter(meaningful_tokens)
        top_skills = [word for word, freq in word_freq.most_common(15)]
        
        self.course_skills_cache[cache_key] = top_skills
        return top_skills
    
    def get_course_recommendations_by_career(self, career_role: str, top_n: int = 20, 
                                           difficulty_filter: Optional[str] = None) -> List[CourseRecommendation]:
        """Get course recommendations based on career role using TF-IDF similarity"""
        if self.courses_df.empty:
            return []
            
        if self.career_processor:
            career_text = self._get_career_description_from_processor(career_role)
        else:
            career_text = career_role
            
        if not career_text:
            return []
            
        # Prepare course texts for similarity comparison
        course_texts = []
        for _, course in self.courses_df.iterrows():
            course_text = f"{course['title']} {course.get('skills', '')} {course.get('description', '')}"
            course_texts.append(course_text)
        
        vectorizer_params = {'max_features': 2000, 'min_df': 2}
        similarities, vectorizer = compute_text_similarities(career_text, course_texts, vectorizer_params)
        
        # Apply difficulty filter if specified
        filtered_courses = self.courses_df.copy()
        if difficulty_filter:
            difficulty_map = {
                'beginner': 'Beginner',
                'intermediate': 'Intermediate', 
                'advanced': 'Advanced'
            }
            if difficulty_filter.lower() in difficulty_map:
                filtered_courses = filtered_courses[
                    filtered_courses['difficulty'] == difficulty_map[difficulty_filter.lower()]
                ]
        
        # Get top matching courses
        course_similarities = list(zip(range(len(similarities)), similarities))
        course_similarities.sort(key=lambda x: x[1], reverse=True)
        
        recommendations = []
        count = 0
        for course_idx, similarity_score in course_similarities:
            if count >= top_n:
                break
                
            if course_idx >= len(filtered_courses):
                continue
                
            course = filtered_courses.iloc[course_idx]
            
            # Extract match reasons from TF-IDF features
            match_reasons = self._extract_match_reasons(career_text, course, vectorizer)
            
            # Parse skills
            skills_list = self._parse_course_skills(course.get('skills', ''))
            
            recommendation = CourseRecommendation(
                course_id=course.get('course_id', f"course_{course_idx}"),
                title=course['title'],
                organization=course.get('organization', 'Unknown'),
                rating=course.get('rating') if pd.notna(course.get('rating')) else None,
                review_count=int(course.get('review_count', 0)) if pd.notna(course.get('review_count')) else 0,
                difficulty=course.get('difficulty', 'Unknown'),
                course_type=course.get('course_type', 'Course'),
                duration=course.get('duration', 'Unknown'),
                skills=skills_list,
                url=course.get('url', ''),
                is_free=course.get('is_free', False),
                relevance_score=round(similarity_score, 3),
                match_reasons=match_reasons
            )
            
            recommendations.append(recommendation)
            count += 1
            
        return recommendations
    
    def get_personalized_recommendations(self, user_profile: UserProfile, 
                                       top_n: int = 15) -> List[CourseRecommendation]:
        """Get personalized course recommendations based on user profile"""
        if self.courses_df.empty:
            return []
            
        # Store user profile
        self.user_profiles[user_profile.user_id] = user_profile
        
        # Create user preference text
        user_text = self._create_user_preference_text(user_profile)
        
        # Get base recommendations
        base_recommendations = []
        
        # Get recommendations for each career goal
        for career_goal in user_profile.career_goals:
            career_recs = self.get_course_recommendations_by_career(
                career_goal, 
                top_n=top_n * 2,  # Get more to allow for filtering
                difficulty_filter=user_profile.difficulty_preference
            )
            base_recommendations.extend(career_recs)
        
        # Remove duplicates
        seen_courses = set()
        unique_recommendations = []
        for rec in base_recommendations:
            if rec.course_id not in seen_courses:
                seen_courses.add(rec.course_id)
                unique_recommendations.append(rec)
        
        # Apply personalization scoring
        personalized_recs = self._apply_personalization_scoring(unique_recommendations, user_profile)
        
        # Sort by personalized score and return top N
        personalized_recs.sort(key=lambda x: x.relevance_score, reverse=True)
        
        return personalized_recs[:top_n]
    
    def get_skill_based_recommendations(self, target_skills: List[str], 
                                      top_n: int = 20) -> List[CourseRecommendation]:
        """Get course recommendations based on specific skills"""
        if self.courses_df.empty:
            return []
            
        skills_text = ' '.join(target_skills)
        
        # Prepare course texts focusing on skills
        course_texts = []
        for _, course in self.courses_df.iterrows():
            skills_field = course.get('skills', '')
            title_field = course.get('title', '')
            course_text = f"{title_field} {skills_field}"
            course_texts.append(course_text)
        
        vectorizer_params = {'max_features': 1500, 'ngram_range': (1, 2)}
        similarities, vectorizer = compute_text_similarities(skills_text, course_texts, vectorizer_params)
        
        # Create recommendations
        course_similarities = list(zip(range(len(similarities)), similarities))
        course_similarities.sort(key=lambda x: x[1], reverse=True)
        
        recommendations = []
        for i, (course_idx, similarity_score) in enumerate(course_similarities[:top_n]):
            course = self.courses_df.iloc[course_idx]
            
            # Calculate skill overlap
            course_skills = self._parse_course_skills(course.get('skills', ''))
            skill_overlap = len(set(target_skills) & set(course_skills))
            
            match_reasons = [f"Matches {skill_overlap} target skills"] if skill_overlap > 0 else []
            skills_list = self._parse_course_skills(course.get('skills', ''))
            
            recommendation = CourseRecommendation(
                course_id=course.get('course_id', f"course_{course_idx}"),
                title=course['title'],
                organization=course.get('organization', 'Unknown'),
                rating=course.get('rating') if pd.notna(course.get('rating')) else None,
                review_count=int(course.get('review_count', 0)) if pd.notna(course.get('review_count')) else 0,
                difficulty=course.get('difficulty', 'Unknown'),
                course_type=course.get('course_type', 'Course'),
                duration=course.get('duration', 'Unknown'),
                skills=skills_list,
                url=course.get('url', ''),
                is_free=course.get('is_free', False),
                relevance_score=round(similarity_score, 3),
                match_reasons=match_reasons
            )
            
            recommendations.append(recommendation)
            
        return recommendations
    
    def get_trending_courses(self, top_n: int = 20, 
                           min_rating: float = 4.0) -> List[CourseRecommendation]:
        """Get trending courses based on ratings and review counts"""
        if self.courses_df.empty:
            return []
            
        # Filter courses with good ratings and substantial reviews
        trending_df = self.courses_df[
            (self.courses_df['rating'] >= min_rating) & 
            (self.courses_df['review_count'] >= 100)
        ].copy()
        
        if trending_df.empty:
            trending_df = self.courses_df.copy()
        
        # Calculate trending score (combination of rating and review count)
        trending_df['trending_score'] = (
            trending_df['rating'].fillna(0) * 0.7 + 
            np.log1p(trending_df['review_count'].fillna(0)) * 0.3
        )
        
        # Sort by trending score
        trending_df = trending_df.sort_values('trending_score', ascending=False)
        
        recommendations = []
        for _, course in trending_df.head(top_n).iterrows():
            skills_list = self._parse_course_skills(course.get('skills', ''))
            
            recommendation = CourseRecommendation(
                course_id=course.get('course_id', f"trending_{len(recommendations)}"),
                title=course['title'],
                organization=course.get('organization', 'Unknown'),
                rating=course.get('rating') if pd.notna(course.get('rating')) else None,
                review_count=int(course.get('review_count', 0)) if pd.notna(course.get('review_count')) else 0,
                difficulty=course.get('difficulty', 'Unknown'),
                course_type=course.get('course_type', 'Course'),
                duration=course.get('duration', 'Unknown'),
                skills=skills_list,
                url=course.get('url', ''),
                is_free=course.get('is_free', False),
                relevance_score=round(course.get('trending_score', 0), 3),
                match_reasons=['High rating and popular']
            )
            
            recommendations.append(recommendation)
            
        return recommendations
    
    def get_learning_path(self, career_goal: str, current_skill_level: str = 'beginner') -> Dict:
        """Generate a structured learning path for a specific career goal"""
        if self.courses_df.empty:
            return {'path': [], 'total_duration': '0 weeks', 'total_courses': 0}
            
        # Define skill progression levels
        level_map = {
            'beginner': ['Beginner'],
            'intermediate': ['Beginner', 'Intermediate'],
            'advanced': ['Beginner', 'Intermediate', 'Advanced']
        }
        
        target_levels = level_map.get(current_skill_level, ['Beginner'])
        
        # Get courses for career goal
        career_courses = self.get_course_recommendations_by_career(career_goal, top_n=50)
        
        # Group courses by difficulty
        grouped_courses = {'Beginner': [], 'Intermediate': [], 'Advanced': []}
        for course in career_courses:
            if course.difficulty in grouped_courses:
                grouped_courses[course.difficulty].append(course)
        
        # Create learning path
        learning_path = []
        total_courses = 0
        
        for level in ['Beginner', 'Intermediate', 'Advanced']:
            if level in target_levels and grouped_courses[level]:
                # Take top courses for this level
                level_courses = sorted(grouped_courses[level], 
                                     key=lambda x: x.relevance_score, reverse=True)[:5]
                
                path_step = {
                    'level': level,
                    'courses': [
                        {
                            'course_id': course.course_id,
                            'title': course.title,
                            'organization': course.organization,
                            'duration': course.duration,
                            'skills': course.skills[:5],  # Top 5 skills
                            'rating': course.rating,
                            'is_free': course.is_free,
                            'relevance_score': course.relevance_score
                        }
                        for course in level_courses
                    ]
                }
                
                learning_path.append(path_step)
                total_courses += len(level_courses)
        
        # Calculate estimated total duration (simplified)
        estimated_weeks = total_courses * 2  # Rough estimate of 2 weeks per course
        
        return {
            'career_goal': career_goal,
            'current_level': current_skill_level,
            'path': learning_path,
            'total_duration': f"{estimated_weeks} weeks",
            'total_courses': total_courses
        }
    
    def _get_career_description_from_processor(self, career_role: str) -> str:
        """Get career description from career processor if available"""
        if not self.career_processor:
            return career_role
            
        try:
            return self.career_processor._get_career_description(career_role)
        except:
            return career_role
    
    def _extract_match_reasons(self, career_text: str, course: pd.Series, 
                             vectorizer) -> List[str]:
        """Extract reasons why a course matches the career"""
        reasons = []
        
        # Get top TF-IDF features
        try:
            course_text = f"{course['title']} {course.get('skills', '')}"
            course_vector = vectorizer.transform([course_text])
            feature_names = vectorizer.get_feature_names_out()
            
            # Get top features for this course
            top_features_idx = course_vector.toarray()[0].argsort()[-5:]
            top_features = [feature_names[idx] for idx in top_features_idx if course_vector[0, idx] > 0]
            
            if top_features:
                reasons.append(f"Relevant topics: {', '.join(top_features[:3])}")
                
        except:
            reasons.append("Content relevance match")
            
        return reasons
    
    def _parse_course_skills(self, skills_text: str) -> List[str]:
        """Parse skills from course skills field"""
        if not skills_text or pd.isna(skills_text):
            return []
            
        # Split by common delimiters and clean
        skills_list = []
        for delimiter in [',', ';', '|', '\n']:
            if delimiter in str(skills_text):
                skills_list = [skill.strip() for skill in str(skills_text).split(delimiter)]
                break
        
        if not skills_list:
            # Split by spaces if no delimiters found
            skills_list = [skill.strip() for skill in str(skills_text).split()]
        
        # Filter and clean skills
        cleaned_skills = []
        for skill in skills_list:
            if len(skill) > 2 and skill.lower() not in ['and', 'the', 'of', 'in', 'for']:
                cleaned_skills.append(skill.title())
        
        return cleaned_skills[:10]  # Limit to top 10 skills
    
    def _create_user_preference_text(self, user_profile: UserProfile) -> str:
        """Create text representation of user preferences"""
        preference_parts = []
        preference_parts.extend(user_profile.preferred_skills)
        preference_parts.extend(user_profile.career_goals)
        preference_parts.append(user_profile.learning_style)
        
        return ' '.join(preference_parts)
    
    def _apply_personalization_scoring(self, recommendations: List[CourseRecommendation], 
                                     user_profile: UserProfile) -> List[CourseRecommendation]:
        """Apply personalization scoring to recommendations"""
        for rec in recommendations:
            personalization_boost = 0
            
            # Boost for matching difficulty preference
            if rec.difficulty.lower() == user_profile.difficulty_preference.lower():
                personalization_boost += 0.1
            
            # Boost for free courses if budget preference is low
            if user_profile.budget_preference.lower() == 'free' and rec.is_free:
                personalization_boost += 0.1
            
            # Boost for matching skills
            skill_overlap = len(set(rec.skills) & set(user_profile.preferred_skills))
            if skill_overlap > 0:
                personalization_boost += min(0.2, skill_overlap * 0.05)
            
            # Apply boost
            rec.relevance_score = min(1.0, rec.relevance_score + personalization_boost)
            
        return recommendations