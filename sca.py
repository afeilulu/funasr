# -*- coding: utf-8 -*-
# This file is auto-generated, don't edit it. Thanks.
# pip install alibabacloud_qualitycheck20190115==8.4.1
# pip install alibabacloud_credentials
#
# import os
import sys
import json

from typing import List, Optional

from alibabacloud_qualitycheck20190115.client import (
    Client as Qualitycheck20190115Client,
)
from alibabacloud_credentials.client import Client as CredentialClient
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_qualitycheck20190115 import models as qualitycheck_20190115_models
from alibabacloud_tea_util import models as util_models
from alibabacloud_tea_util.client import Client as UtilClient

# from redis import client
from pydantic import BaseModel

scaCallbackUrl = "https://gateway.platform.xbt.sx.cn/funasr-api-server/sca/callback"


class CallListItem(BaseModel):
    voiceFileUrl: str
    fileName: str
    remark1: str


class UploadAudioDataRequestJson(BaseModel):
    autoSplit: int
    serviceChannelKeywords: list[str]
    callbackUrl: str
    callList: list[CallListItem]


class GetResultRequestJson(BaseModel):
    pageNumber: int
    pageSize: int
    excludeFields: list
    sortType: str  # desc/asc
    taskId: Optional[str] = None
    remark1: Optional[str] = None


class GetResultToReviewRequestJson(BaseModel):
    taskId: str
    fileId: str  # from GetResult response


class Sample:
    def __init__(self):
        pass

    @staticmethod
    def create_client() -> Qualitycheck20190115Client:
        """
        使用凭据初始化账号 Client
        @return: Client
        @throws Exception
        """
        # 工程代码建议使用更安全的无 AK 方式，凭据配置方式请参见：https://help.aliyun.com/document_detail/378659.html。
        credential = CredentialClient()
        config = open_api_models.Config(credential=credential)
        # Endpoint 请参考 https://api.aliyun.com/product/Qualitycheck
        config.endpoint = "qualitycheck.cn-hangzhou.aliyuncs.com"
        return Qualitycheck20190115Client(config)

    @staticmethod
    def uploadAudio(url: str, fileName: str, remark1: str):
        client = Sample.create_client()
        # callListItem = CallListItem(
        #    voiceFileUrl="https://xbt-platform-public-1301716714.cos.ap-chengdu.myqcloud.com/fd6e48d9-a25d-41da-b9e7-0a7d4a29119e",
        #    fileName="a123456.wav",
        #    remark1="123456",
        # )
        item = CallListItem(voiceFileUrl=url, fileName=fileName, remark1=remark1)
        request = UploadAudioDataRequestJson(
            autoSplit=1,
            serviceChannelKeywords=["给您", "给你", "请坐"],
            callbackUrl=scaCallbackUrl,
            callList=[item],
        )
        uploadAudioDataRequest = qualitycheck_20190115_models.UploadAudioDataRequest(
            # json_str='{"autoSplit":1,"serviceChannelKeywords":["给您","给你"],"callbackUrl":"https://gateway.platform.xbt.sx.cn/funasr-api-server/sca/callback","callList":[{"voiceFileUrl":"https://xbt-platform-public-1301716714.cos.ap-chengdu.myqcloud.com/fd6e48d9-a25d-41da-b9e7-0a7d4a29119e","fileName":"a123456.wav","remark1":"123456"}]}'
            json_str=json.dumps(request, ensure_ascii=False)
        )
        try:
            # 复制代码运行请自行打印 API 的返回值
            response = client.upload_audio_data(uploadAudioDataRequest)
            # {'Code': '200', 'Data': '20251127-5458D5C7-0ED6-5C47-A51E-56110213189B', 'Message': '', 'RequestId': '20251127-5458D5C7-0ED6-5C47-A51E-56110213189B', 'Success': True}
            print(response.body.to_map())
            return response.body
        except Exception as error:
            print(error)

    @staticmethod
    def getResult(taskId=None, remark1=None):
        client = Sample.create_client()
        request = GetResultRequestJson(
            pageNumber=1,
            pageSize=10,
            excludeFields=[
                "Agent",
                "AsrResult",
                "HitResult",
                "HitScore",
                "Recording",
                "SchemeIdList",
                "SchemeNameList",
            ],
            sortType="asc",
            taskId=taskId,
            remark1=remark1,
        )
        # request = qualitycheck_20190115_models.GetResultRequest(json_str="")
        try:
            # 复制代码运行请自行打印 API 的返回值
            response = client.get_result(
                qualitycheck_20190115_models.GetResultRequest(
                    json_str=json.dumps(request, ensure_ascii=False)
                )
            )
            print(response.body.to_map())
            return response.body
        except Exception as error:
            print(error)

    @staticmethod
    def getResultToReview(taskId: str, fileId: str):
        client = Sample.create_client()
        try:
            request = GetResultToReviewRequestJson(taskId=taskId, fileId=fileId)
            response = client.get_result_to_review(
                qualitycheck_20190115_models.GetResultToReviewRequest(
                    # json_str='{"taskId":"20251127-5458D5C7-0ED6-5C47-A51E-56110213189B","fileId":"61bd6a84118b4612843665fdd1783085"}'
                    json_str=json.dumps(request, ensure_ascii=False)
                )
            )
            print(response.body.to_map())
            return response.body
        except Exception as error:
            print(error)

    @staticmethod
    def main(
        args: List[str],
    ) -> None:
        client = Sample.create_client()
        try:
            # 复制代码运行请自行打印 API 的返回值
            response = client.get_result_to_review(
                qualitycheck_20190115_models.GetResultToReviewRequest(
                    json_str='{"taskId":"20251127-5458D5C7-0ED6-5C47-A51E-56110213189B","fileId":"61bd6a84118b4612843665fdd1783085"}'
                )
            )
            print(response.body.to_map())
        except Exception as error:
            # 此处仅做打印展示，请谨慎对待异常处理，在工程项目中切勿直接忽略异常。
            # 错误 message
            print(error)

    @staticmethod
    async def main_async(
        args: List[str],
    ) -> None:
        client = Sample.create_client()
        add_business_category_request = (
            qualitycheck_20190115_models.AddBusinessCategoryRequest(
                json_str="your_value", base_me_agent_id=1
            )
        )
        try:
            # 复制代码运行请自行打印 API 的返回值
            await client.add_business_category_with_options_async(
                add_business_category_request, util_models.RuntimeOptions()
            )
        except Exception as error:
            # 此处仅做打印展示，请谨慎对待异常处理，在工程项目中切勿直接忽略异常。
            # 错误 message
            print(error.message)
            # 诊断地址
            print(error.data.get("Recommend"))
            UtilClient.assert_as_string(error.message)


if __name__ == "__main__":
    Sample.main(sys.argv[1:])
