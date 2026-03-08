import os
import json
import logging
import asyncio
from app.services.resume_builder import ResumeBuilder
from app.services.prompt_registry import PromptRegistryService

logger = logging.getLogger(__name__)

class GoldenResumeTestService:
    """
    Test Suite for verifying AI Resume Performance against 'Golden' benchmarks.
    Ensures quality, consistency, and prevents regression in ATS scoring.
    """
    
    def __init__(self, fixtures_path=None):
        self.fixtures_path = fixtures_path or os.path.join(
            os.getcwd(), 'tests', 'fixtures', 'golden_resumes'
        )

    def load_fixtures(self):
        fixtures = []
        if not os.path.exists(self.fixtures_path):
            os.makedirs(self.fixtures_path)
            return fixtures

        for filename in os.listdir(self.fixtures_path):
            if filename.endswith('.json'):
                with open(os.path.join(self.fixtures_path, filename), 'r') as f:
                    fixtures.append(json.load(f))
        return fixtures

    async def run_benchmark(self, fixture):
        """Runs a single golden resume benchmark test."""
        name = fixture.get('name', 'Unknown Test')
        resume_data = fixture.get('resume')
        job_description = fixture.get('job_description')
        min_score = fixture.get('expected_min_score', 0)
        max_score = fixture.get('expected_max_score', 100)
        required_keywords = fixture.get('required_keywords', [])

        # We need a ResumeBuilder instance. Note: user_id is arbitrary for benchmarking.
        builder = ResumeBuilder(user_id=0)
        
        # We need a Resume object or a mock for optimize_for_job. 
        # Since optimize_for_job uses Resume.query.get, we might need a more direct path or mock the DB.
        # Let's use a specialized benchmark method in ResumeBuilder or just the LLM directly.
        
        prompt_obj = PromptRegistryService.get_prompt('resume_optimization')
        user_prompt = PromptRegistryService.format_prompt(
            prompt_obj,
            resume_json=json.dumps(resume_data),
            job_description=job_description
        )
        
        from app.services.llm_service import ask_ai
        
        logger.info(f"Running Golden Benchmark: {name}")
        
        try:
            response = await ask_ai(
                prompt=user_prompt,
                system_prompt=prompt_obj.system_prompt,
                max_tokens=prompt_obj.max_tokens,
                temperature=prompt_obj.temperature
            )
        except Exception as e:
             return {
                "success": False,
                "name": name,
                "error": f"AI Call Failed: {str(e)}"
            }
        
        # Use ResumeBuilder's validation logic
        result = builder._validate_optimization_json(response)
        
        if not result:
            return {
                "success": False,
                "name": name,
                "error": "Failed to parse AI optimization response"
            }

        actual_score = result.get('ats_score', 0)
        missing_keywords = result.get('missing_keywords', [])
        
        # Check constraints
        score_ok = min_score <= actual_score <= max_score
        
        # Keywords check: Are required keywords marked as missing erroneously?
        # or: Are they present in the "matched" set (not explicitly returned by current schema)
        # For now, we'll check that required_keywords are NOT in the missing list if the resume has them.
        
        detected_missing = [kw.lower() for kw in missing_keywords]
        important_missing = [kw for kw in required_keywords if kw.lower() in detected_missing]
        
        success = score_ok and len(important_missing) == 0
        
        return {
            "success": success,
            "name": name,
            "actual_score": actual_score,
            "expected_range": [min_score, max_score],
            "important_missing": important_missing,
            "prompt_version": prompt_obj.version
        }

    async def run_all_benchmarks(self):
        fixtures = self.load_fixtures()
        results = []
        for fixture in fixtures:
            res = await self.run_benchmark(fixture)
            results.append(res)
        return results
