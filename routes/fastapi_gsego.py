from fastapi import APIRouter
from pydantic import BaseModel
import subprocess
import tempfile
import os
import shutil

router = APIRouter()

class GSEAParams(BaseModel):
    file_path: str
    out_dir: str
    orgdb: str
    min_gs_size: int
    max_gs_size: int
    pvalue_cutoff: float

@router.post("/")
async def run_gsego(params: GSEAParams):
    """Run GSEA analysis using an external R script."""

    # 임시 디렉터리 생성
    with tempfile.TemporaryDirectory() as tmpdir:
        r_script_path = os.path.join(os.path.dirname(__file__), "scripts", "run_gsego.R")

        if not os.path.exists(r_script_path):
            return {"error": f"R script not found at {r_script_path}"}

        # Rscript 명령어 구성
        command = [
            "Rscript",
            r_script_path,
            params.file_path,
            params.out_dir,
            params.orgdb,
            str(params.min_gs_size),
            str(params.max_gs_size),
            str(params.pvalue_cutoff),
        ]

        try:
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            return {"message": "✅ GSEA completed successfully!", "stdout": result.stdout}
        except subprocess.CalledProcessError as e:
            return {
                "error": "❌ GSEA execution failed",
                "stdout": e.stdout,
                "stderr": e.stderr,
            }