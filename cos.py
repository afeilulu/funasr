# -*- coding=utf-8
# to use qcloud_cos: pip install -U cos-python-sdk-v5
from qcloud_cos import CosConfig
from qcloud_cos import CosS3Client
import sys
import os
import logging
from dotenv import load_dotenv

# 加载.env文件中的环境变量
load_dotenv()

# 正常情况日志级别使用 INFO，需要定位时可以修改为 DEBUG，此时 SDK 会打印和服务端的通信信息
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

# 1. 设置用户属性, 包括 secret_id, secret_key, region等。Appid 已在 CosConfig 中移除，请在参数 Bucket 中带上 Appid。Bucket 由 BucketName-Appid 组成
secret_id = os.getenv("COS_SECRETID")    # 用户的 SecretId，建议使用子账号密钥，授权遵循最小权限指引，降低使用风险。子账号密钥获取可参见 https://cloud.tencent.com/document/product/598/37140
secret_key = os.getenv("COS_SECRETKEY")   # 用户的 SecretKey，建议使用子账号密钥，授权遵循最小权限指引，降低使用风险。子账号密钥获取可参见 https://cloud.tencent.com/document/product/598/37140
region = os.getenv("COS_REGIONNAME")      # 替换为用户的 region，已创建桶归属的 region 可以在控制台查看，https://console.cloud.tencent.com/cos5/bucket
                           # COS 支持的所有 region 列表参见https://cloud.tencent.com/document/product/436/6224
bucket = os.getenv("COS_BUCKETNAME")
token = None               # 如果使用永久密钥不需要填入 token，如果使用临时密钥需要填入，临时密钥生成和使用指引参见 https://cloud.tencent.com/document/product/436/14048
scheme = 'https'           # 指定使用 http/https 协议来访问 COS，默认为 https，可不填

config = CosConfig(Region=region, SecretId=secret_id, SecretKey=secret_key, Token=token, Scheme=scheme)
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

def upload_file(file_name: str,file_path: str):
    response = client.put_object_from_local_file(
        Bucket=bucket,
        LocalFilePath=file_path,
        Key=file_name
    )
    etag=response['ETag'] 
    print(etag)
    # 生成URL
    if etag:
        url = client.get_object_url(
            Bucket=bucket,
            Key=file_name
        )
        print(url)
        return url
    
    return None