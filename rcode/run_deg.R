args <- commandArgs(trailingOnly = TRUE)

if (length(args) < 4) {
  stop("Usage: Rscript run_deg.R <csv_path> <fc_input> <pval_input> <result_dir>")
}

csv_path <- args[1]
fc_input <- args[2]
pval_input <- args[3]
result_dir <- args[4]

# 문자열을 벡터로 변환
fc_thresholds <- as.numeric(strsplit(fc_input, ",")[[1]])
pval_thresholds <- as.numeric(strsplit(pval_input, ",")[[1]])

save_filtered_results <- function(csv_path, fc_thresholds, pval_thresholds, result_dir) {
  gene_data <- read.csv(csv_path, stringsAsFactors = FALSE)
  if (!dir.exists(result_dir)) dir.create(result_dir, recursive = TRUE)

  combo_names <- character()

  for (fc_cut in fc_thresholds) {
    for (p_cut in pval_thresholds) {
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
    }
  }

  write.csv(data.frame(combo = combo_names),
            file = file.path(result_dir, "combo_names.csv"), row.names = FALSE)
}

save_filtered_results(csv_path, fc_thresholds, pval_thresholds, result_dir)