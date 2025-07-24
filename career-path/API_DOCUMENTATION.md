# Career Path API Documentation

## Overview

Career Path provides intelligent career guidance through assessment, course recommendations, and personalized learning paths.

This API is built with FastAPI and it offers comprehensive endpoints for career exploration and skill development.

**Base URL:** `https://career-path-api.onrender.com`

## Authentication

Currently, no authentication is required for API access.

## Interactive Documentation

- **Swagger UI:** `https://career-path-api.onrender.com/docs`
- **ReDoc:** `https://career-path-api.onrender.com/redoc`

---

## Endpoints

### Health Check

#### `GET /`
**Description:** Health check endpoint to verify API status.

**Response:**
```json
{
  "message": "Career Platform API is running",
  "status": "healthy",
  "timestamp": "2025-01-24T10:30:00.000Z"
}
```

---

### Career Management

#### `GET /api/careers`
**Description:** Get all available careers with categories for dropdown selection.

**Response:**
```json
{
  "status": "success",
  "careers": [
    {
      "career_id": "data_scientist",
      "career_name": "Data Scientist",
      "category": "Technology"
    }
  ],
  "total_careers": 150
}
```

**Error Responses:**
- `500`: Service temporarily unavailable

---

### Career Assessment

#### `GET /api/assessment/questions`
**Description:** Get all assessment questions for career evaluation.

**Response:**
```json
{
  "status": "success",
  "questions": [
    {
      "question_id": 1,
      "question": "What type of work environment do you prefer?",
      "options": ["Remote", "Office", "Hybrid", "Field work"]
    }
  ],
  "total_questions": 20
}
```

#### `POST /api/assess-career`
**Description:** Process career assessment and return personalized career recommendation.

**Request Body:**
```json
{
  "user_id": "user123",
  "answers": [
    {
      "question_id": 1,
      "answer": "Remote"
    },
    {
      "question_id": 2,
      "answer": "Problem-solving"
    }
  ]
}
```

**Response:**
```json
{
  "status": "success",
  "user_id": "user123",
  "recommended_careers": [
    {
      "career_name": "Data Scientist",
      "match_score": 0.85,
      "reasons": ["Strong analytical skills", "Prefers remote work"]
    }
  ],
  "assessment_summary": {
    "questions_answered": 15,
    "completion_percentage": 75
  }
}
```

**Error Responses:**
- `400`: Incomplete assessment (requires at least 5 answers)
- `500`: Assessment processing failed

---

### Learning Roadmaps

#### `GET /api/roadmap/{career_id}`
**Description:** Generate a structured learning roadmap for a specific career.

**Parameters:**
- `career_id` (path): Career identifier (e.g., "data_scientist")

**Response:**
```json
{
  "status": "success",
  "career_info": {
    "career_id": "data_scientist",
    "career_name": "Data Scientist",
    "description": "Analyze complex data to help organizations make decisions...",
    "qa_count": 25
  },
  "roadmap": {
    "total_checkpoints": 8,
    "estimated_duration": "12-18 months",
    "checkpoints": [
      {
        "checkpoint_id": 1,
        "title": "Foundation in Statistics and Mathematics",
        "description": "Build statistical thinking and mathematical foundations",
        "skills_derived": ["Statistics", "Linear Algebra", "Calculus"],
        "estimated_time": "2-3 months",
        "is_completed": false,
        "skills_source": "career requirements"
      }
    ]
  }
}
```

**Error Responses:**
- `404`: Career not found
- `500`: Roadmap generation failed

---

### Course Recommendations

#### `GET /api/courses/career/{career_id}`
**Description:** Get courses filtered by career and optional difficulty.

**Parameters:**
- `career_id` (path): Career identifier
- `difficulty` (query, optional): "beginner", "intermediate", or "advanced"
- `limit` (query): Number of courses to return (1-100, default: 20)
- `offset` (query): Pagination offset (default: 0)

**Response:**
```json
{
  "status": "success",
  "career_info": {
    "career_id": "data_scientist",
    "career_name": "Data Scientist"
  },
  "courses": [
    {
      "course_id": "course123",
      "title": "Introduction to Data Science",
      "organization": "Coursera",
      "rating": 4.5,
      "review_count": 12500,
      "difficulty": "Beginner",
      "course_type": "Course",
      "duration": "6 weeks",
      "skills": ["Python", "Statistics", "Data Analysis"],
      "url": "https://coursera.org/course123",
      "is_free": false,
      "relevance_score": 0.92
    }
  ],
  "pagination": {
    "total_courses": 150,
    "current_page": 1,
    "total_pages": 8,
    "has_next": true
  }
}
```

#### `GET /api/courses/filter`
**Description:** Filter and sort courses with various criteria.

**Query Parameters:**
- `difficulty`: "beginner", "intermediate", or "advanced"
- `course_type`: Course type filter
- `organization`: Organization name filter
- `is_free`: Boolean for free courses only
- `min_rating`: Minimum rating (0-5)
- `sort_by`: "rating", "review_count", or "relevance"
- `sort_order`: "asc" or "desc"
- `limit`: Results limit (1-100, default: 20)
- `offset`: Pagination offset

**Response:** Similar to career-based course endpoint with applied filters.

#### `POST /api/courses/personalized`
**Description:** Get personalized course recommendations based on user profile.

**Request Body:**
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

**Response:**
```json
{
  "status": "success",
  "user_profile": {
    "user_id": "user123",
    "career_goals": ["Data Scientist", "AI Engineer"],
    "difficulty_preference": "intermediate"
  },
  "recommendations": [
    {
      "course_id": "course456",
      "title": "Machine Learning Specialization",
      "organization": "Stanford",
      "rating": 4.8,
      "review_count": 8900,
      "difficulty": "Intermediate",
      "course_type": "Specialization",
      "duration": "3 months",
      "skills": ["Machine Learning", "Python", "TensorFlow"],
      "url": "https://coursera.org/course456",
      "is_free": false,
      "relevance_score": 0.95,
      "match_reasons": [
        "Matches preferred skill: Machine Learning",
        "Aligns with career goal: Data Scientist",
        "Appropriate difficulty level"
      ]
    }
  ],
  "total_recommendations": 15
}
```

#### `POST /api/courses/skills`
**Description:** Get course recommendations based on specific skills.

**Request Body:**
```json
{
  "skills": ["React", "JavaScript", "Node.js"],
  "limit": 10
}
```

**Response:**
```json
{
  "status": "success",
  "target_skills": ["React", "JavaScript", "Node.js"],
  "recommendations": [
    {
      "course_id": "course789",
      "title": "React - The Complete Guide",
      "organization": "Udemy",
      "rating": 4.6,
      "review_count": 15600,
      "difficulty": "Intermediate",
      "course_type": "Course",
      "duration": "49 hours",
      "skills": ["React", "JavaScript", "Redux"],
      "url": "https://udemy.com/course789",
      "is_free": false,
      "relevance_score": 0.88,
      "match_reasons": [
        "Direct match: React",
        "Direct match: JavaScript",
        "Related skill: Redux"
      ]
    }
  ],
  "total_recommendations": 10
}
```

#### `GET /api/courses/trending`
**Description:** Get trending courses based on ratings and popularity.

**Query Parameters:**
- `min_rating`: Minimum rating filter (0-5, default: 4.0)
- `limit`: Number of courses (1-100, default: 20)

**Response:**
```json
{
  "status": "success",
  "filters": {
    "min_rating": 4.0,
    "limit": 20
  },
  "recommendations": [
    {
      "course_id": "trending123",
      "title": "Complete Python Bootcamp",
      "organization": "Udemy",
      "rating": 4.7,
      "review_count": 45000,
      "difficulty": "Beginner",
      "course_type": "Course",
      "duration": "22 hours",
      "skills": ["Python", "Programming", "Web Development"],
      "url": "https://udemy.com/trending123",
      "is_free": false,
      "relevance_score": 0.91,
      "match_reasons": ["High rating", "Popular course", "Comprehensive content"]
    }
  ],
  "total_recommendations": 20
}
```

---

### Learning Paths

#### `GET /api/learning-path/{career_id}`
**Description:** Generate a structured learning path for a specific career.

**Parameters:**
- `career_id` (path): Career identifier
- `skill_level` (query): "beginner", "intermediate", or "advanced" (default: "beginner")

**Response:**
```json
{
  "status": "success",
  "career_info": {
    "career_id": "web_developer",
    "career_name": "Web Developer",
    "skill_level": "beginner"
  },
  "learning_path": {
    "total_phases": 4,
    "estimated_duration": "8-12 months",
    "phases": [
      {
        "phase_id": 1,
        "phase_name": "Foundation",
        "description": "Learn web development fundamentals",
        "duration": "2-3 months",
        "courses": [
          {
            "course_id": "html_css_basics",
            "title": "HTML & CSS Fundamentals",
            "priority": "high",
            "prerequisite": false
          }
        ],
        "skills_gained": ["HTML", "CSS", "Web Basics"]
      }
    ]
  }
}
```

---

## Error Handling

### Standard Error Response Format

```json
{
  "status": "error",
  "error_code": "ERROR_TYPE",
  "message": "Human-readable error message",
  "details": "Additional error details"
}
```

### Common Error Codes

- `INCOMPLETE_ASSESSMENT`: Assessment requires more answers
- `CAREER_NOT_FOUND`: Specified career doesn't exist
- `SERVICE_UNAVAILABLE`: Required service is temporarily unavailable
- `COURSE_FETCH_FAILED`: Failed to retrieve course data
- `ASSESSMENT_FAILED`: Assessment processing error
- `ROADMAP_GENERATION_FAILED`: Roadmap creation error
- `PERSONALIZATION_FAILED`: Personalized recommendation error
- `SKILL_MATCHING_FAILED`: Skill-based matching error
- `LEARNING_PATH_FAILED`: Learning path generation error

### HTTP Status Codes

- `200`: Success
- `400`: Bad Request (invalid parameters)
- `404`: Not Found (resource doesn't exist)
- `500`: Internal Server Error
- `503`: Service Unavailable

---

## Data Models

### Assessment Answer
```json
{
  "question_id": 1,
  "answer": "string"
}
```

### User Profile
```json
{
  "user_id": "string",
  "preferred_skills": ["string"],
  "difficulty_preference": "beginner|intermediate|advanced",
  "time_availability": "limited|moderate|extensive",
  "budget_preference": "free|budget|premium|mixed",
  "learning_style": "visual|auditory|hands-on|reading",
  "career_goals": ["string"]
}
```

### Course Object
```json
{
  "course_id": "string",
  "title": "string",
  "organization": "string",
  "rating": 4.5,
  "review_count": 1250,
  "difficulty": "Beginner|Intermediate|Advanced",
  "course_type": "string",
  "duration": "string",
  "skills": ["string"],
  "url": "string",
  "is_free": boolean,
  "relevance_score": 0.85,
  "match_reasons": ["string"]
}
```

---

## Support

For API support or questions, please refer to the interactive documentation at `/docs` or `/redoc` endpoints.


