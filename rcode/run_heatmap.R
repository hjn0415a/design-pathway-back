#!/usr/bin/env Rscript

args <- commandArgs(trailingOnly = TRUE)
csv_path <- args[1]
width <- as.numeric(args[2])
height <- as.numeric(args[3])
top_n_genes <- as.numeric(args[4])
output_path <- args[5]

library(pheatmap)
library(readr)
library(svglite)

data <- read_csv(csv_path)
gene_names <- data[[1]]
data <- data[, -1]
sample_cols <- grep("([0-9]+$)", names(data), value = TRUE)
mat <- as.matrix(data[, sample_cols, drop = FALSE])
rownames(mat) <- gene_names
annotation_col <- data.frame(
  Group = factor(sub("(_[0-9]+$)|([0-9]+$)", "", sample_cols)),
  row.names = sample_cols
)

svglite(output_path, width = width, height = height)
pheatmap(
  mat[order(data$pvalue)[1:top_n_genes], , drop = FALSE],
  scale = "row",
  clustering_distance_rows = "euclidean",
  clustering_distance_cols = "euclidean",
  clustering_method = "complete",
  show_rownames = TRUE,
  show_colnames = TRUE,
  annotation_col = annotation_col,
  color = colorRampPalette(c("#6699e0", "white", "#e06666"))(100)
)
dev.off()