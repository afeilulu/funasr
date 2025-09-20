import asyncio
import json
import aiohttp
from typing import List, Optional
from common import extract_json_content

async def fetch_url_content(session: aiohttp.ClientSession, url: str, timeout: int = 30) -> Optional[str]:
    """
    获取单个URL的响应体长度
    
    参数:
    session: aiohttp会话对象
    url: 要请求的URL
    timeout: 请求超时时间（秒）
    
    返回:
    响应体，如果请求失败则返回error:异常信息
    """
    # try:
    #     async with session.get(url, timeout=timeout) as response:
    #         content = await response.text()
    #         return len(content)
    # except Exception as e:
    #     print(f"获取URL {url} 时出错: {e}")
    #     return None
    
    dify_url = "https://dify.dev.xbt.sx.cn/v1/workflows/run"
    headers = {
        "Authorization": "Bearer app-ektXUeDAh9tQMgN1wD0eReYy"
    }
    data = {
        "inputs": {"cuttedFileUrl": url},
        "response_mode": "streaming",
        "user": "user123"
    }
    try:
        async with session.post(url=dify_url,json=data,headers=headers,timeout=timeout) as response:
            # Ensure the response status is successful
            response.raise_for_status()

            # Access the StreamReader for content
            while True:
                line = await response.content.readline()
                if not line:
                    break  # End of stream
                # print(f"Received line: {line.decode().strip()}")
                # SSE 协议中，数据行以 "data: " 开头 [1]
                if line.startswith(b"data:"):
                    # 提取 JSON 字符串
                    json_str = line.decode('utf-8')[5:].strip()
                    dify_data = json.loads(json_str)
                    # 根据事件类型进行条件处理
                    event_type = dify_data.get("event")
                    print(f"{url} {event_type}")
                    # 处理文本片段事件
                    if (event_type == "workflow_finished"):
                        if (dify_data["data"]["status"]=="succeeded"):
                            print(dify_data["data"]["outputs"])
                            json_str = extract_json_content(dify_data["data"]["outputs"]["text"])
                            # print(json_str)
                            return json_str
                        else:
                            error = dify_data["data"]["error"]
                            print(error)
                            return f"error:{error}"

            return "error:None"
    except Exception as e:
        print(f"获取URL {url} 时出错: {e}")
        return f"error:{e}"

async def parallel_url_content(urls: List[str], timeout: int = 30, max_concurrent: int = 10) -> List[Optional[str]]:
    """
    并行获取URL列表中每个URL响应
    
    参数:
    urls: URL列表
    timeout: 每个请求的超时时间（秒）
    max_concurrent: 最大并发请求数
    
    返回:
    一个列表，包含每个URL响应体的长度（失败则为None）
    """
    if not urls:
        return []
    
    # 创建TCP连接器，限制并发连接数
    connector = aiohttp.TCPConnector(limit=max_concurrent)
    
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [fetch_url_content(session, url, timeout) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理可能的异常
        final_results = []
        for result in results:
            if isinstance(result, Exception):
                print(f"任务执行出错: {result}")
                final_results.append(None)
            else:
                final_results.append(result)
                
        return final_results

def get_urls_content(urls: List[str], timeout: int = 300, max_concurrent: int = 50) -> List[Optional[str]]:
    """
    同步接口：获取URL列表中每个URL响应体的长度
    
    参数:
    urls: URL列表
    timeout: 每个请求的超时时间（秒）
    max_concurrent: 最大并发请求数
    
    返回:
    一个列表，包含每个URL响应体的长度（失败则为None）
    """
    # 创建或获取事件循环
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    # 运行异步任务
    return loop.run_until_complete(parallel_url_content(urls, timeout, max_concurrent))

# 示例用法
if __name__ == "__main__":
    # 示例URL列表
    test_urls = [
        "https://xbt-platform-public-1301716714.cos.ap-chengdu.myqcloud.com/funasr_3203520_10288942_1.json",
        "https://xbt-platform-public-1301716714.cos.ap-chengdu.myqcloud.com/funasr_3203520_10288942_2.json",
        "https://xbt-platform-public-1301716714.cos.ap-chengdu.myqcloud.com/funasr_3203520_10288942_3.json",
        "https://xbt-platform-public-1301716714.cos.ap-chengdu.myqcloud.com/funasr_3203520_10288942_4.json",
        "https://xbt-platform-public-1301716714.cos.ap-chengdu.myqcloud.com/funasr_3203520_10288942_5.json",
        "https://xbt-platform-public-1301716714.cos.ap-chengdu.myqcloud.com/funasr_3203520_10288942_6.json",
        "https://xbt-platform-public-1301716714.cos.ap-chengdu.myqcloud.com/funasr_3203520_10288942_7.json",
    ]
    
    # 获取URL内容
    contents = get_urls_content(test_urls, timeout=10, max_concurrent=10)
    
    # 打印结果
    for url, content in zip(test_urls, contents):
        if content is not None:
            print(f"{url} -> 响应: {content}")
        else:
            print(f"{url} -> 请求失败")