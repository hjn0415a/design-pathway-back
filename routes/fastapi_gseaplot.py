# fastapi_gseaplot.py
from fastapi import APIRouter
from pydantic import BaseModel
import subprocess
import os
import tempfile

router = APIRouter(prefix="/run-gseaplot", tags=["GSEA Plot"])

class GSEAPayload(BaseModel):
    input_dir: str
    output_dir: str
    topN: int = 10
    width: float = 12.0
    height: float = 8.0
    ont: str = "BP"
    idx: int = 1

# ----------------- Total gseaplot2 -----------------
@router.post("/total")
def run_gseaplot_total(payload: GSEAPayload):
    os.makedirs(payload.output_dir, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".R", delete=False, encoding="utf-8") as tmp_r:
        r_script_path = tmp_r.name
        tmp_r.write(f"""
library(clusterProfiler)
library(enrichplot)
library(ggplot2)

input_dir <- "{payload.input_dir}"
output_dir <- "{payload.output_dir}"
topN <- {payload.topN}
width <- {payload.width}
height <- {payload.height}

files <- c(BP = "gse_BP.rds", CC = "gse_CC.rds", MF = "gse_MF.rds")

for (ont in names(files)) {{
    rds_path <- file.path(input_dir, files[ont])
    if (!file.exists(rds_path)) next

    gse <- try(readRDS(rds_path), silent=TRUE)
    if (inherits(gse, "try-error") || !inherits(gse, "gseaResult")) next
    if (is.null(gse@result) || nrow(gse@result) == 0) next

    res <- as.data.frame(gse@result)
    res[] <- lapply(res, function(x) if (inherits(x, "Rle")) as.vector(x) else x)

    if (!all(c("ID","p.adjust") %in% names(res))) next
    res$p.adjust <- suppressWarnings(as.numeric(res$p.adjust))
    ord <- order(res$p.adjust, na.last = NA)
    if (!length(ord)) next
    sel <- ord[ seq_len(min(topN, length(ord))) ]
    ids <- res$ID[sel]

    p <- gseaplot2(gse, geneSetID=ids, pvalue_table=TRUE,
                   title=sprintf("Top %d enriched GO:%s terms", length(ids), ont))

    ggsave(file.path(output_dir, sprintf("gseaplot2_%s_top%d.svg", ont, length(ids))),
           plot=p, width=width, height=height)
}}
""")
    result = subprocess.run(["Rscript", r_script_path], capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        return {"error": result.stderr}
    return {"message": "Total gseaplot2 generation completed!"}

# ----------------- GSEA Term Plot -----------------
@router.post("/term")
def run_gseaplot_term(payload: GSEAPayload):
    os.makedirs(payload.output_dir, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".R", delete=False, encoding="utf-8") as tmp_r:
        r_script_path = tmp_r.name
        tmp_r.write(f"""
library(clusterProfiler)
library(enrichplot)
library(ggplot2)
library(cowplot)

input_dir <- "{payload.input_dir}"
output_dir <- "{payload.output_dir}"
ont <- "{payload.ont}"
idx <- {payload.idx}
width <- {payload.width}
height <- {payload.height}

ont_files <- c(BP = "gse_BP.rds", CC = "gse_CC.rds", MF = "gse_MF.rds")
rds_path <- file.path(input_dir, ont_files[[ont]])
if (!file.exists(rds_path)) stop("파일이 존재하지 않습니다: ", rds_path)

gse <- readRDS(rds_path)
if (!inherits(gse, "gseaResult")) stop("읽은 객체가 gseaResult가 아닙니다.")

res <- as.data.frame(gse)
if (nrow(res) == 0) stop("결과가 비어 있습니다.")
if (idx < 1 || idx > nrow(res)) stop(sprintf("idx 범위는 1 ~ %d 입니다.", nrow(res)))

term_id <- res$ID[idx]
term_desc <- res$Description[idx]

p <- gseaplot2(gse, geneSetID=term_id, title=term_desc)
out_name <- sprintf("gseaplot_%s_idx%d_%s.svg", ont, idx, gsub("[:/\\\\]+", "_", term_id))
ggsave(file.path(output_dir, out_name), plot=p, width=width, height=height)
""")
    result = subprocess.run(["Rscript", r_script_path], capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        return {"error": result.stderr}
    return {"message": f"GSEA Term plot ({payload.ont}, idx={payload.idx}) completed!"}