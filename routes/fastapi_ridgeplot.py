from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
import subprocess
import os
from pathlib import Path

router = APIRouter(prefix="/ridgeplot", tags=["Ridgeplot"])

@router.post("/")
async def run_ridgeplot(request_data: dict):
    try:
        input_file = request_data.get("input_file")
        output_dir = request_data.get("output_dir")
        width = request_data.get("width")
        height = request_data.get("height")

        if not all([input_file, output_dir, width, height]):
            raise HTTPException(status_code=400, detail="Missing required parameters.")

        os.makedirs(output_dir, exist_ok=True)

        # ✅ R 스크립트 경로 (예: backend/rcode/run_ridgeplot.R)
        r_script_path = Path(__file__).resolve().parent.parent / "rcode" / "run_ridgeplot.R"

        # ✅ Rscript 명령어 인자 구성
        cmd = [
            "Rscript",
            str(r_script_path),
            input_file,
            output_dir,
            str(width),
            str(height)
        ]

        # ✅ Rscript 실행
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8"
        )

        if result.returncode == 0:
            return JSONResponse(content={"message": "Ridgeplot GSEA completed successfully!", "stdout": result.stdout})
        else:
            raise HTTPException(status_code=500, detail=result.stderr)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))