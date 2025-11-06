from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pathlib import Path
import subprocess
import tempfile
import os

router = APIRouter(prefix="/deg", tags=["DEG"])

class DegParams(BaseModel):
    csv_path: str
    fc_input: str
    pval_input: str

@router.post("/")
async def run_deg(params: DegParams):
    try:
        csv_file = Path(params.csv_path).resolve()
        if not csv_file.exists():
            raise HTTPException(status_code=400, detail=f"{csv_file} does not exist.")

        result_dir = csv_file.parent / "Deg"
        result_dir.mkdir(parents=True, exist_ok=True)

        # thresholds parsing
        fc_thresholds = [float(x.strip()) for x in params.fc_input.split(",") if x.strip()]
        pval_thresholds = [float(x.strip()) for x in params.pval_input.split(",") if x.strip()]

        # R 스크립트 생성
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
fc_thresholds <- c({", ".join(map(str, fc_thresholds))})
pval_thresholds <- c({", ".join(map(str, pval_thresholds))})
result_dir <- "{result_dir}"

save_filtered_results(csv_path, fc_thresholds, pval_thresholds, result_dir)
""")

        result = subprocess.run(
            ["Rscript", str(r_script_path)],
            capture_output=True,
            text=True,
            encoding="utf-8"
        )

        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=result.stderr)

        return {"message": "DEG filtering completed successfully!", "stdout": result.stdout}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))