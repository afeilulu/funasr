from funasr import AutoModel
# from funasr.utils.postprocess_utils import rich_transcription_postprocess
import json
# from dify import dify_post, parse_dify_any
from common import merge_consecutive_items
import multiprocessing
import time

model_dir = "../models/speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch"
vad_model_dir = "../models/speech_fsmn_vad_zh-cn-16k-common-pytorch"
punc_model_dir = "../models/punc_ct-transformer_zh-cn-common-vocab272727-pytorch"
spk_model_dir = "../models/speech_campplus_sv_zh-cn_16k-common"

output_dir = "./results"

def local(number):
    result = sum(i * i for i in range(number))
    print(result)

    model = AutoModel(
        model=model_dir,
        vad_model=vad_model_dir,
        punc_model=punc_model_dir,
        spk_model=spk_model_dir,
        device="cpu",
        disable_update=True,
        ffmpeg_path="/usr/bin/ffmpeg"
    )
    
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

    return result

def cacluate_count(numbers):
    processes = [multiprocessing.Process(target=local, args=(number,)) for number in numbers]
    for process in processes:
        process.start()
    for process in processes:
        process.join()
        
if __name__ == "__main__":
    begin_time = time.perf_counter()
    numbers = [x for x in range(10)]
    cacluate_count(numbers)
    end_time = time.perf_counter()
    print('Total cost time is: ', end_time -  begin_time)

