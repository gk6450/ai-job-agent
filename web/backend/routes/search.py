"""Job search API routes."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..auth import verify_token

router = APIRouter(prefix="/api/search", tags=["search"])


class SearchRequest(BaseModel):
    keywords: str
    location: str = ""
    platforms: str = ""
    experience_level: str = ""
    remote_only: bool = False


@router.post("")
async def search_jobs(req: SearchRequest, _=Depends(verify_token)):
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "mcp-servers" / "job_search"))

    from server import search_all_platforms
    result = await search_all_platforms(
        keywords=req.keywords,
        location=req.location,
        platforms=req.platforms,
        experience_level=req.experience_level,
        remote_only=req.remote_only,
    )
    return {"results": result}


@router.post("/single")
async def search_single_platform(req: dict, _=Depends(verify_token)):
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "mcp-servers" / "job_search"))

    from server import search_jobs as _search
    result = await _search(
        keywords=req.get("keywords", ""),
        platform=req.get("platform", "linkedin"),
        location=req.get("location", ""),
        experience_level=req.get("experience_level", ""),
    )
    return {"results": result}
