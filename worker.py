import os
import typer
import redis
import json
import sys
import logging
from concurrent.futures import ThreadPoolExecutor
from funasr import AutoModel
from dify import dify_post, parse_dify_any
from common import merge_consecutive_items, read_and_join_file, split_and_save_json_list
from dotenv import load_dotenv

from parallel import get_urls_content
# from funasr.utils.postprocess_utils import rich_transcription_postprocess

logger = logging.getLogger()
logger.setLevel(logging.WARNING)

app = typer.Typer()

# 加载.env文件中的环境变量
load_dotenv()

# 配置
MODEL_DIR = (
    "/root/model_cache"
    if sys.platform.startswith("linux")
    else "D:\\funasr\\model_cache"
)
MAX_WORKERS = 100  # 最大并发处理数量
cpu_cores = os.cpu_count()

logger.warn(f"CPU_CORES={cpu_cores}")
logger.warn(f"Starting worker with {MAX_WORKERS} concurrent tasks...")

# 设置模型缓存路径
# os.environ["MODELSCOPE_CACHE"] = os.path.dirname(os.path.abspath(__file__))
os.environ["MODELSCOPE_CACHE"] = MODEL_DIR

# ffmpeg配置
# FFMPEG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffmpeg.exe")
FFMPEG_PATH = "/usr/bin/ffmpeg" if sys.platform.startswith("linux") else "./ffmpeg.exe"

# 模型热词
hotword = read_and_join_file("./hotword")

# Redis客户端
REDIS_HOST = os.getenv("REDIS_HOST", "192.168.5.5")
REDIS_PORT = os.getenv("REDIS_PORT", 6379)
REDIS_DB = os.getenv("REDIS_DB", 0)
REDIS_PASS = os.getenv("REDIS_PASS", "password")
redis_client = redis.Redis(
    host=REDIS_HOST,
    port=int(REDIS_PORT),
    db=int(REDIS_DB),
    decode_responses=True,
    password=REDIS_PASS,
)


def download_model():
    """下载模型"""
    try:
        if os.path.exists(MODEL_DIR) and os.listdir(MODEL_DIR):
            print("Model already exists, skipping download...")
            return True

        os.makedirs(MODEL_DIR, exist_ok=True)
        print("Downloading model...")

        # 初始化模型会自动下载
        AutoModel(
            model="paraformer-zh",
            model_revision="v2.0.4",
            vad_model="fsmn-vad",
            vad_model_revision="v2.0.4",
            punc_model="ct-punc-c",
            punc_model_revision="v2.0.4",
            spk_model="cam++",
            spk_model_revision="v2.0.2",
            disable_update=True,
            use_itn=True,
            device="cuda" if torch.cuda.is_available() else "cpu",
            ffmpeg_path=FFMPEG_PATH,
            ncpu=cpu_cores,
        )
        return True
    except Exception as e:
        print(f"Error downloading model: {str(e)}")
        return False


def process_audio(key: str, file_path: str, model):
    """处理scp文件"""
    try:
        # 更新任务状态为处理中
        redis_client.hset(key, "status", "processing")

        # 执行语音识别
        result = model.generate(
            input=file_path,
            hotword=hotword,
            batch_size_s=300,
        )
        # text = rich_transcription_postprocess(result[0]["text"])
        # print(text)
        # text_result = text

        messages = []
        for stage in result:
            # speech_list = stage["sentence_info"]
            # for item in speech_list:
            #     del item["timestamp"]
            speech_list = merge_consecutive_items(stage["sentence_info"])

            # file_name = f"{key}.json".replace(':',"_")
            # file_path = save_file(speech_list, file_name, output_dir="results")
            # url = upload_file(file_name, file_path)

            base_filename = key.replace(":", "_")
            urls = split_and_save_json_list(
                speech_list, base_filename=base_filename, output_dir="results"
            )

            speech = []

            # 获取URL内容
            contents = get_urls_content(urls, timeout=3000, max_concurrent=len(urls))

            # 打印结果
            for url, content in zip(urls, contents):
                if content is not None:
                    if content.startswith("error:"):
                        print(f"{url} -> {content}")
                    else:
                        speech.extend(json.loads(content))
                else:
                    print(f"{url} -> 请求失败")

            if speech:
                messages.append(speech)

        # 更新任务对话解析结果
        redis_client.hmset(
            key,
            {"status": "completed", "speech": json.dumps(messages, ensure_ascii=False)},
        )

        return True
    except Exception as e:
        print(f"Error processing task {key}: {str(e)}")
        redis_client.hmset(key, {"status": "failed", "result": str(e)})
        return False


def analyze(task_id: str):
    key = f"ana:{task_id}"
    try:
        # 更新任务状态为处理中
        redis_client.hset(key, "status", "processing")

        # 获取历史所有对话
        fuzzy_key = f"funasr:{task_id}:*"
        keys = redis_client.keys(fuzzy_key)
        all_speech = []
        for sub_key in keys:
            print(sub_key)
            sub_task_data = redis_client.hgetall(sub_key)
            if sub_task_data:
                speech_text = sub_task_data.get("speech")
                speech_list = json.loads(str(speech_text))
                all_speech.extend(speech_list)

        if len(all_speech) == 0:
            redis_client.hmset(
                key, {"status": "failed", "result": "lack of information"}
            )
            return False

        # 分析对话
        json_data_ana = dify_post(
            "app-TlgE19fpgxhpQB9yOA3RBfj8",
            "chatContent",
            key,
            json.dumps(all_speech, ensure_ascii=False),
        )
        if json_data_ana:
            ana_str = json_data_ana["data"]["outputs"]["text"]
            print(ana_str)
            text_result = parse_dify_any(ana_str)

            # 更新分析结果
            redis_client.hmset(
                key,
                {
                    "status": "completed",
                    "result": json.dumps(text_result, ensure_ascii=False),
                },
            )
            return True

        return False
    except Exception as e:
        print(f"Error processing analyze {key}: {str(e)}")
        res = {"status": "failed", "result": str(e)}
        redis_client.hmset(key, res)
        return False


def start_worker():
    """启动工作进程"""
    print("Initializing ASR model...")
    # model = AutoModel(
    #     model=f"{MODEL_DIR}/models/iic/speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
    #     punc_model=f"{MODEL_DIR}/models/iic/punc_ct-transformer_zh-cn-common-vocab272727-pytorch",
    #     vad_model=f"{MODEL_DIR}/models/iic/speech_fsmn_vad_zh-cn-16k-common-pytorch",
    #     spk_model=f"{MODEL_DIR}/models/iic/speech_campplus_sv_zh-cn_16k-common",
    #     disable_update=True,
    #     device="cuda" if torch.cuda.is_available() else "cpu",
    #     ffmpeg_path=FFMPEG_PATH,
    #     ncpu=cpu_cores
    # )
    model = AutoModel(
        model="paraformer-zh",
        model_revision="v2.0.4",
        vad_model="fsmn-vad",
        vad_model_revision="v2.0.4",
        punc_model="ct-punc-c",
        punc_model_revision="v2.0.4",
        spk_model="cam++",
        spk_model_revision="v2.0.2",
        disable_update=True,
        use_itn=True,
        device="cuda" if torch.cuda.is_available() else "cpu",
        ffmpeg_path=FFMPEG_PATH,
        ncpu=cpu_cores,
    )

    #    print(f"CPU_CORES={cpu_cores}")
    #    print(f"Starting worker with {MAX_WORKERS} concurrent tasks...")
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        while True:
            # 从队列中获取任务
            task = redis_client.brpop(["asr_tasks"], timeout=1)
            if task is None:
                continue

            key = task[1]  # brpop returns tuple (queue_name, value)
            task_data = redis_client.hgetall(key)

            if not task_data:
                print(f"Task {key} not found in Redis")
                continue

            # 提交任务到线程池
            if key.startswith("ana:"):
                task_id = key[4:].strip()
                executor.submit(analyze, task_id)
            else:
                executor.submit(process_audio, key, task_data["scp_file"], model)


@app.command()
def run(
    download: bool = typer.Option(
        False, "--download", "-d", help="Download model before starting worker"
    ),
):
    """运行ASR工作进程"""
    if download:
        if not download_model():
            print("Failed to download model. Exiting...")
            return

    if not os.path.exists(MODEL_DIR):
        print("Model not found. Please download it first using --download flag")
        return

    start_worker()


if __name__ == "__main__":
    import torch

    if os.environ.get("MODELSCOPE_CACHE") is None:
        print("请设置环境变量MODELSCOPE_CACHE=/path/to/cache/directory")
        sys.exit(1)

    print(f"MODELSCOPE_CACHE = {os.environ.get('MODELSCOPE_CACHE')}")

    app()
