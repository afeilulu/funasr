from funasr import AutoModel
from funasr.utils.postprocess_utils import rich_transcription_postprocess
import json
from utils import dify_post, parse_dify_any

def test():
    output_dir = "./results"
    model = AutoModel(model="paraformer-zh", model_revision="v2.0.4",
                  vad_model="fsmn-vad", vad_model_revision="v2.0.4",
                  punc_model="ct-punc-c", punc_model_revision="v2.0.4",
                  spk_model="cam++", spk_model_revision="v2.0.2",
                  )

    res = model.generate(input="https://xbt-platform-public-1301716714.cos.ap-chengdu.myqcloud.com/4699330c-7735-4f7f-a208-149c878a679f",
                output_dir=output_dir,
                batch_size_s=300,
                hotword='魔搭'
                )
    print(res)

model_dir = "./models/speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch"
vad_model_dir = "./models/speech_fsmn_vad_zh-cn-16k-common-pytorch"
punc_model_dir = "./models/punc_ct-transformer_zh-cn-common-vocab272727-pytorch"
spk_model_dir = "./models/speech_campplus_sv_zh-cn_16k-common"

def local():
    output_dir = "./results"
    model = AutoModel(
        model=model_dir,
        vad_model=vad_model_dir,
        punc_model=punc_model_dir,
        spk_model=spk_model_dir,
        device="cpu",
        disable_update=True,
        ffmpeg_path="./ffmpeg.exe"
    )

    res = model.generate(
        #input="https://xbt-platform-public-1301716714.cos.ap-chengdu.myqcloud.com/4699330c-7735-4f7f-a208-149c878a679f",
        #       input="../samples/audio/test.mp4",
        # input="https://xbt-platform-public-1301716714.cos.ap-chengdu.myqcloud.com/4c973bca-911d-4d3a-8b34-c3a40a0464b6",
        # input="https://xbt-platform-public-1301716714.cos.ap-chengdu.myqcloud.com/e144c18b-08ee-46aa-8eb4-1153b2bc2bef",
        input="./wav.scp",
        output_dir=output_dir,
        batch_size_s=300,
        hotword='魔搭'
    )

    text = rich_transcription_postprocess(res[0]["text"])
    print(text)

    print("-------------------------------------------------------------")
    for item in res:
        speech_list = item["sentence_info"]
        for item in speech_list:
            del item["timestamp"]

        speech = json.dumps(speech_list, ensure_ascii=False)
        json_data = dify_post("app-H4YrU42V6PPTDXLriarazedD", "chatContent", "user_123", speech)
        parse_dify_any(json_data["data"]["outputs"]["chatContent"])
        

if __name__ == "__main__":
    local()


