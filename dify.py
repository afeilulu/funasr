import json
import requests

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
                        dify_data = json.loads(json_str)
                        # 根据事件类型进行条件处理
                        event_type = dify_data.get("event")
                        # print(event_type)
                        # 处理文本片段事件
                        if (event_type == "workflow_finished") :
                            return dify_data

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