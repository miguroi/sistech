# Coursera Course Data Scraping & Preprocessing

## Dataset Overview

**Source**: Coursera Platform  
**Features**: Course title, skills, organization, rating, review count, difficulty, duration, course type, URL, pricing, course ID  
**Dataset Size**: 1,749 English courses across 4 difficulty levels (Beginner: 600, Intermediate: 500, Advanced: 400, Mixed: 250)  
**Organizations**: 236 educational institutions and companies

## Scraping Process

### Initial Exploration
The project began by evaluating multiple platforms as scraping source. Initially, Udemy was considered but ultimately dropper. As a course aggregator, ClassCentral appeared promising but dropped due to strict anti-bot configurations and restrictions in robots.txt. Coursera was finally chosen as the scraping target after verifying that its robots.txt doesn't disallow access to the GraphQL endpoint, though initial analysis revealed a significant limitation: standard pagination was capped at 84 pages, restricting access to only ~1,008 courses.

### Solution Implementation
Rather than accepting the pagination constraints, I discovered that course filtering by difficulty levels wasn't reflected in URLs but handled through dynamic AJAX calls. This led to investigating Coursera's network traffic, which revealed GraphQL API endpoints. The breakthrough came when I found that the `/graphql` endpoint returned complete course data in JSON format, bypassing HTML parsing entirely. By implementing difficulty-based scraping with English language filters, I successfully generated the final dataset of 1,750 courses sample using Python requests with concurrent processing and appropriate rate limiting.

### Technical Flow
1. Built GraphQL payload with difficulty and language filters
2. Made paginated requests to `/graphql` endpoint
3. Extracted course data from JSON responses
4. Applied rate limiting and error handling
5. Removed duplicates based on course ID

## Preprocessing Pipeline

### Processing Steps
1. **Lowercasing**: Normalized text case
2. **Noise Removal**: Removed HTML tags, URLs, punctuation, numbers
3. **Compound Handling**: Preserved multi-word terms (e.g., "machine learning" → "machine_learning")
4. **Stopword Removal**: Removed common words while preserving technical terms (AI, ML, SQL, etc.)
5. **Lemmatization**: Reduced words to base forms

### Original
```
title: "Google CyberSecurity"
skills: "Threat Modeling, Network Security, Incident Response, Vulnerability Management, Computer Security Incident Management..."
```

### After Lowercasing
```
title: "google cybersecurity"
skills: "threat modeling, network security, incident response, vulnerability management, computer security incident management..."
```

### After Noise Removal
```
title: "google cybersecurity"
skills: "threat modeling network security incident response vulnerability management computer security incident management"
```

### After Compound Handling
```
title: "google cybersecurity"
skills: "threat_modeling network_security_incident_response vulnerability_management computer_security_incident_management"
```

### After Stopword Removal
```
title: "google cybersecurity"
skills: "threat_modeling network_security_incident_response vulnerability_management computer_security_incident_management"
```

### After Lemmatization
```
title: "google cybersecurity"
skills: "threat_modeling network_security_incident_response vulnerability_management computer_security_incident_management"
```

## Challenges & Solutions

### Technical Challenges
- **Dynamic Filtering**: Coursera's filters use AJAX calls, not URL parameters
  - *Solution*: Discovered and utilized GraphQL API endpoints
- **Pagination Limits**: Standard scraping limited to ~1,000 courses in total
  - *Solution*: Scraped using GraphQL API to access full dataset
- **Language Filters**: Initially scraped full courses, not only just English course
  - *Solution*: Fixed the scraping notebook to use GraphQL language filters

### Data Quality Issues
- **Compound Terms**: Risk of breaking important technical phrases
  - *Solution*: Implemented pattern-based compound detection using spaCy
- **Technical Vocabulary**: Standard stopword removal affected domain terms
  - *Solution*: Created preserve list for technical abbreviations

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
