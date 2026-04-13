from .linkedin_easy_apply import LinkedInEasyApplyHandler
from .workday import WorkdayHandler
from .greenhouse import GreenhouseHandler
from .lever import LeverHandler
from .naukri_apply import NaukriApplyHandler
from .indeed_apply import IndeedApplyHandler
from .icims import ICIMSHandler
from .generic_fallback import GenericFallbackHandler

HANDLERS = {
    "linkedin": LinkedInEasyApplyHandler,
    "workday": WorkdayHandler,
    "greenhouse": GreenhouseHandler,
    "lever": LeverHandler,
    "naukri": NaukriApplyHandler,
    "indeed": IndeedApplyHandler,
    "icims": ICIMSHandler,
    "unknown": GenericFallbackHandler,
}


def get_handler(ats_type: str):
    """Get the appropriate handler for an ATS type."""
    handler_class = HANDLERS.get(ats_type, GenericFallbackHandler)
    return handler_class()
