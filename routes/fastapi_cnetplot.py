from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel
import subprocess
import os
import shutil
from pathlib import Path
import pandas as pd
import math
import zipfile

router = APIRouter(prefix="/cnetplot", tags=["Cnetplot"])


class CnetRequest(BaseModel):
    result_root: str       # DEG 결과 폴더
    output_root: str       # Cnetplot 결과 저장 폴더
    combo_root: str        # combo_names.csv 위치
    fc_threshold: float
    pval_threshold: float
    showCategory: int
    plot_width: float
    plot_height: float


@router.post("/")
def run_cnetplot(req: CnetRequest, background_tasks: BackgroundTasks):
    """Generate Cnet plots for selected combos and return ZIP file."""

    combo_csv = Path(req.combo_root) / "combo_names.csv"
    if not combo_csv.exists():
        raise HTTPException(status_code=404, detail="combo_names.csv not found")

    combo_df = pd.read_csv(combo_csv)

    # ✅ fc/pval 필터링된 combo 리스트 선택
    selected_combos = [
        c for c in combo_df["combo"]
        if math.isclose(float(c.split("_")[0][2:]), req.fc_threshold, rel_tol=1e-3)
        and math.isclose(float(c.split("_")[1][1:]), req.pval_threshold, rel_tol=1e-3)
    ]

    print("Selected_combos for R:", selected_combos)
    print("fc_threshold:", req.fc_threshold)
    print("pval_threshold:", req.pval_threshold)

    if not selected_combos:
        raise HTTPException(status_code=400, detail="No matching combos found")

    # ✅ 결과 디렉토리 준비
    output_dir = Path(req.output_root)
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # ✅ 콤보 이름을 콤마로 연결 (R에서 strsplit으로 처리)
    combo_str = ",".join(selected_combos)
    print("Combo string passed to R:", combo_str)

    # ✅ R 스크립트 경로
    r_script_path = Path(__file__).resolve().parent.parent / "rcode" / "run_cnetplot.R"
    if not r_script_path.exists():
        raise HTTPException(status_code=500, detail=f"R script not found at {r_script_path}")

    # ✅ Rscript 실행 (6개 인자 정확히 전달)
    cmd = [
        "Rscript",
        str(r_script_path),
        str(req.result_root),
        str(output_dir),
        combo_str,  # ✅ R에서 strsplit으로 처리할 예정
        str(req.showCategory),
        str(req.plot_width),
        str(req.plot_height),
    ]

    print("Running command:", " ".join(cmd))

    try:
        # Rscript 실행
        result = subprocess.run(cmd, text=True, capture_output=True)

        if result.returncode != 0:
            print("❌ Rscript stderr:")
            print(result.stderr)
            raise HTTPException(
                status_code=500,
                detail=f"Rscript execution failed:\n{result.stderr}"
            )

        # 결과를 ZIP으로 패키징
        zip_path = output_dir / "cnetplot.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for file in output_dir.rglob("*"):
                if file.is_file() and file != zip_path:
                    arcname = file.relative_to(output_dir)
                    zipf.write(file, arcname)

        # ZIP 파일 응답 후 자동 삭제
        background_tasks.add_task(zip_path.unlink)

        return FileResponse(
            zip_path,
            media_type="application/zip",
            filename="cnetplot.zip"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))