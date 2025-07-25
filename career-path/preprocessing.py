import pandas as pd
import numpy as np
import re
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import word_tokenize
import spacy
from collections import Counter, defaultdict
import json
import os

nltk.download('stopwords', quiet=True)
nltk.download('punkt', quiet=True)
nltk.download('wordnet', quiet=True)
nltk.download('omw-1.4', quiet=True)
nltk.download('punkt_tab', quiet=True)

def lowercasing(text):
    return str(text).lower()

def clean_noise(text):
    text = str(text)
    text = re.sub(r'<.*?>', '', text)
    text = re.sub(r'https?://\S+|www\.\S+', '', text)
    text = re.sub(r'#\w+', '', text)
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\d+', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def detect_compound_patterns(df, text_column, min_freq=3):
    try:
        nlp = spacy.load("en_core_web_sm")
    except OSError:
        # Fallback to common tech compounds
        common_compounds = [
            'data science', 'machine learning', 'deep learning', 'natural language',
            'artificial intelligence', 'data analysis', 'data visualization',
            'project management', 'software development', 'web development',
            'data literacy', 'data presentation', 'data ethics', 'data validation',
            'tableau software', 'spreadsheet software', 'search engine',
            'social media', 'email marketing', 'content marketing'
        ]
        return common_compounds, {}
    
    compound_patterns = [
        ['NOUN', 'NOUN'],
        ['ADJ', 'NOUN'],
        ['NOUN', 'NOUN', 'NOUN'],
        ['ADJ', 'NOUN', 'NOUN'],
        ['NOUN', 'ADP', 'NOUN'],
        ['VERB', 'NOUN'],
    ]
    
    detected_sequences = defaultdict(int)
    texts = df[text_column].fillna('').astype(str)
    
    for doc in nlp.pipe(texts, batch_size=50):
        tokens = [token for token in doc if token.is_alpha and not token.is_space]
        
        for pattern in compound_patterns:
            pattern_length = len(pattern)
            
            for i in range(len(tokens) - pattern_length + 1):
                sequence = tokens[i:i + pattern_length]
                
                if [token.pos_ for token in sequence] == pattern:
                    if all(not token.is_stop or token.pos_ == 'ADP' for token in sequence):
                        if 'ADP' in pattern:
                            if sequence[1].text.lower() in ['to', 'of', 'for', 'in']:
                                phrase = ' '.join([token.text.lower() for token in sequence])
                                detected_sequences[phrase] += 1
                        else:
                            phrase = ' '.join([token.text.lower() for token in sequence])
                            detected_sequences[phrase] += 1
    
    compounds = [phrase for phrase, count in detected_sequences.items() if count >= min_freq]
    return compounds, detected_sequences

def preserve_compounds(text, compounds):
    if pd.isna(text):
        return text
    
    tokens = str(text).lower().split()
    sorted_compounds = sorted(compounds, key=len, reverse=True)
    
    for compound in sorted_compounds:
        compound_tokens = compound.split()
        compound_length = len(compound_tokens)
        
        i = 0
        while i <= len(tokens) - compound_length:
            if tokens[i:i + compound_length] == compound_tokens:
                replacement = '_'.join(compound_tokens)
                tokens = tokens[:i] + [replacement] + tokens[i + compound_length:]
                i += 1
            else:
                i += 1
    
    return ' '.join(tokens)

def remove_stopwords(text):
    text = str(text).lower()
    
    preserve_terms = {
        'ai', 'ml', 'ar', 'vr', 'ui', 'ux', 'api', 'aws', 'gcp', 'sql',
        'html', 'css', 'ios', 'android', 'react', 'node', 'vue', 'php',
        'java', 'python', 'r', 'scala', 'go', 'ruby', 'swift', 'kotlin',
        '3d', 'bi', 'etl', 'devops', 'cicd', 'ci', 'cd', 'qa', 'nlp',
        'cnn', 'rnn', 'gan', 'bert', 'gpt', 'llm', 'iot', 'erp', 'crm'
    }
    
    tokens = word_tokenize(text)
    stop_words = set(stopwords.words('english'))
    
    filtered_tokens = []
    for token in tokens:
        if token in preserve_terms or '_' in token:
            filtered_tokens.append(token)
        elif token not in stop_words and token.isalpha():
            if len(token) > 2:
                filtered_tokens.append(token)
    
    return ' '.join(filtered_tokens)

def apply_lemmatization(text):
    text = str(text)
    lemmatizer = WordNetLemmatizer()
    
    words = text.split()
    lemmatized_words = [lemmatizer.lemmatize(word) for word in words]
    
    return ' '.join(lemmatized_words)

def cleaning_pipeline(text, compounds):
    text = lowercasing(text)
    text = clean_noise(text)
    text = preserve_compounds(text, compounds)
    text = remove_stopwords(text)
    text = apply_lemmatization(text)
    return text

def fix_skills_format(skills_text):
    """Remove underscores and format skills properly"""
    if pd.isna(skills_text) or not skills_text:
        return []
    
    skills = str(skills_text).split()
    formatted_skills = []
    
    special_cases = {
        'sql': 'SQL', 'api': 'API', 'ui': 'UI', 'ux': 'UX',
        'ai': 'AI', 'ml': 'ML', 'html': 'HTML', 'css': 'CSS',
        'javascript': 'JavaScript', 'aiml': 'AI/ML', 'nlp': 'NLP'
    }
    
    for skill in skills:
        clean_skill = skill.replace('_', ' ').title()
        if clean_skill.lower() in special_cases:
            clean_skill = special_cases[clean_skill.lower()]
        formatted_skills.append(clean_skill)
    
    return formatted_skills

def convert_duration(duration):
    """Convert duration format"""
    duration_map = {
        'THREE_TO_SIX_MONTHS': '3-6 months',
        'ONE_TO_THREE_MONTHS': '1-3 months',
        'SIX_TO_TWELVE_MONTHS': '6-12 months',
        'ONE_TO_TWO_YEARS': '1-2 years',
        'TWO_TO_FOUR_YEARS': '2-4 years',
        'ONE_TO_FOUR_WEEKS': '1-4 weeks',
        'LESS_THAN_ONE_MONTH': 'Less than 1 month',
        'MORE_THAN_FOUR_YEARS': 'More than 4 years',
        'LESS_THAN_TWO_HOURS': 'Less than 2 hours'
    }
    
    if pd.isna(duration):
        return 'Not specified'
    
    return duration_map.get(str(duration).upper(), str(duration))

def main():
    pd.set_option('display.max_colwidth', None)
    
    print("Loading course data...")
    df = pd.read_csv('data/coursera_courses.csv')
    
    df_original = df.copy()
    
    coursera_df = df[['title', 'organization', 'rating', 'review_count', 
                     'difficulty', 'course_type', 'duration', 'skills']].copy()
    coursera_df = coursera_df.dropna()
    
    print(f"Processing {len(coursera_df)} courses...")
    
    # Detect compounds
    compounds_skills, _ = detect_compound_patterns(coursera_df, 'skills', min_freq=5)
    compounds_title, _ = detect_compound_patterns(coursera_df, 'title', min_freq=3)
    
    # Apply cleaning pipeline
    coursera_df['title_cleaned'] = coursera_df['title'].apply(
        lambda x: cleaning_pipeline(x, compounds_title)
    )
    coursera_df['skills_cleaned'] = coursera_df['skills'].apply(
        lambda x: cleaning_pipeline(x, compounds_skills)
    )
    
    # Prepare final dataset with all columns
    df_final = df[df.index.isin(coursera_df.index)].copy()
    df_final = df_final.drop('language', axis=1)
    df_final = df_final.dropna()
    
    # Add processed versions
    df_final['title_original'] = df_final['title']
    df_final['title'] = coursera_df['title_cleaned']
    df_final['skills_original'] = df_final['skills']
    df_final['skills'] = coursera_df['skills_cleaned']
    
    # Format for API
    df_final['skills_formatted'] = df_final['skills'].apply(fix_skills_format)
    df_final['duration_readable'] = df_final['duration'].apply(convert_duration)
    
    # Save cleaned version (for existing model compatibility)
    df_cleaned = df_final[['title', 'organization', 'rating', 'review_count',
                          'difficulty', 'course_type', 'duration', 'skills',
                          'url', 'is_free', 'course_id']].copy()
    df_cleaned.to_csv('data/coursera_courses_cleaned.csv', index=False)
    
    # Save processed version for career-path
    output_dir = 'data'
    os.makedirs(output_dir, exist_ok=True)
    
    # CSV version for career-path
    df_processed = df_final[['course_id', 'title_original', 'title', 'organization',
                            'rating', 'review_count', 'difficulty', 'course_type',
                            'duration_readable', 'duration', 'skills_formatted', 
                            'skills', 'url', 'is_free']].copy()
    
    # Convert skills list to string for CSV compatibility
    df_csv = df_processed.copy()
    df_csv['skills_formatted'] = df_csv['skills_formatted'].apply(
        lambda x: ', '.join(x) if isinstance(x, list) else str(x)
    )
    
    df_csv.to_csv(f'{output_dir}/coursera_courses_processed.csv', index=False)
    
    # JSON version
    records = []
    for _, row in df_processed.iterrows():
        record = row.to_dict()
        # Fix numpy types
        for key, value in record.items():
            if isinstance(value, np.ndarray) or (hasattr(value, '__len__') and not isinstance(value, str)):
                if len(value) == 0 or (hasattr(value, 'isna') and value.isna().all()):
                    record[key] = None
                else:
                    continue
            elif pd.isna(value):
                record[key] = None
            elif isinstance(value, (np.integer, np.int64)):
                record[key] = int(value)
            elif isinstance(value, (np.floating, np.float64)):
                record[key] = float(value)
            elif isinstance(value, np.bool_):
                record[key] = bool(value)
        records.append(record)
    
    with open(f'{output_dir}/coursera_courses_processed.json', 'w') as f:
        json.dump({
            'metadata': {
                'total_courses': len(records),
                'processed_at': pd.Timestamp.now().isoformat()
            },
            'courses': records
        }, f, indent=2)
    
    print(f"✓ Saved {len(df_final)} courses")
    print("✓ Fixed skills formatting (removed underscores)")
    print("✓ Converted duration to readable format")
    print("✓ Preserved original titles")
    print("✓ Generated files for career-path folder")

if __name__ == "__main__":
    main()
