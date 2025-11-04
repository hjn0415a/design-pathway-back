# fastapi_app/fastapi_heatmap.py
import os
import subprocess
import tempfile
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/volcano", tags=["R Analysis"])

class VolcanoRequest(BaseModel):
    excel_path: str
    output_svg: str
    fc_cutoff: float
    pval_cutoff: float

@router.post("/")
def run_volcano(req: VolcanoRequest):
    """기본 Volcano Plot"""
    r_code = f"""
library(readr)
library(ggplot2)
data <- read_csv('{req.excel_path}')
data <- data[!is.na(data$foldchange) & data$foldchange > 0, ]
data$log2FC <- log2(data$foldchange)
fc_cutoff <- {req.fc_cutoff}
pval_cutoff <- {req.pval_cutoff}
p_cutoff <- -log10(pval_cutoff)
data$group <- "NS"
data$group[data$log2FC > fc_cutoff & -log10(data$pvalue) > p_cutoff] <- "Up"
data$group[data$log2FC < -fc_cutoff & -log10(data$pvalue) > p_cutoff] <- "Down"
color_palette <- c("NS"="gray","Up"="red","Down"="blue")
volcano_plot <- ggplot(data, aes(x=log2FC, y=-log10(pvalue), color=group)) +
    geom_point(size=2, alpha=0.8) +
    scale_color_manual(values=color_palette) +
    geom_vline(xintercept=c(-fc_cutoff, fc_cutoff), linetype="dashed", color="gray") +
    geom_hline(yintercept=p_cutoff, linetype="dashed", color="gray") +
    labs(title="Volcano Plot", x="log2 Fold Change", y="-log10 pvalue") +
    theme_minimal()
ggsave(filename='{req.output_svg}', plot=volcano_plot, width=8, height=6, dpi=300, device='svg')
"""
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".R", delete=False, encoding="utf-8") as tmp_r:
            tmp_r.write(r_code)
            tmp_r_path = tmp_r.name
        subprocess.run(["Rscript", tmp_r_path], check=True)
        os.remove(tmp_r_path)
        if os.path.exists(req.output_svg):
            return {"status": "success", "output": req.output_svg}
        else:
            raise HTTPException(status_code=500, detail="SVG not created")
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/enhanced")
def run_enhanced_volcano(req: VolcanoRequest):
    """Enhanced Volcano Plot"""
    r_code = f"""
library(readr)
library(EnhancedVolcano)
data <- read_csv('{req.excel_path}')
data <- data[!is.na(data$foldchange) & data$foldchange > 0, ]
data$log2FC <- log2(data$foldchange)
res <- data.frame(log2FoldChange=data$log2FC, pvalue=data$pvalue)
rownames(res) <- data$Gene_Symbol
res <- res[!is.na(res$log2FoldChange) & is.finite(res$log2FoldChange), ]
svg('{req.output_svg}', width=10, height=8)
EnhancedVolcano(res,
    lab=NA,
    x='log2FoldChange',
    y='pvalue',
    pCutoff={req.pval_cutoff},
    FCcutoff={req.fc_cutoff},
    title='Enhanced Plot',
    subtitle='Sample',
    pointSize=2.5,
    labSize=2.5)
dev.off()
"""
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".R", delete=False, encoding="utf-8") as tmp_r:
            tmp_r.write(r_code)
            tmp_r_path = tmp_r.name
        subprocess.run(["Rscript", tmp_r_path], check=True)
        os.remove(tmp_r_path)
        if os.path.exists(req.output_svg):
            return {"status": "success", "output": req.output_svg}
        else:
            raise HTTPException(status_code=500, detail="SVG not created")
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=str(e))