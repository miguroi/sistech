import pandas as pd
from typing import Dict, List, Tuple
from collections import Counter
from dataclasses import dataclass
import re

@dataclass
class Checkpoint:
    checkpoint_id: int
    title: str
    description: str
    skills_derived: List[str]
    estimated_time: str
    skills_source: str

@dataclass
class Roadmap:
    career_id: str
    career_name: str
    total_checkpoints: int
    estimated_duration: str
    checkpoints: List[Checkpoint]

class RoadmapGenerator:
    STOP_WORDS = {
        'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 
        'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 
        'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'this', 'that',
        'these', 'those', 'you', 'your', 'it', 'its', 'they', 'their', 'we', 'our'
    }

    SOFT_SKILLS = ['communication', 'leadership', 'teamwork', 'presentation', 'management']
    TOOLS = ['software', 'platform', 'framework', 'library', 'tool']

    def __init__(self, career_processor):
        self.career_processor = career_processor
        self.skill_categories = self._initialize_skill_categories()
    
    def _initialize_skill_categories(self) -> Dict[str, List[str]]:
        """Automatically categorize skills based on course data patterns"""
        courses_df = self.career_processor.courses_df
        
        # Extract all skills and categorize by course type and difficulty
        foundation_skills = []
        technical_skills = []
        tool_skills = []
        advanced_skills = []
        soft_skills = []
        
        # Analyze beginner courses for foundation skills
        beginner_courses = courses_df[courses_df['difficulty'] == 'Beginner']
        beginner_skills_text = ' '.join(beginner_courses['skills'].fillna(''))
        foundation_terms = self._extract_frequent_terms(beginner_skills_text, min_freq=5)
        
        # Analyze advanced courses for advanced skills  
        advanced_courses = courses_df[courses_df['difficulty'] == 'Advanced']
        advanced_skills_text = ' '.join(advanced_courses['skills'].fillna(''))
        advanced_terms = self._extract_frequent_terms(advanced_skills_text, min_freq=3)
        
        # Common tool patterns (based on frequency analysis)
        all_skills_text = ' '.join(courses_df['skills'].fillna(''))
        all_terms = self._extract_frequent_terms(all_skills_text, min_freq=10)
        
        return {
            'foundation': foundation_terms[:15],
            'technical': all_terms[:20],
            'tools': self._identify_tool_skills(all_terms),
            'advanced': advanced_terms[:10],
            'soft': self._identify_soft_skills(all_terms)
        }
    
    def _extract_frequent_terms(self, text: str, min_freq: int = 5) -> List[str]:
        """Extract frequent terms from skill text"""
        # Clean and filter text, removing stop words
        words = text.lower().split()
        filtered_words = [word for word in words if word not in self.STOP_WORDS and len(word) > 2]
        term_counts = Counter(filtered_words)
        return [term for term, count in term_counts.most_common() if count >= min_freq]
    
    def _identify_tool_skills(self, terms: List[str]) -> List[str]:
        """Identify tool-related skills from term frequency"""
        tools = []
        tool_indicators = self.TOOLS 
        for term in terms:
            if any(indicator in term.lower() for indicator in tool_indicators):
                tools.append(term)
        return tools[:10]
    
    def _identify_soft_skills(self, terms: List[str]) -> List[str]:
        """Identify soft skills from frequency analysis"""
        soft_skills = []
        soft_indicators = self.SOFT_SKILLS
        for term in terms:
            if any(indicator in term.lower() for indicator in soft_indicators):
                soft_skills.append(term)
        return soft_skills[:8]
    
    def generate_roadmap(self, career_role: str) -> Roadmap:
        """Generate learning roadmap for a career"""
        career_id = career_role.lower().replace(' ', '_')
        
        # Get skills from both sources
        qa_skills = self.career_processor.extract_skills_from_qa(career_role)
        course_skills = self.career_processor.extract_skills_from_courses(career_role)
        
        # Combine and prioritize skills
        all_skills = qa_skills + course_skills
        skill_frequency = Counter(all_skills)
        prioritized_skills = [skill for skill, freq in skill_frequency.most_common(25)]
        
        # Generate checkpoints based on skill analysis
        checkpoints = self._create_checkpoints(prioritized_skills, career_role)
        
        # Estimate total duration based on checkpoint count
        total_weeks = sum([self._parse_duration(cp.estimated_time) for cp in checkpoints])
        duration = self._format_duration(total_weeks)
        
        return Roadmap(
            career_id=career_id,
            career_name=career_role,
            total_checkpoints=len(checkpoints),
            estimated_duration=duration,
            checkpoints=checkpoints
        )
    
    def _create_checkpoints(self, skills: List[str], career_role: str) -> List[Checkpoint]:
        """Create learning checkpoints based on skill analysis"""
        checkpoints = []
        
        # Foundation checkpoint (if needed)
        foundation_skills = [s for s in skills if self._is_foundation_skill(s)]
        if foundation_skills:
            checkpoints.append(Checkpoint(
                checkpoint_id=len(checkpoints) + 1,
                title="Foundation Skills",
                description=f"Build fundamental knowledge required for {career_role}",
                skills_derived=foundation_skills[:5],
                estimated_time="4-6 weeks",
                skills_source="career_qa + courses"
            ))
        
        # Core technical skills
        technical_skills = [s for s in skills if self._is_technical_skill(s)]
        if technical_skills:
            checkpoints.append(Checkpoint(
                checkpoint_id=len(checkpoints) + 1,
                title="Core Technical Skills",
                description=f"Master essential technical skills for {career_role}",
                skills_derived=technical_skills[:6],
                estimated_time="6-8 weeks",
                skills_source="career_qa + courses"
            ))
        
        # Tools and technologies
        tool_skills = [s for s in skills if self._is_tool_skill(s)]
        if tool_skills:
            checkpoints.append(Checkpoint(
                checkpoint_id=len(checkpoints) + 1,
                title="Tools and Technologies",
                description=f"Learn industry-standard tools for {career_role}",
                skills_derived=tool_skills[:5],
                estimated_time="4-6 weeks",
                skills_source="courses"
            ))
        
        # Practical application
        practical_skills = [s for s in skills if self._is_practical_skill(s)]
        if practical_skills:
            checkpoints.append(Checkpoint(
                checkpoint_id=len(checkpoints) + 1,
                title="Practical Application",
                description="Apply skills through hands-on projects and real-world scenarios",
                skills_derived=practical_skills[:4],
                estimated_time="6-8 weeks",
                skills_source="career_qa + courses"
            ))
        
        # Advanced specialization
        advanced_skills = [s for s in skills if self._is_advanced_skill(s)]
        if advanced_skills:
            checkpoints.append(Checkpoint(
                checkpoint_id=len(checkpoints) + 1,
                title="Advanced Specialization",
                description=f"Develop advanced expertise in {career_role}",
                skills_derived=advanced_skills[:4],
                estimated_time="8-10 weeks",
                skills_source="courses"
            ))
        
        # Professional skills
        soft_skills = [s for s in skills if self._is_soft_skill(s)]
        if soft_skills:
            checkpoints.append(Checkpoint(
                checkpoint_id=len(checkpoints) + 1,
                title="Professional Skills",
                description="Develop communication and professional skills for career success",
                skills_derived=soft_skills[:4],
                estimated_time="3-4 weeks",
                skills_source="career_qa"
            ))
        
        return checkpoints
    
    def _is_foundation_skill(self, skill: str) -> bool:
        """Check if skill is foundational based on frequency in beginner courses"""
        return skill.lower() in [s.lower() for s in self.skill_categories['foundation']]
    
    def _is_technical_skill(self, skill: str) -> bool:
        """Check if skill is technical based on patterns"""
        return skill.lower() in [s.lower() for s in self.skill_categories['technical']]
    
    def _is_tool_skill(self, skill: str) -> bool:
        """Check if skill is tool-related"""
        return skill.lower() in [s.lower() for s in self.skill_categories['tools']]
    
    def _is_practical_skill(self, skill: str) -> bool:
        """Check if skill involves practical application"""
        practical_terms = ['project', 'application', 'implementation', 'development', 'analysis']
        return any(term in skill.lower() for term in practical_terms)
    
    def _is_advanced_skill(self, skill: str) -> bool:
        """Check if skill is advanced level"""
        return skill.lower() in [s.lower() for s in self.skill_categories['advanced']]
    
    def _is_soft_skill(self, skill: str) -> bool:
        """Check if skill is soft skill"""
        return skill.lower() in [s.lower() for s in self.skill_categories['soft']]
    
    def _parse_duration(self, duration_str: str) -> int:
        """Parse duration string to weeks"""
        numbers = re.findall(r'\d+', duration_str)
        if numbers:
            return int(numbers[0])  # Take first number as base estimate
        return 4  # Default
    
    def _format_duration(self, total_weeks: int) -> str:
        """Format total weeks into readable duration"""
        if total_weeks <= 12:
            return f"{total_weeks} weeks"
        elif total_weeks <= 52:  # Up to 1 year
            months = total_weeks // 4
            return f"{months} months"
        else:
            months = total_weeks // 4
            years = months // 12
            remaining_months = months % 12
            if remaining_months == 0:
                return f"{years} year{'s' if years > 1 else ''}"
            else:
                return f"{years} year{'s' if years > 1 else ''} {remaining_months} month{'s' if remaining_months > 1 else ''}"
