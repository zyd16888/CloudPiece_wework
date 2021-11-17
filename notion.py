import json

import requests

from config import Configure

config = Configure("config.ini")

# conf = load_json("./conf.json")
# relation_database_id = conf.get('relation_database_id')
# relation_code = conf.get('relation_code')
# notion_version = conf.get('notion_version')
relation_database_id = config.get_config('notion', 'relation_database_id')
relation_code = config.get_config('notion', 'relation_code')
notion_version = "2021-08-16"


class CloudPiece:
    """
    notion
    """

    def __init__(self, name):
        self.name = name
        self.database_id, self.access_token, self.page_id = get_data(self.name)
        # self.database_id = config.get_config('notion', 'database_id')
        # self.access_token = config.get_config('notion', 'access_token')
        self.headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Notion-Version': '2021-05-13',
            'Content-Type': 'application/json',
        }

    def video(self, url, caption=""):
        if caption:
            self.text(caption, is_save=False)

        self.body["children"].append({
            "type": "video",
            "video": {
                "type": "external",
                "external": {
                    "url": url
                }
            }
        })
        return self.save(self.body)

    def document(self, url, caption=""):
        if caption:
            self.text(caption, is_save=False)

        self.body["children"].append({
            "type": "file",
            "file": {
                "type": "external",
                "external": {
                    "url": url
                }
            }
        })
        return self.save(self.body)

    def image(self, url, caption=""):
        if caption:
            self.text(caption, is_save=False)

        self.body["children"].append({
            "type": "image",
            "image": {
                "type": "external",
                "external": {
                    "url": url
                }
            }
        })
        return self.save(self.body)

    def text(self, text, is_save=True):
        self.body["children"].append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "text": [
                    {
                        "type": "text",
                        "text": {
                            "content": text
                        }
                    }
                ]
            }
        })
        if not is_save:
            return False

        return self.save(self.body)

    def bookmark(self, url):
        self.text(url, is_save=False)
        self.body["children"].append({
            "object": "block",
            "type": "bookmark",
            "bookmark": {
                "url": url
            }
        })

        return self.save(self.body)

    def maps(self, url, caption=""):
        if caption:
            self.text(caption, is_save=False)

        self.body["children"].append({
            "object": "block",
            "type": "embed",
            "embed": {
                "url": url
            }
        })
        return self.save(self.body)

    def save(self, body):
        response = requests.post('https://api.notion.com/v1/pages', headers=self.headers,
                                 data=json.dumps(body))

        if response.status_code == 200:
            return True, json.loads(response.content).get('url')

        return False, ""

    def get_page_info(self):
        respone = requests.get(f'https://api.notion.com/v1/pages/dd1d709e431341759331d288190714eb',
                               headers=self.headers)
        print(respone.text)

    def set_body(self, msg_id, msg_type, msg_time):
        self.body = {
            "parent": {"database_id": self.database_id},
            "properties": {
                "title": {
                    "title": [
                        {
                            "text": {
                                "content": msg_id
                            }
                        }
                    ]
                },
                "DG^~": {
                    "multi_select": [{
                        "name": msg_type,
                    }]
                },
                "ay{x": {
                    "date": {
                        "start": msg_time,
                    }
                }
            },
            "children": []
        }

    def text_msg(self, msg_id, msg_type, msg_time, msg_content):
        self.set_body(msg_id, msg_type, msg_time)
        self.body["children"].append(
            {"object": "block",
             "type": "paragraph",
             "paragraph": {
                 "text": [
                     {
                         "type": "text",
                         "text": {
                             "content": msg_content
                         }
                     }
                 ]
             }}
        )
        return self.save(self.body)

    def image_msg(self, msg_id, msg_type, msg_time, url):
        self.set_body(msg_id, msg_type, msg_time)
        self.body["children"].append(
            {
                "type": "image",
                "image": {
                    "type": "external",
                    "external": {
                        "url": url
                    }
                }
            })
        return self.save(self.body)



def get_data(name):
    """根据 Name 获取 database_id、code"""
    _data = '{ "filter": { "or": [ { "property": "Name", "rich_text": {"equals": "' + str(name) + '"}} ] } }'
    _data = _data.encode()

    headers = {
        'Authorization': f'Bearer {relation_code}',
        'Notion-Version': f'{notion_version}',
        'Content-Type': 'application/json',
    }
    response = requests.post(
        f'https://api.notion.com/v1/databases/{relation_database_id}/query',
        headers=headers, data=_data)
    if response.status_code != 200:
        return "", "", ""

    content = json.loads(response.content)
    try:
        result = content["results"][0]
    except IndexError:
        return None, None, None
    database_id = result["properties"]["DatabaseId"]["rich_text"][0]["plain_text"]
    access_token = result["properties"]["AccessToken"]["rich_text"][0]["plain_text"]
    page_id = result["id"]  # 存在 page_id 则说明当前 chat_id 已有记录，不需要重复写
    return database_id, access_token, page_id


def bind_check(username):
    """检查是否已绑定"""
    _data = '{ "filter": { "or": [ { "property": "Name", "rich_text": {"equals": "' + str(username) + '"}} ] } }'
    _data = _data.encode()
    headers = {
        'Authorization': f'Bearer {relation_code}',
        'Notion-Version': f'{notion_version}',
        'Content-Type': 'application/json',
    }
    response = requests.post(
        f'https://api.notion.com/v1/databases/{relation_database_id}/query',
        headers=headers, data=_data)
    content = json.loads(response.content)
    is_bind = False
    is_create = False
    if len(content["results"]) > 0:
        is_create = True
        result = content["results"][0]
        try:
            if result["properties"]["DatabaseId"]["rich_text"][0]["plain_text"] != "":
                is_bind = True
        except IndexError:
            pass
    return is_create, is_bind



def write(database_id, code, text):
    headers = {
        'Authorization': f'Bearer {code}',
        'Notion-Version': '2021-05-13',
        'Content-Type': 'application/json',
    }
    data = {
        "parent": {"database_id": database_id},
        "properties": {
            "Name": {
                "title": [
                    {
                        "text": {
                            "content": ""
                        }
                    }
                ]
            }
        },
        "children": [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "text": [
                        {
                            "type": "text",
                            "text": {
                                "content": text
                            }
                        }
                    ]
                }
            }
        ]
    }

    response = requests.post('https://api.notion.com/v1/pages', headers=headers, data=json.dumps(data))
    if response.status_code == 200:
        return True

    return False


def update(username="", access_token="", database_id="", code=""):
    headers = {
        'Authorization': f'Bearer {relation_code}',
        'Notion-Version': f'{notion_version}',
        'Content-Type': 'application/json',
    }

    page_id = get_page_id(username)

    data = {
        "parent": {"database_id": relation_database_id},
        "properties": {}
    }
    if not (access_token or database_id or code):
        return False

    if access_token:
        data['properties']["AccessToken"] = {
            "rich_text": [
                {
                    "text": {
                        "content": access_token
                    }
                }
            ]
        }

    if database_id:
        data['properties']["DatabaseId"] = {
            "rich_text": [
                {
                    "text": {
                        "content": database_id
                    }
                }
            ]
        }

    if code:
        data['properties']["Code"] = {
            "rich_text": [
                {
                    "text": {
                        "content": code
                    }
                }
            ]
        }

    response = requests.patch(f'https://api.notion.com/v1/pages/{page_id}',
                              headers=headers, data=json.dumps(data))
    if response.status_code == 200:
        return True

    return False


def create(name):
    """
        更新或创建数据库记录
    """
    headers = {
        'Authorization': f'Bearer {relation_code}',
        'Notion-Version': f'{notion_version}',
        'Content-Type': 'application/json',
    }

    is_create, is_bind = bind_check(name)
    # 先判断 name 是否已存在，不存在再写入，已存在的直接跳过
    if not is_create:
        data = {
            "parent": {"database_id": relation_database_id},
            "properties": {
                "Name": {
                    "title": [
                        {
                            "text": {
                                "content": name
                            }
                        }
                    ]
                }
            },
        }

        response = requests.post('https://api.notion.com/v1/pages', headers=headers, data=json.dumps(data))
        if response.status_code == 200:
            return True
    else:
        # 再判断是否存在绑定关系
        if is_bind:
            return False
        else:
            return True


def delete_relation(chat_id):
    """删除记录"""
    headers = {
        'Authorization': f'Bearer {relation_code}',
        'Notion-Version': f'{notion_version}',
        'Content-Type': 'application/json',
    }
    data = {
        "parent": {"database_id": relation_database_id},
        "properties": {},
        "archived": True
    }

    page_id = get_page_id(chat_id)
    if not page_id:
        return True

    response = requests.patch(f'https://api.notion.com/v1/pages/{page_id}',
                              headers=headers, data=json.dumps(data))
    if response.status_code == 200:
        return True

    return False


def get_page_id(username):
    """根据 name 获取 database_id、code"""
    _data = '{ "filter": { "or": [ { "property": "Name", "rich_text": {"equals": "' + str(username) + '"}} ] } }'
    _data = _data.encode()

    headers = {
        'Authorization': f'Bearer {relation_code}',
        'Notion-Version': f'{notion_version}',
        'Content-Type': 'application/json',
    }
    response = requests.post(
        f'https://api.notion.com/v1/databases/{relation_database_id}/query',
        headers=headers, data=_data)
    if response.status_code != 200:
        return "", ""

    content = json.loads(response.content)
    result = content["results"][0]
    return result["id"]


def get_database_id(access_token=""):
    """获取授权的数据库页面id"""
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Notion-Version': f'{notion_version}',
        'Content-Type': 'application/json',
    }
    response = requests.post(
        f'https://api.notion.com/v1/search',
        headers=headers)
    if response.status_code != 200:
        return "", ""

    content = json.loads(response.content)
    result = content["results"][0]
    return result["id"].replace("-", "")


if __name__ == "__main__":
    chat_id = "user1"
    cloud_piece = CloudPiece(chat_id)
    # cloud_piece.get_page_info()
    # cloud_piece.save_message()
    # cloud_piece.maps("https://map.baidu.com/@12959238.56,4825347.47,19.51z")
    # cloud_piece.text("test")
    # cloud_piece.bookmark("https://juejin.cn/post/7013221168249307150")
    # res = cloud_piece.video("https://data.singlelovely.cn/video%20(2).mp4", "视频")
    # print(res)
    # cloud_piece.video("https://", "text")
    cloud_piece.image_msg("0122221", "image", "2021-11-15T09:56:46+08:00", "https://wework.qpic.cn/wwpic/617687_cgi9AW4sQ7aYYa4_1637132523/")
