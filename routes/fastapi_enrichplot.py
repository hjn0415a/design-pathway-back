import subprocess
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/enrichplot", tags=["Enrichplot"])

class EnrichplotParams(BaseModel):
    result_root: str
    output_root: str
    org_db: str
    showCategory: int
    pvalueCutoff: float
    plot_width: float
    plot_height: float

@router.post("/")
def run_enrichplot(params: EnrichplotParams):
    """Run GO enrichment analysis using R script."""
    try:
        # ✅ R 스크립트 경로
        r_script_path = Path(__file__).resolve().parent.parent / "rcode" / "run_enrichplot.R"

        if not r_script_path.exists():
            raise HTTPException(status_code=500, detail=f"R script not found at {r_script_path}")

        # ✅ Rscript 명령 구성
        cmd = [
            "Rscript",
            str(r_script_path),
            params.result_root,
            params.output_root,
            params.org_db,
            str(params.showCategory),
            str(params.pvalueCutoff),
            str(params.plot_width),
            str(params.plot_height),
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8"
        )

        if result.returncode == 0:
            return {"message": "GO enrichment analysis completed successfully!", "stdout": result.stdout}
        else:
            raise HTTPException(status_code=500, detail=result.stderr)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))