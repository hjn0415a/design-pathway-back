#!/usr/bin/env Rscript
args <- commandArgs(trailingOnly = TRUE)

if (length(args) < 7) {
  stop("Usage: Rscript run_emapplot.R <result_root> <figure_root> <combo_vec> <show_n> <width> <height>")
}

result_root <- args[[1]]
figure_root <- args[[2]]
combo_vec   <- eval(parse(text = args[[3]]))
show_n      <- as.numeric(args[[4]])
width       <- as.numeric(args[[5]])
height      <- as.numeric(args[[6]])

suppressPackageStartupMessages({
  library(clusterProfiler)
  library(enrichplot)
  library(ggplot2)
  library(svglite)
})

make_find_ego <- function(combo_dir, ont) {
  direct <- file.path(combo_dir, sprintf("GO_%s_ego.rds", ont))
  if (file.exists(direct)) return(direct)
  cand <- list.files(combo_dir,
                     pattern = paste0("^GO_", ont, "_ego\\.rds$"),
                     recursive = TRUE, full.names = TRUE)
  if (length(cand) >= 1) return(cand[1])
  return(NA_character_)
}

make_emap_from_rds_by_combo <- function(result_root,
                                        figure_root,
                                        combo_names,
                                        onts     = c("BP","CC","MF"),
                                        show_n   = 5,
                                        width    = 7,
                                        height   = 7,
                                        pie      = FALSE,
                                        layout   = "kk") {
  if (!dir.exists(figure_root)) dir.create(figure_root, recursive = TRUE)

  for (nm in combo_names) {
    combo_dir <- file.path(result_root, nm)
    out_dir   <- file.path(figure_root, nm)
    if (!dir.exists(out_dir)) dir.create(out_dir, recursive = TRUE)

    for (ont in onts) {
      rds_path <- make_find_ego(combo_dir, ont)
      if (is.na(rds_path)) next

      ego <- readRDS(rds_path)
      if (is.null(ego) || is.null(ego@result) || nrow(ego@result) < 2) next

      ego_sim <- tryCatch(pairwise_termsim(ego), error = function(e) NULL)
      if (is.null(ego_sim) || is.null(ego_sim@result) || nrow(ego_sim@result) < 2) next

      k <- min(show_n, nrow(ego_sim@result))
      p <- emapplot(ego_sim, showCategory = k, layout = layout, pie = pie)

      out_svg <- file.path(out_dir, sprintf("emap_%s.svg", ont))
      ggsave(out_svg, p, width = width, height = height, device = svglite::svglite)
    }
  }
}

make_emap_from_rds_by_combo(result_root, figure_root, combo_vec,
                            show_n = show_n, width = width, height = height)