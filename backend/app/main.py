from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import websocket
from app.routers import gjf
from app.routers import orbital
from app.routers import td
from app.routers import reorg
from app.routers import reorg_extract
from app.routers import remote
from app.routers import preset
from app.routers import terminal
from app.routers import local
from app.routers import soc

app = FastAPI(title="Molecular Lab Suite, MLS V26.9", version="26.9")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载路由
app.include_router(websocket.router, prefix="/ws")
app.include_router(gjf.router, prefix="/ws", tags=["GJF Modify"])
app.include_router(gjf.router, prefix="/api/gjf", tags=["GJF Modify"])
app.include_router(orbital.router, prefix="/ws", tags=["Orbital"])
app.include_router(td.router, prefix="/ws", tags=["TD"])
app.include_router(reorg.router, prefix="/ws", tags=["Reorg"])
app.include_router(reorg_extract.router, prefix="/ws", tags=["ReorgExtract"])
app.include_router(remote.router)
app.include_router(preset.router)
app.include_router(terminal.router, prefix="/ws", tags=["终端"])
app.include_router(remote.router, prefix="/api/remote")
app.include_router(remote.router, prefix="/api/remote/cache")
app.include_router(local.router)
app.include_router(soc.router)

@app.get("/api/health")
async def health():
    return {"status": "ok"}