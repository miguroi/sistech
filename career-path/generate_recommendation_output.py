import pandas as pd
import json
import numpy as np
from datetime import datetime
from career_processor import CareerProcessor
from assessment_questions import AssessmentGenerator
from course_recommender import CourseRecommender, UserProfile

class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, (np.bool_, bool)):
            return bool(obj)
        return super(NumpyEncoder, self).default(obj)

def generate_sample_recommendations():
    """Generate sample recommendation outputs"""
    
    career_processor = CareerProcessor(
        'data/career_dataset.csv',
        'data/coursera_courses_cleaned.csv'
    )
    assessment_generator = AssessmentGenerator(career_processor)
    
    try:
        course_recommender = CourseRecommender(
            courses_data_path='data/coursera_courses_cleaned.csv',
            career_processor=career_processor
        )
    except:
        course_recommender = None
    
    # Sample user responses for career assessment
    sample_responses = {
        'answers': [
            {'question_id': 1, 'answer': 'Creative problem-solving'},
            {'question_id': 2, 'answer': 'Beginner (0-1 years)'},
            {'question_id': 3, 'answer': 'Remote work'},
            {'question_id': 4, 'answer': 'Making an impact'},
            {'question_id': 5, 'answer': 'Hands-on practice'},
            {'question_id': 6, 'answer': 'Technical challenges'},
            {'question_id': 7, 'answer': 'Work as part of a team'},
            {'question_id': 10, 'answer': 'Data analysis and statistics'},
            {'question_id': 13, 'answer': 'Individual contributor with minimal oversight'},
            {'question_id': 14, 'answer': 'Extremely important - strict boundaries'}
        ]
    }
    
    recommendations = {}
    
    # 1. Career Assessment Results
    print("Generating career assessment results...")
    career_result = assessment_generator.process_assessment(sample_responses)
    recommendations['career_assessment'] = {
        'user_responses': sample_responses,
        'recommended_career': career_result.get('career_recommendation'),
        'alternatives': career_result.get('alternatives', []),
        'confidence_score': career_result.get('confidence_score', 0)
    }
    
    # 2. Course Recommendations by Career
    print("Generating course recommendations...")
    if career_result.get('status') == 'success':
        career_name = career_result['career_recommendation']['career_name']
        related_courses = career_processor.get_related_courses(career_name, top_n=10)
        
        course_list = []
        for _, course in related_courses.iterrows():
            course_data = {
                'course_id': course['course_id'],
                'title': course['title'],
                'organization': course['organization'],
                'rating': float(course['rating']) if pd.notna(course['rating']) else None,
                'review_count': int(course['review_count']) if pd.notna(course['review_count']) else 0,
                'difficulty': course['difficulty'],
                'course_type': course['course_type'],
                'duration': course['duration'],
                'skills': course['skills'].split() if pd.notna(course['skills']) else [],
                'url': course['url'],
                'is_free': bool(course['is_free']),
                'relevance_score': float(course['similarity_score']) if 'similarity_score' in course else 0.5
            }
            course_list.append(course_data)
        
        recommendations['course_recommendations'] = {
            'career': career_name,
            'total_courses': len(course_list),
            'courses': course_list
        }
    
    # 3. Personalized Recommendations
    if course_recommender:
        print("Generating personalized recommendations...")
        sample_profile = UserProfile(
            user_id="sample_user",
            preferred_skills=["Python", "Data Analysis", "Machine Learning"],
            difficulty_preference="beginner",
            time_availability="moderate",
            budget_preference="mixed",
            learning_style="visual",
            career_goals=["Data Scientist"]
        )
        
        personal_recs = course_recommender.get_personalized_recommendations(sample_profile, top_n=8)
        
        personal_courses = []
        for rec in personal_recs:
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
            personal_courses.append(course_data)
        
        recommendations['personalized_recommendations'] = {
            'user_profile': {
                'preferred_skills': sample_profile.preferred_skills,
                'difficulty_preference': sample_profile.difficulty_preference,
                'career_goals': sample_profile.career_goals
            },
            'total_recommendations': len(personal_courses),
            'recommendations': personal_courses
        }
    
    # 4. Skill-based Recommendations
    if course_recommender:
        print("Generating skill-based recommendations...")
        skill_recs = course_recommender.get_skill_based_recommendations(
            ["Python", "Data Analysis"], top_n=5
        )
        
        skill_courses = []
        for rec in skill_recs:
            course_data = {
                'course_id': rec.course_id,
                'title': rec.title,
                'organization': rec.organization,
                'rating': rec.rating,
                'difficulty': rec.difficulty,
                'skills': rec.skills,
                'relevance_score': rec.relevance_score,
                'match_reasons': rec.match_reasons
            }
            skill_courses.append(course_data)
        
        recommendations['skill_based_recommendations'] = {
            'target_skills': ["Python", "Data Analysis"],
            'total_recommendations': len(skill_courses),
            'recommendations': skill_courses
        }
    
    return recommendations

def main():
    print("Generating recommendation system output for Frontend Engineering team...")
    
    try:
        # Generate recommendations
        recommendations = generate_sample_recommendations()
        
        # Create output structure
        output = {
            'metadata': {
                'system_name': 'Career Platform Recommendation System',
                'version': '1.0.0',
                'generated_at': datetime.now().isoformat(),
                'description': 'ML recommendation system outputs in JSON format',
                'total_recommendation_types': len([k for k in recommendations.keys() if k != 'metadata'])
            },
            'recommendation_outputs': recommendations
        }
        
        # Save to JSON file
        filename = 'PP_MLOps_SayyidahFatimahAzzahra_NabilahShamid_Output.json'
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False, cls=NumpyEncoder)
        
        print(f"✅ Successfully generated {filename}")
        print(f"📊 Contains {len(recommendations)} types of recommendations")
        print("📁 File ready for Frontend Engineering team")
        
        # Print summary
        print("\n📋 Output Summary:")
        for key, value in recommendations.items():
            if isinstance(value, dict):
                if 'total_courses' in value:
                    print(f"   • {key}: {value['total_courses']} courses")
                elif 'total_recommendations' in value:
                    print(f"   • {key}: {value['total_recommendations']} recommendations")
                else:
                    print(f"   • {key}: included")
    
    except Exception as e:
        print(f"❌ Error generating recommendations: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
