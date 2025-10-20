import operator
import os
import time
import sys
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
import aiofiles

from redis import asyncio as aioredis
import requests
import json
from urllib.parse import urlparse
from contextlib import asynccontextmanager

# import signal
from consul_service import register_service, deregister_service
from dotenv import load_dotenv

# 加载.env文件中的环境变量
load_dotenv()

# 生产必须是8000端口
service_port = int(os.getenv("SERVICE_PORT", 18000))
service_name = "funasr-api-server"

# Lifespan events for FastAPI
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Register with Consul
    register_service(service_name, service_port)

    yield

    # Shutdown: Deregister from Consul
    deregister_service()


# Create FastAPI app with lifespan events
app = FastAPI(
    title="FunASR API Server", lifespan=lifespan, root_path="/funasr-api-server"
)

# Register signal handlers
# signal.signal(signal.SIGINT, handle_shutdown)
# signal.signal(signal.SIGTERM, handle_shutdown)

# 音频文件存储目录
# AUDIO_DIR = "audio"
AUDIO_DIR = "/root/audio_cache" if sys.platform.startswith('linux') else "D:\\funasr\\audio_cache"
os.makedirs(AUDIO_DIR, exist_ok=True)

# Redis客户端
REDIS_HOST = os.getenv("REDIS_HOST", "192.168.5.5")
REDIS_PORT = os.getenv("REDIS_PORT", 6379)
REDIS_DB = os.getenv("REDIS_DB", 0)
REDIS_PASS = os.getenv("REDIS_PASS", "password")
redis_client = aioredis.Redis(
    host=REDIS_HOST,
    port=int(REDIS_PORT),
    db=int(REDIS_DB),
    decode_responses=True,
    password=REDIS_PASS,
)


class FileUrl(BaseModel):
    timestamp: int
    url: str  # 可以是本地文件路径或URL


class AudioRecognitionRequest(BaseModel):
    customer_id: int  # patientId
    appointment_id: int
    files: list[FileUrl]
    parse: bool
    check_in_time: int


class TaskResponse(BaseModel):
    task_id: str
    message: str


class TaskStatus(BaseModel):
    task_id: str
    status: str
    appointment_id: Optional[int] = None
    files: Optional[str] = None
    speech: Optional[str] = None
    timestamp: Optional[int] = None
    check_in_time: Optional[int] = None


class AnalyzeStatus(BaseModel):
    status: str
    result: Optional[str] = None
    timestamp: Optional[int] = None


def is_valid_url(url: str) -> bool:
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False


async def download_file(url: str, save_path: str):
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        async with aiofiles.open(save_path, "wb") as f:
            await f.write(response.content)
        return True
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Failed to download file: {str(e)}"
        )


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/metrics")
async def metrics():
    return {"info": "nothing"}


@app.get("/")
async def root():
    return {"message": "Hello from FastAPI service registered in Consul!"}


@app.post("/recognize", response_model=TaskResponse)
async def recognize_audio(request: AudioRecognitionRequest):
    # task_id = str(uuid.uuid4())
    task_id = str(request.customer_id)
    appointment_id = str(request.appointment_id)
    output_file_name = f"{task_id}_{appointment_id}.scp"
    output_file = os.path.join(AUDIO_DIR, output_file_name)

    with open(output_file, "w") as f:
        for file in request.files:
            file_path = file.url
            timestamp = file.timestamp
            if is_valid_url(file_path):
                # 处理URL
                file_name = (
                    os.path.basename(urlparse(file_path).path) or f"{task_id}.audio"
                )
                save_path = os.path.join(AUDIO_DIR, file_name)
                await download_file(file_path, save_path)
                file_path = save_path
            elif not os.path.isfile(file_path):
                raise HTTPException(status_code=400, detail="File not found")

            f.write(f"{timestamp} {file_path}\n")
            f.flush()

    status = "idle"
    if request.parse is True:
        status = "pending"

    # 将任务添加到Redis队列
    task_data = {
        "task_id": task_id,
        "appointment_id": appointment_id,
        "files": json.dumps(jsonable_encoder(request.files), ensure_ascii=False),
        "scp_file": output_file,
        "status": status,
        "timestamp": int(time.time()),
        "check_in_time": request.check_in_time,
    }

    key = f"funasr:{task_id}:{appointment_id}"
    await redis_client.hmset(key, task_data)
    if request.parse is True:
        await redis_client.lpush("asr_tasks", key)

    return TaskResponse(task_id=key, message="Task submitted successfully")


@app.get("/statusList/{task_id}", response_model=list[TaskStatus])
async def get_task_list(task_id: str):
    fuzzy_key = f"funasr:{task_id}:*"
    keys = await redis_client.keys(fuzzy_key)
    if not keys:
        raise HTTPException(status_code=404, detail="Task not found")

    res = []
    for key in keys:
        task_data = await redis_client.hgetall(key)
        res.append(
            TaskStatus(
                task_id=task_id,
                appointment_id=task_data.get("appointment_id"),
                files=task_data.get("files"),
                status=task_data.get("status", "unknown"),
                speech=task_data.get("speech"),
                timestamp=task_data.get("timestamp"),
                check_in_time=task_data.get("check_in_time") or int(time.time()),
            )
        )

    sorted_res = sorted(res, key=operator.attrgetter("check_in_time"), reverse=True)
    return sorted_res


@app.get("/status/{task_id}/{appointment_id}", response_model=TaskStatus)
async def get_task(task_id: str, appointment_id: str):
    key = f"funasr:{task_id}:{appointment_id}"
    task_data = await redis_client.hgetall(key)
    if not task_data:
        raise HTTPException(status_code=404, detail="Task not found")

    return TaskStatus(
        task_id=task_id,
        appointment_id=appointment_id,
        files=task_data.get("files"),
        status=task_data.get("status", "unknown"),
        speech=task_data.get("speech"),
        timestamp=task_data.get("timestamp"),
    )


@app.get("/getAnalyzeStatus/{task_id}", response_model=AnalyzeStatus)
async def get_analyze_status(task_id: str):
    key = f"ana:{task_id}"
    task_data = await redis_client.hgetall(key)
    if not task_data:
        raise HTTPException(status_code=404, detail="Task not found")

    return AnalyzeStatus(
        status=task_data.get("status", "unknown"),
        result=task_data.get("result"),
        timestamp=task_data.get("timestamp"),
    )


@app.get("/analyze/{task_id}", response_model=TaskResponse)
async def analyze(task_id: str):
    key = f"ana:{task_id}"

    # 更新任务状态为排队中
    redis_client.hset(key, "status", "pending")
    redis_client.hset(key, "timestamp", int(time.time()))
    redis_client.lpush("asr_tasks", key)
    return TaskResponse(task_id=key, message="Task submitted successfully")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=service_port)
