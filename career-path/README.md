# MLOps Final Project: Course & Certification Recommendation System

This repository contains the final project for the Machine Learning Operations (MLOps) module of the Sisters in Tech (SISTECH) 2025 program by RISTEK Fasilkom UI. This project involves building an end-to-end machine learning-based recommendation system for 'Course & Certification'. The system encompasses data scraping, text cleaning, data transformation, similarity calculation, and exposes recommendations through a local REST API.

## Table of Contents
1.  [Project Overview](#project-overview)
2.  [Features](#features)
3.  [Data Sources and Structure](#data-sources-and-structure)
4.  [Project Workflow](#project-workflow)
5.  [API Endpoints](#api-endpoints)
6.  [Deliverables](#deliverables)
7.  [How to Run the Project](#how-to-run-the-project)

---

## 1. Project Overview

This final project is the culmination of the Machine Learning Ops module that participants have undergone. Our team developed an end-to-end machine learning-based recommendation system specifically for courses and certifications. The core functionality includes processing raw data to derive meaningful insights and providing relevant recommendations via a local API. The project is designed to represent a real-world workflow in developing text-based machine learning solutions.

## 2. Features

Our recommendation system offers the following functionalities through its API endpoints:

* **Health Check:** Verifies the API's operational status.
* **Career Management & Assessment:**
    * Retrieve all available careers with categories for dropdown selection.
    * Process user assessment answers to provide personalized career recommendations and relevant course suggestions.
* **Learning Roadmap & Paths:**
    * Generate a structured learning roadmap for a specific career, including checkpoints, estimated durations, and derived skills.
    * Generate a structured learning path for a specific career and skill level (beginner, intermediate, advanced).
* **Course Recommendations:**
    * Get courses filtered by career and optional difficulty.
    * Filter and sort courses based on various criteria such as difficulty, course type, organization, free status, minimum rating, and sorting preferences.
    * Get personalized course recommendations based on user profile, including preferred skills, difficulty preference, time availability, budget preference, learning style, and career goals.
    * Get trending courses based on ratings and popularity.
* **Skill-based Course Recommendation:** Get course recommendations based on specific skills input by the user.

## 3. Data Sources and Structure

Our system utilizes two main datasets:

* **Coursera Dataset:** Contains 1,704 courses.
    * **Source:** `https://www.coursera.org/courses`.
    * **Fields:** `title` (cleaned course title) , `organization` (provider like Google, IBM, etc.) , `rating` (average rating as float) , `review_count` (number of reviews as int) , `difficulty` (Beginner/Intermediate/Advanced) , `course_type` (Professional Certificate, Course, Specialization) , `duration` (e.g., THREE_TO_SIX_MONTHS, ONE_TO_THREE_MONTHS) , `skills` (processed skills string) , `url` (Coursera URL path) , `is_free` (Boolean) , `course_id` (unique identifier).

* **Career Guidance Dataset:** Contains 1,620 rows, combining 54 career roles.
    * **Source:** `https://huggingface.co/datasets/Pradeep016/career-guidance-qa-dataset`.
    * **Fields:** `Role` (the name of the career role, e.g., Data Scientist, Software Engineer, Product Manager) , `Question` (the question related to the career role, e.g., "What are the required skills for a Data Scientist?") , `Answer` (the answer to the question, providing relevant information about the career role).

## 4. Project Workflow

The development of this recommendation system followed these stages:

1.  **Data Scraping:** Data was retrieved from public sources using web scraping techniques. The collected data was adjusted to fit the needs of the developed recommendation system.
2.  **Data Processing:** Data cleaning and standardization were performed to prepare data for further processes, including text normalization and removal of irrelevant elements.
3.  **Text Vectorization:** Text-based data was converted into numerical representations (vectors) for computational processing, using adaptable techniques like TF-IDF or Word2Vec.
4.  **Similarity Mapping:** Similarity between data points was measured based on the generated vectors to determine relationships or relevance among analyzed items.
5.  **Recommendation Modelling:** The recommendation system's logic was developed based on the calculated similarity results, for example, by displaying the most relevant items or creating specific recommendation rules.
6.  **REST API Development (Local - Mandatory):** A simple REST API was created using tools like Flask or FastAPI to serve the recommendation results locally, capable of receiving input and returning functional recommendation output. Deployment to external environments is optional and does not add to the assessment score , but is encouraged for additional valuable experience.
7.  **Documentation & Presentation:** A final presentation in slide format (.pdf) was created as a comprehensive project report, summarizing the process from beginning to end.

## 5. API Endpoints

The API is built using FastAPI and can be accessed locally.

* **API Base URL (Deployed):** `https://career-path-api.onrender.com/` 
* **API Swagger Documentation:** `https://career-path-api.onrender.com/docs` 
* **API Redocs Documentation:** `https://career-path-api.onrender.com/redocs`
* **API Postman Documentation:** `https://www.postman.com/arhaz/sistech/collection/ec8507d/api-documentation` 

Here are the main API endpoints:

* `GET /`
    * **Purpose:** Health check endpoint to verify API status.
* `GET /api/careers`
    * **Purpose:** Get all available careers with categories for dropdown selection.
* `GET /api/assessment/questions`
    * **Purpose:** Get all assessment questions for career evaluation.
* `POST /api/assess-career`
    * **Purpose:** Process career assessment and return personalized career recommendation.
    * **Request Body Example:**
        ```json
        {
          "user_id": "user123",
          "answers": [
            { "question_id": 1, "answer": "Creative problem-solving" },
            { "question_id": 2, "answer": "Beginner (0-1 years)" }
            // ... (include all answered questions as per the provided example in the documentation)
          ]
        }
        ```
* `GET /api/roadmap/{career_id}`
    * **Purpose:** Generate a structured learning roadmap for a specific career.
    * **Parameters:** `career_id` (path parameter, e.g., "data scientist").
* `GET /api/learning-path/{career_id}`
    * **Purpose:** Generate a structured learning path for a specific career.
    * **Parameters:** `career_id` (path parameter) , `skill_level` (query, optional: "beginner", "intermediate", or "advanced", default: "beginner").
* `GET /api/courses/career/{career_id}`
    * **Purpose:** Get courses filtered by career and optional difficulty.
    * **Parameters:** `career_id` (path parameter) , `difficulty` (query, optional) , `limit` (query) , `offset` (query).
* `GET /api/courses/filter`
    * **Purpose:** Filter and sort courses with various criteria.
    * **Parameters:** `difficulty` , `course_type` , `organization` , `is_free` , `min_rating` , `sort_by` (`rating`, `review count`, or `relevance`) , `sort_order` (`asc` or `desc`) , `limit` , `offset`.
* `POST /api/courses/personalized`
    * **Purpose:** Get personalized course recommendations based on user profile.
    * **Request Body Example:**
        ```json
        {
          "user_id": "user123",
          "preferred_skills": ["Python", "Machine Learning", "Statistics"],
          "difficulty_preference": "intermediate",
          "time_availability": "moderate",
          "budget_preference": "mixed",
          "learning_style": "visual",
          "career_goals": ["Data Scientist", "AI Engineer"]
        }
        ```
* `POST /api/courses/skills`
    * **Purpose:** Get course recommendations based on specific skills.
    * **Request Body Example:**
        ```json
        {
          "skills": ["React", "JavaScript", "Node.js"],
          "limit": 2
        }
        ```
* `GET /api/courses/trending`
    * **Purpose:** Get trending courses based on ratings and popularity.
    * **Parameters:** `min_rating` (0-5, default: 4.0) , `limit` (1-100, default: 20).

## 6. Deliverables

As part of the final project, the following deliverables are included in the `.zip` submission:

* **Source Code:** Python scripts or notebooks for all stages of work (scraping, preprocessing, vectorization, similarity, recommendation), and the REST API that can be run locally.
* **Final Report (PDF):** The final report in slide presentation format (.pdf). It contains a summary of the work process, final reflection, and a link to this GitHub repository. (Filename: `PP_MLOps_[FullName1]_[FullName2]_Report.pdf`) 
* **GitHub Repository:** A neat repository containing all project code and files. It includes a `README.md` that explains the folder structure and how to run the project.
* **Model Output File (JSON):** The output file of the model used in the recommendation system in `.json` format. This file contains ready-to-use recommendation results and will be provided to the Front-End Engineering team. (Filename: `PP_MLOps_[FullName1]_[FullName2]_Output.json`) 

## 7. How to Run the Project

Follow these steps to set up and run the project locally:

### Prerequisites

* Python 3.x (Ensure you have a recent version, e.g., 3.8+)
* `pip` (Python package installer)
* `virtualenv` (recommended for environment isolation)

### Installation

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/miguroi/sistech.git](https://github.com/miguroi/sistech.git)
    cd sistech/career-path # Navigate into your project directory
    ```
2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    # On Windows:
    .\venv\Scripts\activate
    # On macOS/Linux:
    source venv/bin/activate
    ```
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
### Running the API

1.  **Prepare the data:**
    * "Ensure all necessary data files (e.g., `coursera_courses.json`, `career_guidance.json`) are present in the `data/` directory located within `sistech/career-path/data`."

2.  **Start the FastAPI application:**
    ```bash
    uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
    ```

    The API will then be accessible at `http://127.0.0.1:8000` or `http://localhost:8000`. You can access the **Swagger UI documentation** for testing the endpoints at `http://localhost:8000/docs`.

### Running Individual Scripts (Optional - for data processing/model generation)

* **Example for Data Scraping:**
    ```bash
    python scripts/scrape_data.py
    ```
* **Example for Data Preprocessing:**
    ```bash
    python scripts/preprocess_data.py
    ```
* **Example for Model/Similarity Generation:**
    ```bash
    python scripts/generate_model.py
    ```
---
