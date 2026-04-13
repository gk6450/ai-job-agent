from .linkedin import LinkedInScraper
from .indeed import IndeedScraper
from .naukri import NaukriScraper
from .glassdoor import GlassdoorScraper
from .wellfound import WellfoundScraper

SCRAPERS = {
    "linkedin": LinkedInScraper,
    "indeed": IndeedScraper,
    "naukri": NaukriScraper,
    "glassdoor": GlassdoorScraper,
    "wellfound": WellfoundScraper,
}
