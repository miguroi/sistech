import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import KMeans
from collections import Counter
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from typing import Dict, List, Tuple
from dataclasses import dataclass

@dataclass
class CareerMatch:
    career_id: str
    career_name: str
    match_score: float
    matching_skills: List[str]

COMMON_STOPWORDS = {'and', 'the', 'of', 'in', 'for', 'to', 'a', 'an', 'is', 'are', 'was', 'were'}

def create_tfidf_vectorizer(max_features=1000, ngram_range=(1, 2), min_df=1):
    """Create TF-IDF vectorizer"""
    return TfidfVectorizer(
        stop_words='english',
        max_features=max_features,
        ngram_range=ngram_range,
        min_df=min_df
    )

def extract_tokens(text):
    """Extract tokens from text"""
    tokens = word_tokenize(text.lower())
    stop_words = set(stopwords.words('english'))
    return [
        token for token in tokens 
        if len(token) > 2 and token not in stop_words and token.isalpha()
    ]

def get_top_frequent_words(text, top_n=20):
    """Get most frequent words from text"""
    tokens = extract_tokens(text)
    word_freq = Counter(tokens)
    return [word for word, freq in word_freq.most_common(top_n)]

def compute_text_similarities(query_text, target_texts, vectorizer_params=None):
    """Compute cosine similarities between query and target texts"""
    if vectorizer_params is None:
        vectorizer_params = {}
    
    all_texts = [query_text] + list(target_texts)
    
    # Handle edge cases
    if not all_texts or all(not text.strip() for text in all_texts):
        return np.zeros(len(target_texts)), None
    
    # Filter out empty texts and add fallback content
    processed_texts = []
    for text in all_texts:
        if text and text.strip():
            processed_texts.append(text)
        else:
            processed_texts.append("placeholder content")
    
    try:
        vectorizer = create_tfidf_vectorizer(**vectorizer_params)
        tfidf_matrix = vectorizer.fit_transform(processed_texts)
        
        query_vector = tfidf_matrix[0:1]
        target_vectors = tfidf_matrix[1:]
        similarities = cosine_similarity(query_vector, target_vectors).flatten()
        
        return similarities, vectorizer
    except ValueError as e:
        # Handle empty vocabulary or other TF-IDF issues
        return np.zeros(len(target_texts)), None

def create_kmeans_clustering(texts, n_clusters=None, vectorizer_params=None):
    """Perform K-means clustering on texts"""
    if vectorizer_params is None:
        vectorizer_params = {'max_features': 500, 'min_df': 2}
    
    vectorizer = create_tfidf_vectorizer(**vectorizer_params)
    tfidf_matrix = vectorizer.fit_transform(texts)
    
    if n_clusters is None:
        n_clusters = min(8, max(2, min(3, len(texts))))
    
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    cluster_labels = kmeans.fit_predict(tfidf_matrix)
    
    return cluster_labels, kmeans, vectorizer

class CareerProcessor:
    def __init__(self, career_data_path: str, courses_data_path: str = None):
        self.career_df = pd.read_csv(career_data_path)
        if courses_data_path:
            self.courses_df = pd.read_csv(courses_data_path)
        else:
            # Create empty DataFrame with expected columns
            self.courses_df = pd.DataFrame(columns=[
                'course_id', 'title', 'organization', 'rating', 'review_count',
                'difficulty', 'course_type', 'duration', 'skills', 'url', 'is_free'
            ])
        self.career_skills_cache = {}
        self.course_recommender = None
        
    def initialize_course_recommender(self, courses_data_path: str = None):
        """Initialize course recommender with course data"""
        try:
            from course_recommender import CourseRecommender
            if courses_data_path:
                self.courses_df = pd.read_csv(courses_data_path)
            self.course_recommender = CourseRecommender(
                courses_data_path=courses_data_path,
                career_processor=self
            )
            return True
        except Exception as e:
            print(f"Warning: Could not initialize course recommender: {e}")
            return False
        
    def extract_skills_from_qa(self, career_role: str) -> List[str]:
        """Extract skills from career Q&A using frequency analysis"""
        if career_role in self.career_skills_cache:
            return self.career_skills_cache[career_role]
            
        career_data = self.career_df[self.career_df['role'] == career_role]
        all_answers = ' '.join(career_data['answer'].values)
        
        meaningful_tokens = extract_tokens(all_answers)
        
        # Get most frequent terms as potential skills
        word_freq = Counter(meaningful_tokens)
        top_skills = [word for word, freq in word_freq.most_common(20)]
        
        self.career_skills_cache[career_role] = top_skills
        return top_skills
    
    def extract_skills_from_courses(self, career_role: str) -> List[str]:
        """Extract skills from courses related to this career"""
        related_courses = self.get_related_courses(career_role, top_n=30)
        
        if related_courses.empty:
            return []
            
        # Combine all skills from related courses
        all_course_skills = ' '.join(related_courses['skills'].fillna(''))
        
        # Split by common delimiters and clean
        skills_list = []
        for skill_text in all_course_skills.split():
            if len(skill_text) > 2:
                skills_list.append(skill_text.strip().lower())
        
        # Return most frequent skills
        skill_freq = Counter(skills_list)
        return [skill for skill, freq in skill_freq.most_common(15)]
    
    def get_related_courses(self, career_role: str, top_n: int = 20) -> pd.DataFrame:
        """Find courses most relevant to a career using TF-IDF similarity"""
        career_text = self._get_career_description(career_role)
        
        if not career_text:
            return pd.DataFrame()
            
        # Prepare course texts
        course_texts = (self.courses_df['title'] + ' ' + 
                       self.courses_df['skills'].fillna('')).values
        
        vectorizer_params = {'max_features': 2000, 'min_df': 2}
        similarities, _ = compute_text_similarities(career_text, course_texts, vectorizer_params)
        
        # Get top matching courses
        top_indices = similarities.argsort()[-top_n:][::-1]
        related_courses = self.courses_df.iloc[top_indices].copy()
        related_courses['similarity_score'] = similarities[top_indices]
        
        return related_courses.sort_values('similarity_score', ascending=False)
        
    def _get_career_description(self, career_role: str) -> str:
        """Combine all Q&A content for a career"""
        career_data = self.career_df[self.career_df['role'] == career_role]
        questions = ' '.join(career_data['question'].values)
        answers = ' '.join(career_data['answer'].values)
        return f"{questions} {answers}"
    
    def assess_career_match(self, user_responses: Dict) -> List[CareerMatch]:
        """Match user responses to careers using content similarity"""
        user_text = self._combine_user_responses(user_responses)
        
        # Get all unique careers
        careers = self.career_df['role'].unique()
        career_texts = [self._get_career_description(career) for career in careers]
        
        # Use the available vectorizer function for consistency
        vectorizer_params = {'max_features': 1000, 'ngram_range': (1, 2)}
        similarities, vectorizer = compute_text_similarities(user_text, career_texts, vectorizer_params)
        
        # Create matches with extracted skills
        matches = []
        feature_names = vectorizer.get_feature_names_out()
        
        # Re-transform texts to get individual vectors for skill extraction
        all_texts = [user_text] + career_texts
        tfidf_matrix = vectorizer.transform(all_texts)
        career_vectors = tfidf_matrix[1:]
        
        for i, career in enumerate(careers):
            # Get top features that contributed to this match
            career_vector = career_vectors[i]
            top_feature_indices = career_vector.toarray().argsort()[0][-10:]
            matching_skills = [feature_names[idx] for idx in top_feature_indices]
            
            matches.append(CareerMatch(
                career_id=career.lower().replace(' ', '_'),
                career_name=career,
                match_score=similarities[i],
                matching_skills=matching_skills
            ))
            
        return sorted(matches, key=lambda x: x.match_score, reverse=True)
    
    def _combine_user_responses(self, responses: Dict) -> str:
        """Combine user assessment responses into single text"""
        combined_text = []
        for answer_data in responses.get('answers', []):
            answer = str(answer_data.get('answer', '')).strip()
            if answer:
                combined_text.append(answer)
        return ' '.join(combined_text)
    
    def get_dynamic_career_category(self, career_name: str) -> str:
        """Dynamically discover career category using pure data-driven clustering"""
        # Cache cluster assignments to avoid recomputing
        if not hasattr(self, '_career_clusters'):
            self._compute_career_clusters()
            
        # Find this career in the clusters
        for cluster_id, careers_in_cluster in self._career_clusters.items():
            if career_name in careers_in_cluster:
                return self._generate_cluster_label(cluster_id, careers_in_cluster)
                
        return "Miscellaneous"
    
    def _compute_career_clusters(self):
        """Use unsupervised clustering to group similar careers"""
        careers = self.career_df['role'].unique()
        career_texts = [self._get_career_description(career) for career in careers]
        
        vectorizer_params = {'max_features': 500, 'min_df': 2}
        cluster_labels, kmeans, vectorizer = create_kmeans_clustering(career_texts, None, vectorizer_params)
        
        # Group careers by cluster
        self._career_clusters = {}
        self._cluster_centers = kmeans.cluster_centers_
        self._vectorizer = vectorizer
        
        for i, career in enumerate(careers):
            cluster_id = cluster_labels[i]
            if cluster_id not in self._career_clusters:
                self._career_clusters[cluster_id] = []
            self._career_clusters[cluster_id].append(career)
    
    def _generate_cluster_label(self, cluster_id: int, careers_in_cluster: List[str]) -> str:
        """Generate meaningful label purely from data"""
        # Extract the most common meaningful words from career names in this cluster
        all_words = []
        for career in careers_in_cluster:
            # Split career name and filter meaningful words
            words = [word.lower() for word in career.split() 
                    if len(word) > 2 and word.lower() not in COMMON_STOPWORDS]
            all_words.extend(words)
        
        # Get most frequent words
        word_freq = Counter(all_words)
        most_common_words = word_freq.most_common(3)
        
        if most_common_words:
            # Use the most frequent word as base, but make it more descriptive
            primary_word = most_common_words[0][0]
            
            # If multiple words have similar frequency, combine them
            if len(most_common_words) > 1 and most_common_words[0][1] == most_common_words[1][1]:
                return f"{primary_word.title()} & {most_common_words[1][0].title()}"
            else:
                return f"{primary_word.title()} Careers"
        
        # Fallback: use cluster characteristics from TF-IDF
        cluster_center = self._cluster_centers[cluster_id]
        feature_names = self._vectorizer.get_feature_names_out()
        top_feature_idx = cluster_center.argmax()
        top_feature = feature_names[top_feature_idx]
        
        return f"{top_feature.title()}-Related"
    
    def get_course_recommendations(self, career_role: str, top_n: int = 20, 
                                 difficulty_filter: str = None):
        """Get course recommendations for a specific career role"""
        if not self.course_recommender:
            # Fallback to basic course matching if recommender not available
            return self.get_related_courses(career_role, top_n)
            
        return self.course_recommender.get_course_recommendations_by_career(
            career_role, top_n, difficulty_filter
        )
    
    def get_personalized_course_recommendations(self, user_profile, top_n: int = 15):
        """Get personalized course recommendations based on user profile"""
        if not self.course_recommender:
            return []
            
        return self.course_recommender.get_personalized_recommendations(user_profile, top_n)
    
    def get_skill_based_courses(self, skills: List[str], top_n: int = 20):
        """Get courses based on specific skills"""
        if not self.course_recommender:
            return []
            
        return self.course_recommender.get_skill_based_recommendations(skills, top_n)
    
    def get_learning_path_for_career(self, career_role: str, skill_level: str = 'beginner'):
        """Generate a learning path for a specific career"""
        if not self.course_recommender:
            return {'path': [], 'total_duration': '0 weeks', 'total_courses': 0}
            
        return self.course_recommender.get_learning_path(career_role, skill_level)
    
    def get_trending_courses(self, top_n: int = 20, min_rating: float = 4.0):
        """Get trending courses"""
        if not self.course_recommender:
            return []
            
        return self.course_recommender.get_trending_courses(top_n, min_rating)
