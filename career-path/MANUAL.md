# Career Path Recommendation System

ML-powered career recommendation system with course suggestions and assessments.

## Quick Setup

### 1. Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### 3. Run Data Preprocessing (Required First Step)
```bash
python preprocessing.py
```
This processes `data/coursera_courses.csv` and generates cleaned data files in `data/` folder.

### 4. Start System
```bash
# API Server
cd api && python api_server.py
# Available at: http://localhost:8000

# OR Generate Sample Output
python generate_recommendation_output.py
```

## System Flow

1. **preprocessing.py** → Cleans raw course data → Saves to `data/` folder
2. **Other scripts** → Use processed data from `data/` folder
3. **API** → Serves recommendations via FastAPI

## Key Files
- `preprocessing.py` - Data cleaning pipeline (run first)
- `api/api_server.py` - FastAPI server
- `course_recommender.py` - Recommendation engine
- `data/` - All data files (input and processed)

## Troubleshooting
- **Import errors**: Activate venv, reinstall requirements
- **Data not found**: Run `preprocessing.py` first
- **SpaCy errors**: `python -m spacy download en_core_web_sm`

**Always run `preprocessing.py` before using other components.**
