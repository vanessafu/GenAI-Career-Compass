# Career Compass

**Team members:** Zitong Fu (03786391), Yuxuan Qian (03717005), Benjamin Theurich (03812839), Anh Tu Ly (03826660), Moritz Busch (03783991), Anthea Kleiner (03813218), Semjon Eschweiler ()

## 1. Project Description

This project aims to provide users with a simple and intuitive interface for exploring possible career options in IT and technology based on their current experience, skills, and background. Inspired by tools like Google Labs' Career Dreamer, the system analyzes a user's current role and skills, then suggests related roles they could potentially transition into. After the user selects a target career, the tool generates a focused career path and identifies skill gaps, helping the user quickly see where they fall short and what steps they can take to make the transition.

## 2. Test Data and Input Sources

### Test Data

- **Mock Curriculum Vitae:** Artificially created CVs representing different experience levels and backgrounds for controlled testing.
- **Student Curriculum Vitae:** CVs provided by students within the course (with consent), used to evaluate the system under realistic conditions.
- **User Input:** User-provided information, including uploaded CVs, selected positions, and stated skills and interests, which are used to personalize role matching and career path generation.

### Input Sources

- **Database Integration:** Integration of standardized databases such as ESCO and O*NET to access structured occupational data. These sources are used to retrieve real-world job roles, detailed skill definitions, and competency requirements.
- **User Input:** User-provided information, including uploaded CVs, selected positions, and stated skills and interests, which are used to personalize role matching and career path generation.

## 3. Key Deliverables

### Mandatory Features

- **Position Idea Generation:** Generates tailored job position suggestions based on the user's skills, interests, and past experience, enhanced through integration with ESCO and O*NET databases. This enables accurate mapping of user profiles to relevant roles.
- **Career Path Generation:** Generates potential career paths based on positions selected by the user, highlighting transitions between roles. This helps users explore personalized career progression options aligned with their interests and preferences.
- **Editable Prompt:** Users will have access to an editable prompt feature, allowing them to manually tweak the AI's parameters, constraints, or context to refine their specific career transition query.
- **Option for Curriculum Vitae Upload:** Allows users to upload their CV to extract structured information about their skills, experience, and education. This data is used to match the user with suitable roles from integrated databases and to generate additional role suggestions that align with their profile.
- **Gap Identifier:** Overlay the user's skill map over the skill map for the desired position and show a percentage score of how close of a match it is. The user will be able to easily identify what skills they are lacking in a visual manner.

### Optional Features

- **Fine-grained career path:** Pull realtime job-listings, bootcamps, and courses from the web so the user has a specific, tangible path with concrete next steps.
- **Peer-to-peer gaps:** Identifies where "users like you" (similar age, education level, past experience, etc.) have skills, certifications, and experience that you don't, so you can identify where you might be falling behind compared to your peers.
- **Viability score:** Show stats of the amount of people who have successfully made this transition, highlighting how viable such a move is.
- **Explainable matching dashboard:** Provides a visual dashboard that breaks down each recommendation into multiple dimensions, like skill match, past experience match, transition difficulty, and so on. Each dimension will be assigned a matching score, so that users can quickly have an overall understanding of how well they fit the recommendation.

## 4. LLM API Integration

- **Data Parsing:** Parse unstructured text from uploaded CVs into structured metadata (e.g., skills, experience, education)
- **Semantic Mapping:** Use embedding-based similarity search as the primary method to match the user's extracted profile with standardized occupations and skills from ESCO and O*NET, while LLM APIs may further enhance this process through additional contextual understanding and personalization
- **Role Explanation & Skill Gap Analysis:** Use LLM to generate explanations for retrieved roles and identified skill gaps, helping users understand both the suitability of each role and the steps required to achieve it.
- **Actionable Path Generation:** Given a selected target role and the identified skill gaps, the LLM generates a structured and actionable career development path, outlining concrete steps for upskilling and progression.
