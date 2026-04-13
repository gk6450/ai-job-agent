"""Resume and cover letter API routes."""

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from pathlib import Path

from ..auth import verify_token
from ..config import GENERATED_DIR

router = APIRouter(prefix="/api/resume", tags=["resume"])


@router.get("/generated")
async def list_generated(_=Depends(verify_token)):
    resume_dir = GENERATED_DIR / "resumes"
    cover_dir = GENERATED_DIR / "cover_letters"

    resumes = []
    if resume_dir.exists():
        for f in sorted(resume_dir.glob("*.pdf")):
            resumes.append({"name": f.name, "size_kb": round(f.stat().st_size / 1024, 1)})

    covers = []
    if cover_dir.exists():
        for f in sorted(cover_dir.glob("*.pdf")):
            covers.append({"name": f.name, "size_kb": round(f.stat().st_size / 1024, 1)})

    return {"resumes": resumes, "cover_letters": covers}


@router.get("/download/{doc_type}/{filename}")
async def download_document(doc_type: str, filename: str, _=Depends(verify_token)):
    if doc_type == "resume":
        filepath = GENERATED_DIR / "resumes" / filename
    elif doc_type == "cover_letter":
        filepath = GENERATED_DIR / "cover_letters" / filename
    else:
        return {"error": "Invalid document type"}

    if not filepath.exists():
        return {"error": "File not found"}

    return FileResponse(path=str(filepath), filename=filename, media_type="application/pdf")


@router.post("/tailor")
async def tailor_resume(body: dict, _=Depends(verify_token)):
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "mcp-servers" / "resume_tailor"))

    from server import tailor_resume_for_job
    result = await tailor_resume_for_job(
        job_description=body.get("job_description", ""),
        job_title=body.get("job_title", ""),
        company=body.get("company", ""),
        application_id=body.get("application_id", ""),
    )
    return {"result": result}
