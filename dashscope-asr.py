from http import HTTPStatus
from dashscope.audio.asr import Transcription
import dashscope
import os
import json
import sys
from dotenv import load_dotenv

env_file = ".env.dev"
if len(sys.argv) > 1:
    env = sys.argv[1]
    env_file = f".env.{env}"

# 加载.env文件中的环境变量
load_dotenv(dotenv_path=env_file)

# 若没有配置环境变量，请用百炼API Key将下行替换为：dashscope.api_key = "sk-xxx"
dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")

task_response = Transcription.async_call(
    model="fun-asr",
    file_urls=[
        #        "https://dashscope.oss-cn-beijing.aliyuncs.com/samples/audio/paraformer/hello_world_female2.wav",
        #        "https://dashscope.oss-cn-beijing.aliyuncs.com/samples/audio/paraformer/hello_world_male2.wav",
        "https://xbt-platform-public-1301716714.cos.ap-chengdu.myqcloud.com/fd6e48d9-a25d-41da-b9e7-0a7d4a29119e",
        "https://xbt-platform-public-1301716714.cos.ap-chengdu.myqcloud.com/50673451-f7f3-4f5f-a6dd-c2ae89bf50c9",
    ],
    diarization_enabled=True,
    speaker_count=2,
)

transcribe_response = Transcription.wait(task=task_response.output.task_id)
if transcribe_response.status_code == HTTPStatus.OK:
    print(json.dumps(transcribe_response.output, indent=4, ensure_ascii=False))
    print("transcription done!")

# {
#     "task_id": "617e3ff6-0263-4585-88e0-520617ac0dae",
#     "task_status": "SUCCEEDED",
#     "submit_time": "2025-12-03 14:38:53.584",
#     "scheduled_time": "2025-12-03 14:38:53.624",
#     "end_time": "2025-12-03 14:39:00.030",
#     "results": [
#         {
#             "file_url": "https://xbt-platform-public-1301716714.cos.ap-chengdu.myqcloud.com/fd6e48d9-a25d-41da-b9e7-0a7d4a29119e",
#             "transcription_url": "https://dashscope-result-bj.oss-cn-beijing.aliyuncs.com/prod/fun-asr-v1/20251203/14%3A38/97b256ab-0525-44a5-8fa9-822ff347912c-1.json?Expires=1764830339&OSSAccessKeyId=LTAI5tQZd8AEcZX6KZV4G8qL&Signature=D3xY11Xmrxn5Vvlk2eK0vMENgAQ%3D",
#             "subtask_status": "SUCCEEDED"
#         },
#         {
#             "file_url": "https://xbt-platform-public-1301716714.cos.ap-chengdu.myqcloud.com/50673451-f7f3-4f5f-a6dd-c2ae89bf50c9",
#             "transcription_url": "https://dashscope-result-bj.oss-cn-beijing.aliyuncs.com/prod/fun-asr-v1/20251203/14%3A38/d7332465-8ab0-4498-8a8d-ed984c5ca90c-1.json?Expires=1764830339&OSSAccessKeyId=LTAI5tQZd8AEcZX6KZV4G8qL&Signature=XkbqNXcmvH1o3nNuuPraDmXXvTg%3D",
#             "subtask_status": "SUCCEEDED"
#         }
#     ],
#     "task_metrics": {
#         "TOTAL": 2,
#         "SUCCEEDED": 2,
#         "FAILED": 0
#     }
# }
