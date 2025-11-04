from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import (
    fastapi_heatmap,
    fastapi_volcano,
    fastapi_pca,
    fastapi_deg,
    fastapi_enrichplot,
    fastapi_cnetplot,
    fastapi_emapplot,
    fastapi_gsego,
    fastapi_ridgeplot,
    fastapi_pathway_gene,
    fastapi_upload,
)

app = FastAPI(
    title="Omics Analysis API",
    description="Provides endpoints for heatmap, volcano, and STRING network analysis",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(fastapi_heatmap.router, prefix="/api", tags=["Heatmap"])
app.include_router(fastapi_volcano.router, prefix="/api", tags=["Volcano"])
app.include_router(fastapi_pca.router, prefix="/api", tags=["PCA"])
app.include_router(fastapi_deg.router, prefix="/api", tags=["DEG"])
app.include_router(fastapi_enrichplot.router, prefix="/api", tags=["Enrichplot"])
app.include_router(fastapi_cnetplot.router, prefix="/api", tags=["Cnetplot"])
app.include_router(fastapi_emapplot.router, prefix="/api", tags=["Emapplot"])
app.include_router(fastapi_gsego.router, prefix="/api", tags=["GSEGO"])
app.include_router(fastapi_ridgeplot.router, prefix="/api", tags=["Ridgeplot"])
app.include_router(fastapi_pathway_gene.router, prefix="/api", tags=["Pathway Gene"])
app.include_router(fastapi_upload.router, prefix="/api", tags=["Upload CSV"])

@app.get("/")
def root():
    return {"message": "FastAPI backend is running successfully 🚀"}