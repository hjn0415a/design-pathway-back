# fastapi_string.py
import os
import subprocess
import tempfile
from fastapi import APIRouter, HTTPException, Form
from pydantic import BaseModel
from typing import Optional
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/run-string", tags=["STRING Network"])

class STRINGRequest(BaseModel):
    input_root: str
    combo_file: str
    output_dir: str
    taxon_id: int
    cutoff: float
    limit: int

@router.post("/")
async def run_string(
    input_root: str = Form(...),
    combo_file: str = Form(...),
    output_dir: str = Form(...),
    taxon_id: int = Form(...),
    cutoff: float = Form(...),
    limit: int = Form(...)
):
    try:
        os.makedirs(output_dir, exist_ok=True)

        # 임시 R 스크립트 생성
        with tempfile.NamedTemporaryFile(mode="w", suffix=".R", delete=False, encoding="utf-8") as tmp_r:
            r_script_path = tmp_r.name

            tmp_r.write(f"""
library(RCy3)
library(readr)

ping <- tryCatch(cytoscapePing(), error=function(e) NULL)
if (is.null(ping)) stop("Cytoscape not reachable at localhost:1234")

combo_names <- readRDS(file.path("{input_root}", "{combo_file}"))
result_root <- "{input_root}"
out_dir     <- "{output_dir}"

for (nm in combo_names) {{
    combo_dir <- file.path(result_root, nm)
    f <- file.path(combo_dir, "filtered_gene_list.csv")
    if (!file.exists(f)) next

    df <- read.csv(f, check.names = FALSE, stringsAsFactors = FALSE)
    sym_col <- grep("^(Geneid|Gene_Symbol|SYMBOL)$", names(df), ignore.case=TRUE, value=TRUE)[1]
    if (is.na(sym_col)) next

    genes <- unique(na.omit(trimws(as.character(df[[sym_col]]))))
    if (length(genes) < 2) next

    gene_str <- paste(genes, collapse=",")

    cmd <- sprintf('string protein query query="%s" taxonID=%d cutoff=%s limit=%d',
                   gene_str, {taxon_id}, {cutoff}, {limit})
    commandsRun(cmd)

    net_suid <- getNetworkSuid()
    net_name <- paste0("STRING_", nm)
    renameNetwork(net_name, network=net_suid)

    combo_out <- file.path(out_dir, nm)
    if (!dir.exists(combo_out)) dir.create(combo_out, recursive=TRUE)
    out_file <- file.path(combo_out, paste0("STRING_", nm, ".svg"))
    fitContent()
    exportImage(out_file, type="SVG")
}}
""")

        # Rscript 실행
        result = subprocess.run(["Rscript", r_script_path], capture_output=True, text=True, encoding="utf-8")
        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=result.stderr)

        return JSONResponse(content={"success": True, "message": "STRING network generation completed."})

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))