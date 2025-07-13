# Coursera Course Data Scraping & Preprocessing

## Dataset Overview

**Source**: Coursera Platform  
**Features**: Course title, skills, organization, rating, review count, difficulty, duration, course type, URL, pricing, course ID  
**Dataset Size**: 1,704 English courses across 4 difficulty levels
**Organizations**: 236 educational institutions and companies

## Scraping Process

### Initial Exploration
The project began by evaluating multiple platforms as scraping source. Initially, Udemy was considered but ultimately dropped. As a course aggregator, ClassCentral appeared promising but dropped due to strict anti-bot configurations and restrictions in robots.txt. Coursera was finally chosen as the scraping target after verifying that its robots.txt doesn't disallow access to the GraphQL endpoint, though initial analysis revealed a significant limitation: standard pagination was capped at 84 pages, restricting access to only ~1,008 courses.

### Solution Implementation
Rather than accepting the pagination constraints, I discovered that course filtering by difficulty levels wasn't reflected in URLs but handled through dynamic AJAX calls. This led to investigating Coursera's network traffic, which revealed GraphQL API endpoints. The breakthrough came when I found that the `/graphql` endpoint returned complete course data in JSON format, bypassing HTML parsing entirely. By implementing difficulty-based scraping with English language filters, I successfully collected 1,750 courses, which after preprocessing yielded the final dataset of 1,704 courses using Python requests with concurrent processing and appropriate rate limiting.

### Technical Flow
1. Built GraphQL payload with difficulty and language filters
2. Made paginated requests to `/graphql` endpoint
3. Extracted course data from JSON responses
4. Applied rate limiting and error handling
5. Removed duplicates based on course ID
6. Dropped entries with missing data for final dataset

## Preprocessing Pipeline

### Processing Steps
1. **Lowercasing**: Normalized text case for all text fields
2. **Noise Removal**: Removed HTML tags, URLs, punctuation, numbers, and extra whitespace
3. **Compound Handling**: Detected and preserved multi-word terms using spaCy POS patterns
4. **Stopword Removal**: Removed common words while preserving technical terms (AI, ML, SQL, etc.)
5. **Lemmatization**: Reduced words to base forms using NLTK Wordnet lemmatizer

### Original
```
title: "Google AI Essentials"
skills: "Prompt Engineering, Generative AI, Artificial Intelligence and Machine Learning (AI/ML), Large Language Modeling, Process Optimization, Productivity Software, Workforce Development, Digital Transformation, Innovation, Technical Writing, Emerging Technologies, Operational Efficiency, Business Solutions, Machine Learning Software, Data Security, Critical Thinking, Analysis, Data Analysis, Data Quality"
```

### After Lowercasing
```
title: "google ai essentials"
skills: "prompt engineering, generative ai, artificial intelligence and machine learning (ai/ml), large language modeling, process optimization, productivity software, workforce development, digital transformation, innovation, technical writing, emerging technologies, operational efficiency, business solutions, machine learning software, data security, critical thinking, analysis, data analysis, data quality"
```

### After Noise Removal (Removed parentheses and commas)
```
title: "google ai essentials"
skills: "prompt engineering generative ai artificial intelligence and machine learning aiml large language modeling process optimization productivity software workforce development digital transformation innovation technical writing emerging technologies operational efficiency business solutions machine learning software data security critical thinking analysis data analysis data quality"
```

### After Compound Handling (Created clear formation of compounds)
```
title: "google ai essentials"
skills: "prompt_engineering_generative ai artificial_intelligence and machine_learning_aiml large_language_modeling process_optimization productivity_software workforce_development digital_transformation innovation technical_writing emerging_technologies operational_efficiency business solutions machine learning_software data_security critical_thinking analysis_data_analysis data_quality"
```

### After Stopword Removal (Removed 'and' from 'artificial intelligence and machine learning')
```
title: "google ai essentials"
skills: "prompt_engineering_generative ai artificial_intelligence machine_learning_aiml large_language_modeling process_optimization productivity_software workforce_development digital_transformation innovation technical_writing emerging_technologies operational_efficiency business solutions machine learning_software data_security critical_thinking analysis_data_analysis data_quality"
```

### After Lemmatization ('essentials' -> 'essential' and 'solutions' -> 'solution')
```
title: "google ai essential"
skills: "prompt_engineering_generative ai artificial_intelligence machine_learning_aiml large_language_modeling process_optimization productivity_software workforce_development digital_transformation innovation technical_writing emerging_technologies operational_efficiency business solution machine learning_software data_security critical_thinking analysis_data_analysis data_quality"
```

## Challenges & Solutions

### Technical Challenges
- **Dynamic Filtering**: Coursera's filters use AJAX calls, not URL parameters
  - *Solution*: Discovered and utilized GraphQL API endpoints
- **Pagination Limits**: Standard scraping limited to ~1,000 courses in total
  - *Solution*: Scraped using GraphQL API to access full dataset
- **Language Filters**: Initially scraped courses in all languages
  - *Solution*: Implemented GraphQL language filters for English-only courses

### Data Quality Issues
- **Compound Terms**: Risk of breaking important technical phrases
  - *Solution*: Implemented pattern-based compound detection using spaCy POS tagging
- **Technical Vocabulary**: Standard stopword removal affected domain terms
  - *Solution*: Created preserve list for technical abbreviations
- **Missing Data**: Some courses lacked ratings or skills information
  - *Solution*: Dropped entries with missing critical data (46 courses removed)

### Ethical Compliance
- **Anti-bot Measures**: Avoided platforms with strict restrictions
  - *Solution*: Chose Coursera's GraphQL API (not restricted in robots.txt)
- **Rate Limiting**: Implemented delays to respect server resources

## How to Use

### Requirements
```bash
pip install requests pandas nltk spacy
python -m spacy download en_core_web_sm
```

### Running the Scripts
1. **Scraping**: Run `sistech_scraping.ipynb` to collect fresh data
2. **Preprocessing**: Run `sistech_preprocessing.ipynb` to clean the data

## Output Files
- `coursera_courses.csv`: Raw scraped data
- `coursera_courses_cleaned.csv`: Preprocessed dataset
- `coursera_courses_cleaned.json`: JSON format for analysis
