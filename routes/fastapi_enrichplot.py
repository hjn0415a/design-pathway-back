import subprocess
from pathlib import Path
from fastapi import APIRouter, HTTPException, BackgroundTasks, Body
from fastapi.responses import FileResponse
from pydantic import BaseModel
import shutil
import tempfile
import zipfile

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
def run_enrichplot(
    background_tasks: BackgroundTasks,
    params: EnrichplotParams = Body(...)
):
    """Run GO enrichment analysis and return results as a ZIP file."""
    try:
        # R 스크립트 경로
        r_script_path = Path(__file__).resolve().parent.parent / "rcode" / "run_enrichplot.R"
        if not r_script_path.exists():
            raise HTTPException(status_code=500, detail=f"R script not found at {r_script_path}")

        # 절대 경로 변환
        result_root = str(Path(params.result_root).resolve())
        output_root = str(Path(params.output_root).resolve())

        # 디버깅 출력
        print(f"[DEBUG] result_root = {result_root}")
        print(f"[DEBUG] output_root = {output_root}")

        # Rscript 실행
        cmd = [
            "Rscript",
            str(r_script_path),
            result_root,
            output_root,
            params.org_db,
            str(params.showCategory),
            str(params.pvalueCutoff),
            str(params.plot_width),
            str(params.plot_height),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")

        if result.returncode != 0:
            print("❌ Rscript stderr:", result.stderr)
            raise HTTPException(status_code=500, detail=f"Rscript execution failed:\n{result.stderr}")

        # 결과 폴더 압축
        output_path = Path(output_root)
        if not output_path.exists():
            raise HTTPException(status_code=500, detail=f"Output directory not found: {output_root}")

        # 임시 디렉토리에서 ZIP 생성
        tmp_dir = tempfile.mkdtemp()
        zip_path = Path(tmp_dir) / "enrichment_results.zip"

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for file in output_path.rglob("*"):
                if file.is_file():
                    arcname = file.relative_to(output_path)
                    zipf.write(file, arcname)

        # ZIP 파일 응답 후 삭제
        background_tasks.add_task(shutil.rmtree, tmp_dir)

        return FileResponse(
            zip_path,
            media_type="application/zip",
            filename="enrichment_results.zip"
        )

    except subprocess.SubprocessError as e:
        raise HTTPException(status_code=500, detail=f"Subprocess error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))