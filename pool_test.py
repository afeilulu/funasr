from funasr import AutoModel
# from funasr.utils.postprocess_utils import rich_transcription_postprocess
import json
# from dify import dify_post, parse_dify_any
from common import merge_consecutive_items
from concurrent.futures import ThreadPoolExecutor
import time

model_dir = "../models/speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch"
vad_model_dir = "../models/speech_fsmn_vad_zh-cn-16k-common-pytorch"
punc_model_dir = "../models/punc_ct-transformer_zh-cn-common-vocab272727-pytorch"
spk_model_dir = "../models/speech_campplus_sv_zh-cn_16k-common"

output_dir = "./results"

def local(model):
    
    res = model.generate(
        input="./test.wav",
        output_dir=output_dir,
        batch_size_s=300,
        hotword='正畸 患者主诉 牙齿疼痛 牙龈出血 牙齿敏感 要求洁牙 牙齿不齐 检查发现 探诊出血 牙周袋 牙龈红肿 牙齿松动 充填体脱落 裂纹 缺失牙 诊断 慢性牙周炎 慢性根尖周炎 急性牙髓炎 深龋 中龋 浅龋 牙列缺损 牙列不齐 牙髓坏死 牙龈炎 颌关节紊乱',
        # hotword='魔搭'
    )

    # text = rich_transcription_postprocess(res[0]["text"])
    # print(text)

    print("-------------------------------------------------------------")
    for item in res:
        # speech_list = item["sentence_info"]
        # for item in speech_list:
        #     del item["timestamp"]
        speech_list = merge_consecutive_items(item["sentence_info"])
        speech = json.dumps(speech_list, ensure_ascii=False)
        print(speech)

def start_worker():
    """启动工作进程"""
    print("Initializing ASR model...")
    model = AutoModel(
        model=model_dir,
        vad_model=vad_model_dir,
        punc_model=punc_model_dir,
        spk_model=spk_model_dir,
        device="cpu",
        disable_update=True,
        ffmpeg_path="/usr/bin/ffmpeg",
        ncpu = 24
    )

    with ThreadPoolExecutor(max_workers=20) as executor:
        for x in range(10):
            executor.submit(local, model)
        
if __name__ == "__main__":
    begin_time = time.perf_counter()
    start_worker()
    end_time = time.perf_counter()
    print('Total cost time is: ', end_time -  begin_time)

