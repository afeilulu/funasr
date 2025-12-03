# -*- coding=utf-8
# to use qcloud_cos: pip install -U cos-python-sdk-v5
from qcloud_cos import CosConfig
from qcloud_cos import CosS3Client
import sys
import os
import logging
import json
import requests

# from urllib.parse import urlparse, unquote
from urllib.request import urlopen
from dotenv import load_dotenv

env_file = ".env.dev"
# if len(sys.argv) > 1:
#    env = sys.argv[1]
#    env_file = f".env.{env}"

# 加载.env文件中的环境变量
load_dotenv(dotenv_path=env_file)


# 正常情况日志级别使用 INFO，需要定位时可以修改为 DEBUG，此时 SDK 会打印和服务端的通信信息
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

# 1. 设置用户属性, 包括 secret_id, secret_key, region等。Appid 已在 CosConfig 中移除，请在参数 Bucket 中带上 Appid。Bucket 由 BucketName-Appid 组成
secret_id = os.getenv(
    "COS_SECRETID"
)  # 用户的 SecretId，建议使用子账号密钥，授权遵循最小权限指引，降低使用风险。子账号密钥获取可参见 https://cloud.tencent.com/document/product/598/37140
secret_key = os.getenv(
    "COS_SECRETKEY"
)  # 用户的 SecretKey，建议使用子账号密钥，授权遵循最小权限指引，降低使用风险。子账号密钥获取可参见 https://cloud.tencent.com/document/product/598/37140
region = os.getenv(
    "COS_REGIONNAME"
)  # 替换为用户的 region，已创建桶归属的 region 可以在控制台查看，https://console.cloud.tencent.com/cos5/bucket
# COS 支持的所有 region 列表参见https://cloud.tencent.com/document/product/436/6224
bucket = os.getenv("COS_BUCKETNAME")
token = None  # 如果使用永久密钥不需要填入 token，如果使用临时密钥需要填入，临时密钥生成和使用指引参见 https://cloud.tencent.com/document/product/436/14048
scheme = "https"  # 指定使用 http/https 协议来访问 COS，默认为 https，可不填

config = CosConfig(
    Region=region, SecretId=secret_id, SecretKey=secret_key, Token=token, Scheme=scheme
)
client = CosS3Client(config)

# # 文件流 简单上传
# file_name = 'test.txt'
# with open('test.txt', 'rb') as fp:
#     response = client.put_object(
#         Bucket='examplebucket-1250000000',  # Bucket 由 BucketName-APPID 组成
#         Body=fp,
#         Key=file_name,
#         StorageClass='STANDARD',
#         ContentType='text/html; charset=utf-8'
#     )
#     print(response['ETag'])

# # 字节流 简单上传
# response = client.put_object(
#     Bucket='examplebucket-1250000000',
#     Body=b'abcdefg',
#     Key=file_name
# )
# print(response['ETag'])

# # 本地路径 简单上传
# response = client.put_object_from_local_file(
#     Bucket='examplebucket-1250000000',
#     LocalFilePath='local.txt',
#     Key=file_name
# )
# print(response['ETag'])


def upload_remote_json_file(url: str):
    try:
        # 发送请求获取JSON
        response = requests.get(url)
        response.raise_for_status()  # 检查HTTP错误

        # 解析JSON
        data = response.json()

        # 需要解码URL编码的字符
        file_name = url.split("/")[-1].split("?")[0]
        print(file_name)

        # 保存到文件
        with open(file_name, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print("\n数据已保存到文件: f2cbf445-e155-4b05-8e49-65436f0f9d34-1.json")

        with open(file_name, "rb") as fp:
            response = client.put_object(
                Bucket=bucket,
                Body=fp,
                Key=file_name,
                StorageClass="STANDARD",
                ContentType="text/html; charset=utf-8",
            )
            etag = response["ETag"]
            print(etag)
            # 生成URL
            if etag:
                url = client.get_object_url(Bucket=bucket, Key=file_name)
                print(url)
                return url

    except requests.exceptions.RequestException as e:
        print(f"HTTP请求错误: {e}")
    except json.JSONDecodeError as e:
        print(f"JSON解析错误: {e}")
    except Exception as e:
        print(f"其他错误: {e}")

    return None


def upload_file(file_name: str, file_path: str):
    response = client.put_object_from_local_file(
        Bucket=bucket, LocalFilePath=file_path, Key=file_name
    )
    etag = response["ETag"]
    print(etag)
    # 生成URL
    if etag:
        url = client.get_object_url(Bucket=bucket, Key=file_name)
        print(url)
        return url

    return None


if __name__ == "__main__":
    # upload_remote_json_file(
    #     "https://dashscope-result-bj.oss-cn-beijing.aliyuncs.com/prod/fun-asr-v1/20251203/13%3A19/152b0af7-3a14-417c-b79b-1729bb20fd9a-1.json?Expires=1764825579&OSSAccessKeyId=LTAI5tQZd8AEcZX6KZV4G8qL&Signature=PvfeZ8%2FFjmEbLFQmQmqfR0rFtec%3D"
    # )
    response = urlopen(
        "https://dashscope-result-bj.oss-cn-beijing.aliyuncs.com/prod/fun-asr-v1/20251203/14%3A38/97b256ab-0525-44a5-8fa9-822ff347912c-1.json?Expires=1764830339&OSSAccessKeyId=LTAI5tQZd8AEcZX6KZV4G8qL&Signature=D3xY11Xmrxn5Vvlk2eK0vMENgAQ%3D"
    )
    data_bytes = response.read()
    data_string = data_bytes.decode("utf-8")
    json_data = json.loads(data_string)
    for sentence in json_data["transcripts"][0]["sentences"]:
        print(sentence["text"])
