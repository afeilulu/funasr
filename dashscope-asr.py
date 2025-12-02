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
    env_file = f".env.${env}"

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
    ],
)

transcribe_response = Transcription.wait(task=task_response.output.task_id)
if transcribe_response.status_code == HTTPStatus.OK:
    print(json.dumps(transcribe_response.output, indent=4, ensure_ascii=False))
    print("transcription done!")
