"""Gmail sync API routes."""

from fastapi import APIRouter, Depends

from ..auth import verify_token

router = APIRouter(prefix="/api/gmail", tags=["gmail"])


@router.get("/status")
async def gmail_status(_=Depends(verify_token)):
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "mcp-servers" / "gmail_sync"))

    from auth import check_auth_status
    return check_auth_status()


@router.post("/sync")
async def sync_gmail(_=Depends(verify_token)):
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "mcp-servers" / "gmail_sync"))

    from server import sync_all
    result = await sync_all()
    return {"result": result}


@router.get("/responses")
async def check_responses(days_back: int = 7, _=Depends(verify_token)):
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "mcp-servers" / "gmail_sync"))

    from server import check_new_responses
    result = await check_new_responses(days_back=days_back)
    return {"result": result}
