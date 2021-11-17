from fastapi import FastAPI, Body, Response
import uvicorn
from weworkSDK.WXBizMsgCrypt3 import WXBizMsgCrypt
import xml.etree.ElementTree as ET
import asyncio
from notion import CloudPiece, get_database_id, bind_check, create, update
from util import timestamp2iso
from sendMessage import SendMessage
from encryption import AESCipher
import base64
import requests
from config import Configure

config = Configure("config.ini")

app = FastAPI()
sToken = config.get_config("wework", "Token")
sEncodingAESKey = config.get_config("wework", "EncodingAESKey")
sCorpID = config.get_config("wework", "corp_id")
wxcpt = WXBizMsgCrypt(sToken, sEncodingAESKey, sCorpID)
# AttributeError: 'AESCipher' object has no attribute 'block_size' 暂未找到解决方法
# AES = AESCipher("")
wework_send = SendMessage()


@app.get("/")
def read_root(msg_signature: str, timestamp: str, nonce: str, echostr: str):
    return verify_url(msg_signature, timestamp, nonce, echostr)


def verify_url(msg_signature: str, timestamp: str, nonce: str, echostr: str):
    sVerifyMsgSig = msg_signature
    sVerifyTimeStamp = timestamp
    sVerifyNonce = nonce
    sVerifyEchoStr = echostr
    ret, sEchoStr = wxcpt.VerifyURL(
        sVerifyMsgSig, sVerifyTimeStamp, sVerifyNonce, sVerifyEchoStr
    )
    if ret != 0:
        print("ERR: VerifyURL ret: " + str(ret))
        return
    else:
        print("SUCC: VerifyURL ret: " + str(ret))
        return Response(sEchoStr)


@app.post("/")
async def receive_msg(
        msg_signature: str,
        timestamp: str,
        nonce: str,
        message: str = Body(...)
):
    ret, sMsg = wxcpt.DecryptMsg(message, msg_signature, timestamp, nonce)
    if ret != 0:
        print("ERR: DecryptMsg ret: " + str(ret))
        return ""
    else:
        print("SUCK: DecryptMsg ret: " + str(ret))
        # print(str(sMsg, encoding="utf-8"))
        # 创建协程任务，异步处理消息
        asyncio.create_task(process_message(sMsg))
        return passive_reply(sMsg, nonce, timestamp)


def passive_reply(message, nonce, timestamp):
    xml_tree = ET.fromstring(message)
    msg_type = xml_tree.find("MsgType").text
    to_user = xml_tree.find("FromUserName").text
    sRespData = "<xml><ToUserName>{}</ToUserName><FromUserName>wwe14538319d196cfa</FromUserName><CreateTime" \
                ">1476422779</CreateTime><MsgType>text</MsgType><Content>消息接收成功，检测到您发送的消息类型是：{}，正在处理中。</Content></xml>"\
        .format(
            to_user, msg_type
        )
    ret, sEncryptMsg = wxcpt.EncryptMsg(sRespData, nonce, timestamp)
    if ret != 0:
        print("ERR: EncryptMsg ret: " + str(ret))
        return ""
    else:
        print("SUCK: EncryptMsg ret: " + str(ret))
        # 事件类消息不发送回复响应
        if msg_type == "event":
            return ""
        return Response(sEncryptMsg)


async def process_message(message):
    xml_tree = ET.fromstring(message)
    msg_type = xml_tree.find("MsgType").text
    print(msg_type)
    if msg_type == "text":
        text_message(message)
    elif msg_type == "video":
        video_message(message)
    elif msg_type == "image":
        image_message(message)
    elif msg_type == "voice":
        voice_message(message)
    elif msg_type == "location":
        location_message(message)
    elif msg_type == "link":
        link_message(message)
    elif msg_type == "event":
        pass
    else:
        pass


def text_message(message):
    """
    <xml><ToUserName><![CDATA[wwe14538319d196cfa]]></ToUserName><FromUserName><![CDATA[username]]></FromUserName><CreateTime>1636869746</CreateTime><MsgType><![CDATA[text]]></MsgType><Content><![CDATA[1122525]]></Content><MsgId>7030302030506019854</MsgId><AgentID>1000002</AgentID></xml>
    :param message:
    :return:
    """
    print("this is a text message")
    xml_tree = ET.fromstring(message)
    msg_type = xml_tree.find("MsgType").text
    msg_id = xml_tree.find("MsgId").text
    msg_content = xml_tree.find("Content").text
    user_name = xml_tree.find("FromUserName").text
    msg_time = timestamp2iso(int(xml_tree.find("CreateTime").text))

    if keyword_check(msg_content, user_name):
        return
    if not bind_info_check(user_name):
        return
    cloud_piece = CloudPiece(user_name)
    res, url = cloud_piece.text_msg(msg_id, msg_type, msg_time, msg_content)
    if res:
        wework_send.send_message("", f"消息保存成功。点击链接编辑：{url}", user_name)
        return
    else:
        wework_send.send_message("", "消息保存失败，请重试。", user_name)
        return


def bind_info_check(user_name):
    is_create, is_bind = bind_check(user_name)
    if is_create and is_bind:
        return True
    else:
        wework_send.send_message("", "当前用户尚未绑定notion，消息已丢弃。", user_name)
        return False


def keyword_check(mag_content: str, user_name: str):
    if "绑定".__eq__(mag_content):
        bind(user_name)
        return True
    if "开始".__eq__(mag_content):
        start(user_name)
        return


def image_message(message):
    """
    <xml><ToUserName><![CDATA[wwe14538319d196cfa]]></ToUserName><FromUserName><![CDATA[username]]></FromUserName><CreateTime>1636869932</CreateTime><MsgType><![CDATA[image]]></MsgType><PicUrl><![CDATA[https://wework.qpic.cn/wwpic/144608_vSrhCdqkR3GGa0-_1636869932/]]></PicUrl><MsgId>7030302826418713870</MsgId><MediaId><![CDATA[17EQcZgqFnJIsFudL4aSk-iCiF6XdR-Mx-eKGLLophLc]]></MediaId><AgentID>1000002</AgentID></xml>
    :param message:
    :return:
    """
    print("this is a image message")
    xml_tree = ET.fromstring(message)
    msg_type = xml_tree.find("MsgType").text
    msg_id = xml_tree.find("MsgId").text
    pic_url = xml_tree.find("PicUrl").text
    user_name = xml_tree.find("FromUserName").text
    msg_time = timestamp2iso(int(xml_tree.find("CreateTime").text))
    if not bind_info_check(user_name):
        return
    wework_send.send_message("", f"暂不支持{msg_type}消息处理，消息已丢弃。", user_name)
    return
    # cloud_piece = CloudPiece(user_name)
    # res, url = cloud_piece.image_msg(msg_id, msg_type, msg_time, pic_url)
    # if res:
    #     wework_send.send_message("", f"消息保存成功。点击链接编辑：{url}", user_name)


def voice_message(message: bytes):
    """
    <xml><ToUserName><![CDATA[wwe14538319d196cfa]]></ToUserName><FromUserName><![CDATA[username]]></FromUserName><CreateTime>1636870250</CreateTime><MsgType><![CDATA[voice]]></MsgType><MediaId><![CDATA[17EQcZgqFnJIsFudL4aSk-iCiF6XdR-Mx-eKGLLophLc]]></MediaId><Format><![CDATA[amr]]></Format><MsgId>7030302926403775470</MsgId><AgentID>1000002</AgentID></xml>
    :param message:
    :return:
    """
    xml_tree = ET.fromstring(message)
    msg_type = xml_tree.find("MsgType").text
    user_name = xml_tree.find("FromUserName").text
    if not bind_info_check(user_name):
        return
    wework_send.send_message("", f"暂不支持{msg_type}消息处理，消息已丢弃。", user_name)
    return


def video_message(message: bytes):
    """

    """
    xml_tree = ET.fromstring(message)
    msg_type = xml_tree.find("MsgType").text
    user_name = xml_tree.find("FromUserName").text
    if not bind_info_check(user_name):
        return
    wework_send.send_message("", f"暂不支持{msg_type}消息处理，消息已丢弃。", user_name)
    return


def location_message(message: bytes):
    """
    <xml><ToUserName><![CDATA[wwe14538319d196cfa]]></ToUserName><FromUserName><![CDATA[username]]></FromUserName><CreateTime>1636870106</CreateTime><MsgType><![CDATA[location]]></MsgType><Location_X>30.2833</Location_X><Location_Y>120.0667</Location_Y><Scale>15</Scale><Label><![CDATA[]]></Label><MsgId>703030302645019854</MsgId><AgentID>1000002</AgentID></xml>
    :param message:
    :return:
    """
    xml_tree = ET.fromstring(message)
    msg_type = xml_tree.find("MsgType").text
    user_name = xml_tree.find("FromUserName").text
    if not bind_info_check(user_name):
        return
    wework_send.send_message("", f"暂不支持{msg_type}消息处理，消息已丢弃。", user_name)
    return


def link_message(message: bytes):
    """
    <xml><ToUserName><![CDATA[wwe14538319d196cfa]]></ToUserName><FromUserName><![CDATA[username]]></FromUserName><CreateTime>1636870225</CreateTime><MsgType><![CDATA[link]]></MsgType><Title><![CDATA[]]></Title><Description><![CDATA[]]></Description><Url><![CDATA[]]></Url><MsgId>703030302645019854</MsgId><AgentID>1000002</AgentID></xml>
    :param message:
    :return:
    """
    xml_tree = ET.fromstring(message)
    msg_type = xml_tree.find("MsgType").text
    user_name = xml_tree.find("FromUserName").text
    if not bind_info_check(user_name):
        return
    wework_send.send_message("", f"暂不支持{msg_type}消息处理，消息已丢弃。", user_name)
    return


@app.get("/notion/auth")
async def auth(code: str, state: str):
    """notion授权回调"""
    # 向 https://api.notion.com/v1/oauth/token 发起请求
    # code = request.rel_url.query["code"]
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": "https://message.singlelovely.cn/notion/auth"
    }
    client_id = config.get_config("notion", "client_id")
    client_secret = config.get_config("notion", "client_secret")

    authorization = base64.b64encode(f"{client_id}:{client_secret}".encode("utf-8")).decode("utf-8")
    headers = {
        'content-type': 'application/json',
        'Authorization': f'Basic {authorization}'
    }
    result = requests.post('https://api.notion.com/v1/oauth/token', json=data, headers=headers)
    if result.status_code != 200:
        # print(result.content, "----")
        return {"message": "Failure"}

    json_data = result.json()
    # 根据 chat_id、code、json_data 更新数据库
    access_token = json_data.get('access_token')
    database_id = get_database_id(access_token)
    # todo： state加密
    username = state
    res = update(username=username, access_token=access_token, database_id=database_id, code=code)

    if res:
        wework_send.send_message("", "授权成功", username)
        return {"message": "Success"}
    else:
        wework_send.send_message("", "授权失败", username)
        return {"message": "Failure"}

def start(username: str):
    text = """
          欢迎使用【CloudPiece】      \n
        CloudPiece 能够快速记录你的想法到 Notion 笔记中。快速记录，不流失任何一个灵感。\n
        1. 请拷贝 模板：https://www.notion.so/fd97073a0aef4654beead458bd7bd437 到自己的 Notion 中 \n
        2. 发送 绑定 开始绑定模板。
        """
    wework_send.send_message("", text, username)


def bind(username: str):
    """
    绑定用户
    :return:
    """
    if not create(username):
        wework_send.send_message("", "已绑定, 无需再次绑定", username)
        return

    client_id = config.get_config("notion", "client_id")
    redirect_uri = config.get_config("notion", "redirect_uri")
    state = username
    reply_message = f"https://api.notion.com/v1/oauth/authorize?owner=user" \
                    f"&client_id={client_id}" \
                    f"&redirect_uri={redirect_uri}" \
                    "&response_type=code" \
                    f"&state={state}"
    wework_send.send_message("点击链接授权绑定notion", reply_message, username)
    return


if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8888)
