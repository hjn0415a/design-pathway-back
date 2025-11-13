from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel
import subprocess
import os
import shutil
import zipfile
from pathlib import Path

router = APIRouter(prefix="/gsego", tags=["Gsego"])

class GSEAParams(BaseModel):
    file_path: str
    out_dir: str
    orgdb: str
    min_gs_size: int
    max_gs_size: int
    pvalue_cutoff: float
    plot_width: float
    plot_height: float

@router.post("/")
def run_gsego(req: GSEAParams, background_tasks: BackgroundTasks):
    """Run GSEA analysis using an external R script and return ZIP file."""

    # ✅ 출력 디렉토리 준비
    output_dir = Path(req.out_dir)
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # ✅ R 스크립트 경로
    r_script_path = Path(__file__).resolve().parent.parent / "rcode" / "run_gsego.R"
    if not r_script_path.exists():
        raise HTTPException(status_code=500, detail=f"R script not found at {r_script_path}")

    # ✅ Rscript 실행 명령어
    cmd = [
        "Rscript",
        str(r_script_path),
        str(req.file_path),
        str(output_dir),
        str(req.orgdb),
        str(req.min_gs_size),
        str(req.max_gs_size),
        str(req.pvalue_cutoff),
        str(req.plot_width),
        str(req.plot_height),  
    ]

    print("Running command:", " ".join(cmd))

    try:
        result = subprocess.run(cmd, text=True, capture_output=True)

        if result.returncode != 0:
            print("❌ Rscript stderr:")
            print(result.stderr)
            raise HTTPException(
                status_code=500,
                detail=f"GSEA execution failed:\n{result.stderr}"
            )

        # ✅ 결과 ZIP으로 패키징
        zip_path = output_dir / "gsego_results.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for file in output_dir.rglob("*"):
                if file.is_file() and file != zip_path:
                    arcname = file.relative_to(output_dir)
                    zipf.write(file, arcname)

        # ✅ ZIP 파일 응답 후 자동 삭제
        background_tasks.add_task(zip_path.unlink)

        return FileResponse(
            zip_path,
            media_type="application/zip",
            filename="gsego_results.zip",
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))