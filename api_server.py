import operator
import os
import time
import sys
import sca
from typing import Optional
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import aiofiles

from redis import asyncio as aioredis
import requests
from urllib.parse import urlparse
from contextlib import asynccontextmanager

# import signal
from consul_service import register_service, deregister_service
from dotenv import load_dotenv

env_file = ".env.dev"
if len(sys.argv) > 1:
    env = sys.argv[1]
    env_file = f".env.{env}"

# 加载.env文件中的环境变量
load_dotenv(dotenv_path=env_file)

# 生产必须是8000端口
service_port = int(os.getenv("SERVICE_PORT", 8000))
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
AUDIO_DIR = (
    "/root/audio_cache"
    if sys.platform.startswith("linux")
    else "D:\\funasr\\audio_cache"
)
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
    patient_id: int
    appointment_id: int
    file: str
    parse: bool
    check_in_time: int


class TaskResponse(BaseModel):
    task_id: str
    message: str


class TaskStatus(BaseModel):
    task_id: str
    status: str
    appointment_id: Optional[int] = None
    file: Optional[str] = None
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
    task_id = str(request.patient_id)
    timestamp = int(time.time())
    appointment_id = str(request.appointment_id)

    status = "pending"

    # 将任务添加到Redis队列
    key = f"funasr:{task_id}:{timestamp}"
    task_data = {
        "patient_id": task_id,
        "appointment_id": appointment_id,
        "file": request.file,
        "status": status,
        "timestamp": int(time.time()),
        "check_in_time": request.check_in_time,
    }
    await redis_client.hset(key, mapping=task_data)  # type: ignore # 必须写mapping=

    if request.parse is True:
        await redis_client.lpush("asr_tasks", key)  # type: ignore

    return TaskResponse(task_id=key, message="Task submitted successfully")


@app.get("/statusList/{task_id}", response_model=list[TaskStatus])
async def get_task_list(task_id: str):
    fuzzy_key = f"funasr:{task_id}:*"
    keys = await redis_client.keys(fuzzy_key)
    if not keys:
        raise HTTPException(status_code=404, detail="Task not found")

    res = []
    for key in keys:
        task_data = await redis_client.hgetall(key)  # type: ignore
        res.append(
            TaskStatus(
                task_id=task_id,
                appointment_id=task_data.get("appointment_id"),
                file=task_data.get("file"),
                status=task_data.get("status", "unknown"),
                speech=task_data.get("speech"),
                timestamp=task_data.get("timestamp"),
                check_in_time=task_data.get("check_in_time") or int(time.time()),
            )
        )

    sorted_res = sorted(res, key=operator.attrgetter("check_in_time"), reverse=True)
    return sorted_res


@app.get("/status/{task_id}/{timestamp}", response_model=TaskStatus)
async def get_task(task_id: str, timestamp: str):
    key = f"funasr:{task_id}:{timestamp}"
    task_data = await redis_client.hgetall(key)  # type: ignore
    if not task_data:
        raise HTTPException(status_code=404, detail="Task not found")

    return TaskStatus(
        task_id=task_id,
        appointment_id=task_data.get("appointment_id"),
        file=task_data.get("file"),
        status=task_data.get("status", "unknown"),
        speech=task_data.get("speech"),
        timestamp=task_data.get("timestamp"),
    )


@app.get("/getAnalyzeStatus/{task_id}", response_model=AnalyzeStatus)
async def get_analyze_status(task_id: str):
    key = f"ana:{task_id}"
    task_data = await redis_client.hgetall(key)  # type: ignore
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
    await redis_client.hset(key, "status", "pending")  # type: ignore
    await redis_client.hset(key, "timestamp", int(time.time()))  # type: ignore
    await redis_client.lpush("asr_tasks", key)  # type:ignore
    return TaskResponse(task_id=key, message="Task submitted successfully")


# sca #####################################################################################


@app.get("/sca/callback")
async def sca_call_back(request: Request):
    # http://aliyun.com/callback?taskId=xxx&timestamp=xxx&aliUid=xxx&signature=xxx&event=xxx
    params = dict(request.query_params)
    print("/sca/callback")
    print(params.get("taskId"))
    print(params.get("timestamp"))
    print(params.get("aliUid"))
    print(params.get("signature"))
    print(params.get("event"))


class ScaUploadRequest(BaseModel):
    voiceFileUrl: str
    fileName: str
    patientId: str


@app.post("/sca/upload")
async def sca_upload(request: ScaUploadRequest):
    resp = sca.Sample.uploadAudio(
        request.voiceFileUrl, request.fileName, request.patientId
    )

    if resp is not None:
        # resp.data = taskId
        key = f"sca:{request.patientId}:{resp.data}"
        await redis_client.hset(key, "url", request.voiceFileUrl)  # type:ignore
        await redis_client.hset(key, "fileName", request.fileName)  # type: ignore
        await redis_client.hset(key, "taskId", resp.data)  # type:ignore
        await redis_client.hset(key, "timestamp", str(int(time.time())))  # type:ignore

    return resp


class ScaTaskIdsResponse(BaseModel):
    url: str | None
    fileName: str | None
    taskId: str | None
    vid: str | None
    timestamp: str | None


@app.get("/sca/taskIds")
async def sca_taskIds(patientId: str) -> list[ScaTaskIdsResponse]:
    resp = []
    fuzzy_key = f"sca:{patientId}:*"
    keys = await redis_client.keys(fuzzy_key)
    if keys:
        for key in keys:
            raw = await redis_client.hgetall(key)  # type:ignore
            if raw:
                resp.append(
                    ScaTaskIdsResponse(
                        url=raw.get("url"),
                        fileName=raw.get("fileName"),
                        taskId=raw.get("taskId"),
                        vid=raw.get("vid"),
                        timestamp=raw.get("timestamp"),
                    )
                )

    return resp


@app.get("/sca/getResult")
async def sca_get_result(patientId: str, taskId: str):
    resp = sca.Sample.getResult(taskId, patientId)

    if resp is not None:
        for info in resp.data.result_info:
            key = f"sca:{patientId}:{info.task_id}"
            await redis_client.hset(key, "vid", info.vid)  # type:ignore
    else:
        raise HTTPException(status_code=404, detail="Item not found")

    return resp


@app.get("/sca/getResultToView")
async def sca_get_result_to_view(taskId: str, vid: str):
    resp = sca.Sample.getResultToReview(taskId, vid)
    if resp is None:
        raise HTTPException(status_code=404, detail="Item not found")

    return resp


if __name__ == "__main__":
    if os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_ID") is None:
        print("请设置环境变量ALIBABA_CLOUD_ACCESS_KEY_ID")
        sys.exit(1)

    if os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_SECRET") is None:
        print("请设置环境变量ALIBABA_CLOUD_ACCESS_KEY_SECRET")
        sys.exit(1)

    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=service_port)
