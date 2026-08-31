from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
import glob
from app.core.mm_optimizer import run_mol_optimize_stream

router = APIRouter()


class OptimizeRequest(BaseModel):
    input_folder: str
    output_folder: str
    prefix: str = "opt_"
    ff: str = "MMFF94"
    maxiter: int = 500
    embed: bool = True
    add_h: bool = True
    charge: str = "0"
    mult: str = "1"
    keyword: str = "#p opt b3lyp/6-31g(d,p)"
    mem: str = "20GB"
    nproc: str = "8"


@router.post("/run")
async def run_optimize(request: OptimizeRequest):
    """直接使用路径启动优化（同步执行）"""
    if not os.path.isdir(request.input_folder):
        raise HTTPException(status_code=400, detail="输入文件夹不存在")
    # 检查 .mol 文件
    mol_files = glob.glob(os.path.join(request.input_folder, "*.mol"))
    if not mol_files:
        raise HTTPException(status_code=400, detail="未找到 .mol 文件")

    # 创建输出目录
    os.makedirs(request.output_folder, exist_ok=True)

    # 执行优化生成器，这里由于是普通路由，无法实时推送，我们可以改为 WebSocket 方式
    # 或者直接返回最终结果，但实时推送更适合 WebSocket
    # 我们保留 WebSocket 用于实时更新，此接口可改为启动任务后返回 task_id
    # 建议直接使用 WebSocket 方式，前端连接后发送参数
    return {"message": "优化任务已启动，请通过 WebSocket 接收进度"}