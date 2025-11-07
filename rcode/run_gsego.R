#!/usr/bin/env Rscript

# Load required libraries
suppressMessages({
  library(clusterProfiler)
  library(org.Hs.eg.db)
  library(org.Mm.eg.db)
  library(enrichplot)
  library(ggplot2)
  library(dplyr)
  library(readr)
})

# Get command line arguments
args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 6) {
  stop("Usage: Rscript run_gsego.R <file_path> <out_dir> <orgdb> <minGSSize> <maxGSSize> <pvalueCutoff>")
}

file_path <- args[1]
out_dir <- args[2]
orgdb <- args[3]
minGSSize <- as.numeric(args[4])
maxGSSize <- as.numeric(args[5])
pvalueCutoff <- as.numeric(args[6])

# Ensure output directory exists
if (!dir.exists(out_dir)) {
  dir.create(out_dir, recursive = TRUE)
}

# Load input data
df <- read_csv(file_path)
if (!all(c("gene", "logFC") %in% names(df))) {
  stop("Input CSV must contain 'gene' and 'logFC' columns")
}

geneList <- df$logFC
names(geneList) <- df$gene
geneList <- sort(geneList, decreasing = TRUE)

# Select OrgDb dynamically
OrgDb <- get(orgdb)

# Run GSEA
ontologies <- c("BP", "CC", "MF")
for (ont in ontologies) {
  gsea_result <- gseGO(
    geneList     = geneList,
    OrgDb        = OrgDb,
    ont          = ont,
    minGSSize    = minGSSize,
    maxGSSize    = maxGSSize,
    pvalueCutoff = pvalueCutoff,
    verbose      = FALSE
  )

  # Save CSV
  output_csv <- file.path(out_dir, paste0("gse_", ont, ".csv"))
  write.csv(as.data.frame(gsea_result), output_csv, row.names = FALSE)

  # Save plot
  output_plot <- file.path(out_dir, paste0("gseaplot_", ont, ".svg"))
  gseaplot2(gsea_result, geneSetID = 1, title = ont)
  ggsave(output_plot, width = 8, height = 6)
}