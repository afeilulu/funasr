

### 下载模型到本地
```
modelscope download --model iic/speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch  --local_dir ./speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch
modelscope download --model iic/speech_fsmn_vad_zh-cn-16k-common-pytorch  --local_dir ./speech_fsmn_vad_zh-cn-16k-common-pytorch
modelscope download --model iic/punc_ct-transformer_zh-cn-common-vocab272727-pytorch  --local_dir ./punc_ct-transformer_zh-cn-common-vocab272727-pytorch
modelscope download --model iic/speech_campplus_sv_zh-cn_16k-common  --local_dir ./speech_campplus_sv_zh-cn_16k-common
```

### 对话prompt
目标:
附件是牙科患者和咨询师的对话。请将该文件解析为自然对话的过程。

要求
1. 区分患者和咨询师的身份
2. 尽量合并同一身份的连续发言
3. 带上时间信息，文件中的时间单位是毫秒，需要转化为 分:秒:毫秒
4. 格式化输出。身份(分:秒:毫秒 ~ 分:秒:毫秒)：(换行)内容

### 内容分析prompt
目标
附件牙科患者和牙科咨询师的对话。请分析对话内容。

要求
1. 明确患者主要诉求
2. 明确患者心理预期
3. 明确患者消费逾期
4. 尝试患者分群，给患者打标签
5. 给咨询师提出建议，以便更好引导患者


### 尝试funasr-runtime
nohup bash run_server.sh \
  --download-model-dir /workspace/models \
  --vad-dir damo/speech_fsmn_vad_zh-cn-16k-common-onnx \
  --model-dir damo/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-onnx  \
  --punc-dir damo/punc_ct-transformer_cn-en-common-vocab471067-large-onnx \
  --lm-dir damo/speech_ngram_lm_zh-cn-ai-wesp-fst \
  --itn-dir thuduj12/fst_itn_zh \
  --certfile 0 \
  --hotword /workspace/models/hotwords.txt > log.txt 2>&1 &


nohup bash run_server.sh \
  --download-model-dir /workspace/models \
  --model-dir iic/speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch \
  --vad-dir iic/speech_fsmn_vad_zh-cn-16k-common-onnx \
  --punc-dir iic/punc_ct-transformer_zh-cn-common-vocab272727-onnx \
  --certfile 0 \
  --hotword /workspace/models/hotwords.txt > log.txt 2>&1 &


full: https://xbt-platform-public-1301716714.cos.ap-chengdu.myqcloud.com/be0c1221-1958-4679-b4c8-770fec1a114f
80: https://xbt-platform-public-1301716714.cos.ap-chengdu.myqcloud.com/beb8b21f-6ea7-47aa-856f-9b63583afa19