import logging
from app.services.linkedin_scraper import LinkedInScraper
from app.services.naukri_scraper import NaukriScraper
from app.services.indeed_scraper import IndeedScraper
from app.services.platform_scrapers import (
    MonsterScraper, GlassdoorScraper, AngelListScraper, DiceScraper,
    CareerBuilderScraper, ZipRecruiterScraper, SimplyHiredScraper
)

logger = logging.getLogger(__name__)

class ScraperFactory:
    @staticmethod
    def get_scraper(platform, headless=True):
        platform = platform.lower()
        if platform == 'linkedin':
            return LinkedInScraper(headless=headless)
        elif platform == 'naukri':
            return NaukriScraper(headless=headless)
        elif platform == 'indeed':
            return IndeedScraper(headless=headless)
        elif platform == 'monster':
            return MonsterScraper(headless=headless)
        elif platform == 'glassdoor':
            return GlassdoorScraper(headless=headless)
        elif platform == 'angellist':
            return AngelListScraper(headless=headless)
        elif platform == 'dice':
            return DiceScraper(headless=headless)
        elif platform == 'careerbuilder':
            return CareerBuilderScraper(headless=headless)
        elif platform == 'ziprecruiter':
            return ZipRecruiterScraper(headless=headless)
        elif platform == 'simplyhired':
            return SimplyHiredScraper(headless=headless)
        else:
            raise ValueError(f"Unknown platform: {platform}")

    @staticmethod
    def get_supported_platforms():
        return ['linkedin', 'naukri', 'indeed', 'monster', 'glassdoor', 'angellist', 'dice', 'careerbuilder', 'ziprecruiter', 'simplyhired']
