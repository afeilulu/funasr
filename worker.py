import os
import typer
import redis
import json
from concurrent.futures import ThreadPoolExecutor
from funasr import AutoModel
from dify import dify_post, parse_dify_any
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

def read_and_join_file(filename):
    """
    读取UTF-8文件，忽略#开头的行，将每行用英文空格拼接返回
    
    Args:
        filename (str): 要读取的文件路径
        
    Returns:
        str: 处理后的字符串
    """
    lines = []
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            for line in file:
                # 去除行首尾空白字符
                stripped_line = line.strip()
                # 跳过空行和以#开头的行
                if stripped_line and not stripped_line.startswith('#'):
                    lines.append(stripped_line)
    except FileNotFoundError:
        return f"错误：文件 '{filename}' 未找到"
    except Exception as e:
        return f"读取文件时出错：{str(e)}"
    
    # 用空格拼接所有非注释行
    return ' '.join(lines)

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
        result = model.generate(
            input=file_path,
            hotword=read_and_join_file('./hotword.txt'),
            batch_size_s=300
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

            # speech = json.dumps(speech_list, indent=2, ensure_ascii=False)
            speech = json.dumps(speech_list, ensure_ascii=False)
            # dify解析对话，优化输出
            json_data = dify_post("app-H4YrU42V6PPTDXLriarazedD", "chatContent", key, speech)
            # 解析输出为json
            # print(json_data)
            data_str = json_data["data"]["outputs"]["chatContent"]
            print(data_str)
            msg_json = parse_dify_any(data_str)
            msg_json = merge_consecutive_items(msg_json)
            if (msg_json is not None):
                messages.append(msg_json)

        # 更新任务对话解析结果
        redis_client.hmset(key, {
            "status": "completed",
            "speech": json.dumps(messages,ensure_ascii=False)
        })

        return True
    except Exception as e:
        print(f"Error processing task {key}: {str(e)}")
        redis_client.hmset(key, {
            "status": "failed",
            "result": str(e)
        })
        return False
    
def analyze(task_id: str):
    key = f"ana:{task_id}"
    try:
        # 更新任务状态为处理中
        redis_client.hset(key, "status", "processing")

        # 获取历史所有对话    
        fuzzy_key = f"funasr:{task_id}:*"
        keys = redis_client.keys(fuzzy_key)
        all_speech=[]
        for sub_key in keys :
            print(sub_key)
            sub_task_data = redis_client.hgetall(sub_key)
            speech_list = json.loads(sub_task_data.get("speech"))
            all_speech.extend(speech_list)

        if (len(all_speech) == 0):
            redis_client.hmset(key, {
                "status": "failed",
                "result": "lack of information"
            })
            return False

        # 分析对话
        json_data_ana = dify_post("app-TlgE19fpgxhpQB9yOA3RBfj8", "chatContent", key, json.dumps(all_speech, ensure_ascii=False))
        print(json_data_ana)
        ana_str = json_data_ana["data"]["outputs"]["text"]
        print(ana_str)
        text_result = parse_dify_any(ana_str)

        # 更新分析结果
        redis_client.hmset(key, {
            "status": "completed",
            "result": json.dumps(text_result,ensure_ascii=False)
        })
        return True
    except Exception as e:
        print(f"Error processing analyze {key}: {str(e)}")
        res = {
            "status": "failed",
            "result": str(e)
        }
        redis_client.hmset(key, res)
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
            if key.startswith("ana:"):
                task_id = key[4:].strip()
                executor.submit(analyze, task_id)
            else:
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

def merge_consecutive_items(items):
    if not items:
        return []
    
    merged_items = []
    current_item = items[0].copy()  # 创建当前项的副本以避免修改原项
    if ("timestamp" in current_item):
        del current_item["timestamp"]
    
    for i in range(1, len(items)):
        next_item = items[i]
        if ("timestamp" in next_item):
            del next_item["timestamp"]
        
        # 检查是否满足合并条件：相同说话人且当前结束时间等于下一项开始时间
        if (current_item['spk'] == next_item['spk'] and 
            current_item['end'] == next_item['start']):
            
            # 合并文本
            current_item['text'] += next_item['text']
            # 更新结束时间为下一项的结束时间
            current_item['end'] = next_item['end']
        else:
            # 如果不满足合并条件，将当前项添加到结果列表
            merged_items.append(current_item)
            # 重置当前项为下一项
            current_item = next_item.copy()
    
    # 添加最后一个当前项
    merged_items.append(current_item)
    
    return merged_items


if __name__ == "__main__":
    import torch

    app()
