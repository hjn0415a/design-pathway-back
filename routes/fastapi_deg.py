from fastapi import APIRouter, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pathlib import Path
import subprocess
import tempfile
import zipfile
import os
import shutil

router = APIRouter(prefix="/deg", tags=["DEG"])

@router.post("/")
async def run_deg(
    background_tasks: BackgroundTasks,
    csv_path: str = Form(...),
    fc_input: str = Form(...),
    pval_input: str = Form(...)
):
    csv_file = Path(csv_path).resolve()
    if not csv_file.exists():
        raise HTTPException(status_code=400, detail=f"{csv_file} does not exist.")

    # 결과 디렉토리 설정
    result_dir = csv_file.parent.parent / "Deg"
    if result_dir.exists():
        shutil.rmtree(result_dir)
    result_dir.mkdir(parents=True, exist_ok=True)

    # R 스크립트 경로 지정
    r_script_path = Path(__file__).resolve().parent.parent / "rcode" / "run_deg.R"

    # R 스크립트 실행 명령어 구성
    cmd = [
        "Rscript",
        str(r_script_path),
        str(csv_file),
        fc_input,
        pval_input,
        str(result_dir)
    ]

    try:
        result = subprocess.run(cmd, text=True, capture_output=True)

        if result.returncode != 0:
            print("❌ Rscript stderr:")
            print(result.stderr)
            raise HTTPException(
                status_code=500,
                detail=f"Rscript execution failed:\n{result.stderr}"
            )
        
        zip_path = result_dir / "deg.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for file in result_dir.rglob("*"):
                if file.is_file() and file != zip_path:
                    arcname = file.relative_to(result_dir)
                    zipf.write(file, arcname)

        # ✅ 응답 후 zip 파일 자동 삭제
        background_tasks.add_task(zip_path.unlink)

        return FileResponse(
            zip_path,
            media_type="application/zip",
            filename="deg.zip"
        )

    except subprocess.SubprocessError as e:
        raise HTTPException(status_code=500, detail=f"Subprocess error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))