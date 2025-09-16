import os
import typer
import redis
import json
import requests
from concurrent.futures import ThreadPoolExecutor
from funasr import AutoModel
# from funasr.utils.postprocess_utils import rich_transcription_postprocess

app = typer.Typer()

# 配置
REDIS_HOST = "192.168.5.127"
REDIS_PORT = 32163
REDIS_DB = 1
MODEL_DIR = "models"
MAX_WORKERS = 2  # 最大并发处理数量

os.environ["MODELSCOPE_CACHE"] = os.path.dirname(os.path.abspath(__file__))  # 设置模型缓存路径

# ffmpeg配置
FFMPEG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffmpeg.exe")

# Redis客户端
redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    decode_responses=True,
    password="xbt123456"
)

def dify_post(token, var_name, user, content):
    url = "https://dify.dev.xbt.sx.cn/v1/workflows/run"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    data = {
        "inputs": {f"{var_name}": content},
        "response_mode": "streaming",
        "user": user
    }
    try:
        r = requests.post(url=url,json=data,headers=headers,stream=True)
        if r.status_code == 200:
            print("请求成功！")
        
            for line in r.iter_lines():
                if line:
                    # SSE 协议中，数据行以 "data: " 开头 [1]
                    if line.startswith(b"data:"):
                        # 提取 JSON 字符串
                        json_str = line.decode('utf-8')[5:].strip()
                        data = json.loads(json_str)
                        # 根据事件类型进行条件处理
                        event_type = data.get("event")
                        # print(event_type)
                        # 处理文本片段事件
                        if (event_type == "workflow_finished") :
                            return data

            return None
        else:
            print(f"请求失败，状态码：{r.status_code}")
            print(r.text)
            return None
    except requests.RequestException as e:
        print(f"请求失败，错误：{e}")
        return None
    
def parse_dify_any(outputs):
    if (outputs is None):
        return None

    # 进一步解析outputs中的JSON数组
    try:
        # 去除Markdown代码块标记和多余的转义字符
        json_content = outputs.strip('`').replace('\\n', '').replace('\\t', '').replace('\\"', '"')
        # 提取JSON部分（去掉开头的"json"标记）
        if json_content.startswith('json'):
            json_content = json_content[4:].strip()
        
        # 解析JSON数组
        messages = json.loads(json_content)
        return messages
    except json.JSONDecodeError as e:
        print(f"解析chatContent中的JSON时出错: {e}")
        return None

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
            model="paraformer-zh",model_revision="v2.0.4",
            vad_model="fsmn-vad",vad_model_revision="v2.0.4",
            punc_model="ct-punc-c", punc_model_revision="v2.0.4",
            spk_model="cam++", spk_model_revision="v2.0.2",
            device="cuda" if torch.cuda.is_available() else "cpu",
            ffmpeg_path=FFMPEG_PATH
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
        result = model.generate(input=file_path)
        # text = rich_transcription_postprocess(result[0]["text"])
        # print(text)
        # text_result = text

        messages = []
        for stage in result:
            speech_list = stage["sentence_info"]
            for item in speech_list:
                del item["timestamp"]

            # speech = json.dumps(speech_list, indent=2, ensure_ascii=False)
            speech = json.dumps(speech_list, ensure_ascii=False)
            # print(speech)
            # dify解析对话，优化输出
            json_data = dify_post("app-H4YrU42V6PPTDXLriarazedD", "chatContent", key, speech)
            # 解析输出为json
            data_str = json_data["data"]["outputs"]["chatContent"]
            print(data_str)
            msg_json = parse_dify_any(data_str)
            if (msg_json is not None):
                messages.append(msg_json)

        # 更新任务对话解析结果
        redis_client.hmset(key, {
            "status": "completed",
            "speech": json.dumps(messages,ensure_ascii=False)
        })

        analyze(key)

        return True
    except Exception as e:
        print(f"Error processing task {key}: {str(e)}")
        redis_client.hmset(key, {
            "status": "failed",
            "result": str(e)
        })
        return False
    
def analyze(key: str):
    task_data = redis_client.hgetall(key)
    task_id=task_data.get("task_id")
    ana_key = f"ana:{task_id}"
    try:
        # 获取历史所有对话    
        fuzzy_key = f"funasr:{task_id}:*"
        keys = redis_client.keys(fuzzy_key)
        all_speech=[]
        for sub_key in keys :
            sub_task_data = redis_client.hgetall(sub_key)
            all_speech.append(sub_task_data.get("speech"))

        # 分析对话
        json_data_ana = dify_post("app-TlgE19fpgxhpQB9yOA3RBfj8", "chatContent", key, json.dumps(all_speech, ensure_ascii=False))
        ana_str = json_data_ana["data"]["outputs"]["text"]
        print(ana_str)
        text_result = parse_dify_any(ana_str)

        # 更新分析结果
        redis_client.hmset(ana_key, {
            "status": "completed",
            "result": json.dumps(text_result,ensure_ascii=False)
        })

        print(f"Task {ana_key} completed successfully")
    except Exception as e:
        print(f"Error processing task {ana_key}: {str(e)}")
        redis_client.hmset(ana_key, {
            "status": "failed",
            "result": str(e)
        })
        return False


def start_worker():
    """启动工作进程"""
    print("Initializing ASR model...")
    model = AutoModel(
        model=f"{os.path.dirname(os.path.abspath(__file__))}/models/speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
        punc_model=f"{os.path.dirname(os.path.abspath(__file__))}/models/punc_ct-transformer_zh-cn-common-vocab272727-pytorch",
        vad_model=f"{os.path.dirname(os.path.abspath(__file__))}/models/speech_fsmn_vad_zh-cn-16k-common-pytorch",
        spk_model=f"{os.path.dirname(os.path.abspath(__file__))}/models/speech_campplus_sv_zh-cn_16k-common",
        disable_update=True,
        device="cuda" if torch.cuda.is_available() else "cpu",
        ffmpeg_path=FFMPEG_PATH
    )

    print(f"Starting worker with {MAX_WORKERS} concurrent tasks...")
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        while True:
            # 从队列中获取任务
            task = redis_client.brpop("asr_tasks", timeout=1)
            if task is None:
                continue

            key = task[1]  # brpop returns tuple (queue_name, value)
            task_data = redis_client.hgetall(key)

            if not task_data:
                print(f"Task {key} not found in Redis")
                continue

            # 提交任务到线程池
            executor.submit(process_audio, key, task_data['scp_file'], model)


@app.command()
def run(download: bool = typer.Option(False, "--download", "-d", help="Download model before starting worker")):
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

    app()
