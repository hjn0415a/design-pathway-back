from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
import subprocess
import tempfile
import zipfile
import os

router = APIRouter(prefix="/deg", tags=["DEG"])

@router.post("/")
async def run_deg(
    csv_path: str = Form(...),
    fc_input: str = Form(...),
    pval_input: str = Form(...)
):
    csv_file = Path(csv_path).resolve()
    if not csv_file.exists():
        raise HTTPException(status_code=400, detail=f"{csv_file} does not exist.")

    # 결과 디렉토리 설정
    result_dir = csv_file.parent.parent / "Deg"
    result_dir.mkdir(parents=True, exist_ok=True)

    # R 스크립트 임시 파일 생성
    with tempfile.NamedTemporaryFile(mode="w", suffix=".R", delete=False, encoding="utf-8") as tmp_r:
        r_script_path = Path(tmp_r.name)

        tmp_r.write(f"""
save_filtered_results <- function(csv_path, fc_thresholds, pval_thresholds, result_dir) {{
  gene_data <- read.csv(csv_path, stringsAsFactors = FALSE)
  if (!dir.exists(result_dir)) dir.create(result_dir, recursive = TRUE)

  combo_names <- character()

  for (fc_cut in fc_thresholds) {{
    for (p_cut in pval_thresholds) {{
      subset_genes <- gene_data[abs(gene_data$foldchange) >= fc_cut &
                                gene_data$pvalue <= p_cut, , drop = FALSE]

      combo_name <- paste0("FC", fc_cut, "_p", p_cut)
      combo_dir  <- file.path(result_dir, combo_name)
      if (!dir.exists(combo_dir)) dir.create(combo_dir, recursive = TRUE)

      combo_names <- c(combo_names, combo_name)

      write.csv(subset_genes,
                file = file.path(combo_dir, "filtered_gene_list.csv"),
                row.names = FALSE)

      message(sprintf("저장 완료: FC >= %.2f, pvalue <= %.3f (%d genes)",
                      fc_cut, p_cut, nrow(subset_genes)))
    }}
  }}

  write.csv(data.frame(combo = combo_names),
            file = file.path(result_dir, "combo_names.csv"), row.names = FALSE)
}}

csv_path <- "{csv_file}"
fc_thresholds <- c({", ".join(fc_input.split(","))})
pval_thresholds <- c({", ".join(pval_input.split(","))})
result_dir <- "{result_dir}"

save_filtered_results(csv_path, fc_thresholds, pval_thresholds, result_dir)
""")

    # subprocess 명령어 실행
    cmd = ["Rscript", str(r_script_path)]

    try:
        result = subprocess.run(cmd, text=True, capture_output=True)

        if result.returncode != 0:
            print("❌ Rscript stderr:")
            print(result.stderr)
            raise HTTPException(
                status_code=500,
                detail=f"Rscript execution failed:\n{result.stderr}"
            )
        
        zip_path = result_dir/"deg.zip"
        if zip_path.exists():
            zip_path.unlink()




        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for file in result_dir.rglob("*"):
                if file.is_file():
                    zipf.write(file, file.relative_to(result_dir))
        os.sync() 

 
        return FileResponse(
            zip_path,
            media_type="application/zip",
            filename="deg.zip")

    except subprocess.SubprocessError as e:
        raise HTTPException(status_code=500, detail=f"Subprocess error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))