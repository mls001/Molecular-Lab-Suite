from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import websocket
from app.routers import gjf
from app.routers import orbital  # 新增导入


app = FastAPI(title="Molecular Lab Suite, MLS V26.9", version="26.9")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(websocket.router, prefix="/ws")
app.include_router(gjf.router, prefix="/ws", tags=["GJF Modify"])
app.include_router(gjf.router, prefix="/api/gjf", tags=["GJF Modify"])
app.include_router(orbital.router, prefix="/ws", tags=["Orbital"])


@app.get("/api/health")
async def health():
    return {"status": "ok"}
