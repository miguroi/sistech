# Coursera Course Recommendation System

## Dataset Overview

**Source**: Coursera Platform  
**Features**: Course title, skills, organization, rating, review count, difficulty, duration, course type, URL, pricing, course ID  
**Dataset Size**: 1,704 English courses across 4 difficulty levels
**Organizations**: 236 educational institutions and companies

## Development Process

### Initial Exploration

The project began with the goal of building a recommendation system using previously scraped course data. I implemented three different approaches: content-based filtering for content similarity analysis, collaborative filtering for user behavior patterns, and a hybrid system that combines both approaches.

### Technical Flow

1. **Synthetic Data Generation**: Generated synthetic user interaction data to simulate real-world usage patterns.
2. **Feature Engineering**: Implemented TF-IDF vectorization for text features and numerical normalization.
3. **Recommendation Engines**: Built and evaluated three recommendation engines.
4. **Results Export**: Exported all results for analysis and validation.

## Method Selection

### TF-IDF Vectorization

I chose TF-IDF because, unlike simple Bag-of-Words, it automatically handles the importance weighting of terms, reducing the impact of common words that don't provide discriminative information. While Word2Vec offers semantic understanding, the course titles and skills in this dataset are more keyword-focused rather than semantic, making TF-IDF's term-frequency approach more suitable. Additionally, TF-IDF provides interpretable results where we can understand which terms are driving the similarity calculations.

## Recommendation Results

### Testing Scenario: "Machine Learning" Course Recommendations

### Sample Course: "Google Data Analytics"

| Rank | Content-Based Filtering | Collaborative Filtering | Hybrid System |
|------|-------------------------|------------------------|---------------|
| 1 | Google Project Management | Mechanization in Construction | Mechanization in Construction |
| 2 | Google IT Support | Human Anatomy & Physiology I | Human Anatomy & Physiology I |
| 3 | Google UX Design | Strategies for Heavy Lifting | Strategies for Heavy Lifting |

### Analysis

- **Content-Based Filtering**: When analyzing the "Google Data Analytics" course, the system clustered related Google professional certificates, recognizing shared organizational branding, similar skill development approaches, and comparable course structures.
- **Collaborative Filtering**: Based on the results, users who engaged with "Google Data Analytics" showed preferences for hands-on technical courses like construction mechanization and anatomy studies. This could indicate career changers from technical fields or professionals seeking to apply analytical thinking to physical-world problems. However, since the user interaction data was synthetically generated, these patterns may not reflect real-world behavior.
- **Hybrid System**: The hybrid approach identified an interesting pattern where learners value both structured skill development and diverse practical applications.

## Challenges & Solutions

### Synthetic Data Creation

**Problem**: I was initially confused about how to build a collaborative filtering system without real user interaction data.

**Solution**: I created a synthetic user dataset with 500 users having 5-50 course interactions each.

### Sparse Matrix Dilemma

**Problem**: The user-course rating matrix became extremely sparse, with most cells empty.

**Solution**: I designed the collaborative filtering to focus on users who actually had rating overlaps. The hybrid approach compensates for sparsity by falling back on content-based recommendations when collaborative data is insufficient.

**Problem**: How to recommend courses for completely new users or brand new courses with no interaction history.

**Solution**: The hybrid system naturally handles this by weighting content-based recommendations higher when collaborative data is insufficient. For new users, the system can still provide meaningful recommendations based on course content similarity, then gradually incorporate collaborative signals as user interaction data accumulates.
