# backend/routes/fastapi_pathway_gene.py
import os
import tempfile
import subprocess
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import zipfile
import io

router = APIRouter(
    prefix="/pathway_gene",
    tags=["PathwayGene"]
)

class PathwayGeneRequest(BaseModel):
    edox_dir: str
    csv_path: str
    output_dir: str
    top_pathways: int = 5
    top_genes_per_pathway: int = 20
    width: float = 12.0
    height: float = 6.0

@router.post("/", response_class=None)  # ZIP 바이너리 반환
def run_pathway_heatplot(request: PathwayGeneRequest):
    edox_dir = request.edox_dir
    csv_path = request.csv_path
    output_dir = request.output_dir
    top_pathways = request.top_pathways
    top_genes = request.top_genes_per_pathway
    width = request.width
    height = request.height
    max_setsize = 50

    if not os.path.exists(csv_path):
        raise HTTPException(status_code=400, detail=f"CSV file not found: {csv_path}")
    if not os.path.exists(edox_dir):
        raise HTTPException(status_code=400, detail=f"Edox directory not found: {edox_dir}")
    os.makedirs(output_dir, exist_ok=True)

    # 임시 R 스크립트 생성
    with tempfile.NamedTemporaryFile(mode="w", suffix=".R", delete=False, encoding="utf-8") as tmp_r:
        r_script_path = tmp_r.name
        tmp_r.write(f"""
library(clusterProfiler)
library(enrichplot)
library(ggplot2)
library(cowplot)
library(org.Hs.eg.db)

csv_path <- "{csv_path}"
edox_dir <- "{edox_dir}"
out_dir <- "{output_dir}"
top_pathways <- {top_pathways}
top_genes <- {top_genes}
max_setsize <- {max_setsize}

df <- read.csv(csv_path, check.names=FALSE, stringsAsFactors=FALSE)
stopifnot("Geneid" %in% names(df), "foldchange" %in% names(df))
fc_vec <- setNames(log2(df$foldchange + 1e-8), df$Geneid)
fc_vec <- fc_vec[is.finite(fc_vec)]

harmonize_fc <- function(edox, fc_named) {{
  core_ids <- unique(unlist(strsplit(edox@result$core_enrichment, "/")))
  if(length(core_ids) == 0 || all(is.na(core_ids))) return(fc_named)
  if(sum(names(fc_named) %in% core_ids) > 0) return(fc_named)
  is_entrez <- all(grepl("^[0-9]+$", head(core_ids[!is.na(core_ids)], 50)))
  if(is_entrez) {{
    mp <- suppressMessages(bitr(names(fc_named), fromType="SYMBOL", toType="ENTREZID", OrgDb=org.Hs.eg.db))
    if(!nrow(mp)) return(numeric(0))
    mp <- mp[!duplicated(mp$SYMBOL), ]
    out <- fc_named[mp$SYMBOL]; names(out) <- mp$ENTREZID
    out[!is.na(names(out))]
  }} else {{
    mp <- suppressMessages(bitr(names(fc_named), fromType="ENTREZID", toType="SYMBOL", OrgDb=org.Hs.eg.db))
    if(!nrow(mp)) return(numeric(0))
    mp <- mp[!duplicated(mp$ENTREZID), ]
    out <- fc_named[mp$ENTREZID]; names(out) <- mp$SYMBOL
    out[!is.na(names(out))]
  }}
}}

files <- c(BP="gse_BP.rds", CC="gse_CC.rds", MF="gse_MF.rds")

for(ont in names(files)) {{
  rds <- file.path(edox_dir, files[ont])
  if(!file.exists(rds)) next
  edox <- try(readRDS(rds), silent=TRUE)
  if(inherits(edox, "try-error") || nrow(edox@result) == 0) next
  if(!is.null(max_setsize) && "setSize" %in% names(edox@result)) {{
    edox@result <- edox@result[edox@result$setSize <= max_setsize, , drop=FALSE]
    if(nrow(edox@result)==0) next
  }}
  fc_use <- harmonize_fc(edox, fc_vec)
  if(!length(fc_use)) next
  fc_use <- fc_use[is.finite(fc_use)]
  res_top <- head(edox@result[order(edox@result$p.adjust), , drop=FALSE], top_pathways)
  core_top <- unique(unlist(strsplit(res_top$core_enrichment, "/")))
  fc_use <- fc_use[names(fc_use) %in% core_top]
  fc_use <- fc_use[order(abs(fc_use), decreasing=TRUE)]
  fc_use <- head(fc_use, top_genes)
  
  p1 <- heatplot(edox, showCategory=top_pathways) + theme(axis.text.x=element_text(angle=45,hjust=1,size=7))
  p2 <- heatplot(edox, foldChange=fc_use, showCategory=top_pathways) + theme(axis.text.x=element_text(angle=45,hjust=1,size=7))
  
  g <- cowplot::plot_grid(p1, p2, ncol=1, labels=c("A","B"))
  ggsave(file.path(out_dir, sprintf("heatplot_%s_top%dgenes.svg", ont, top_genes)), g, width={width}, height={height})
}}
""")

    # Rscript 실행
    try:
        subprocess.run(["Rscript", r_script_path], check=True, text=True)
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"R script execution failed: {e}")
    finally:
        os.remove(r_script_path)

    # 생성된 SVG들을 ZIP으로 반환
    svg_files = [os.path.join(output_dir, f) for f in os.listdir(output_dir) if f.endswith(".svg")]
    if not svg_files:
        raise HTTPException(status_code=500, detail="No heatplot SVGs generated.")

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zipf:
        for f in svg_files:
            zipf.write(f, arcname=os.path.basename(f))
    zip_buffer.seek(0)
    return zip_buffer.read()