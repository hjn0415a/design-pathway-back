# Usage:
# Rscript run_gseaplot_term.R input_dir output_dir width height ont idx

args <- commandArgs(trailingOnly=TRUE)
input_dir <- args[1]
output_dir <- args[2]
width <- as.numeric(args[3])
height <- as.numeric(args[4])
ont <- args[5]
idx <- as.numeric(args[6])

library(clusterProfiler)
library(enrichplot)
library(ggplot2)
library(cowplot)

ont_files <- c(BP = "gse_BP.rds", CC = "gse_CC.rds", MF = "gse_MF.rds")
rds_path <- file.path(input_dir, ont_files[[ont]])
if (!file.exists(rds_path)) stop("File does not exist: ", rds_path)

gse <- readRDS(rds_path)
if (!inherits(gse, "gseaResult")) stop("Object is not gseaResult")

res <- as.data.frame(gse@result)
if (nrow(res) == 0) stop("No results available")
if (idx < 1 || idx > nrow(res)) stop(sprintf("idx must be 1 ~ %d", nrow(res)))

term_id <- res$ID[idx]
term_desc <- res$Description[idx]

p <- gseaplot2(gse, geneSetID=term_id, title=term_desc)
out_name <- sprintf("gseaplot_%s_idx%d_%s.svg", ont, idx, gsub("[:/\\\\]+", "_", term_id))
ggsave(file.path(output_dir, out_name), plot=p, width=width, height=height)