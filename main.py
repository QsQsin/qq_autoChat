from fastapi import FastAPI, Request
import uvicorn
import requests
import time

app = FastAPI()

CQHTTP_API_URL = "http://127.0.0.1:3000"

RULES = {
    "在吗": "在的，我现在正在使用机器人自动回复。有什么事吗？",
    "测试": "自动回复测试成功！",
    "你好": "你好呀！[自动回复]",
}
DEFAULT_REPLY = "【自动回复】刚才消息收到了，如果不着急我稍后会统一回复。"
LISTEN_USER_QQ = [] 

@app.post("/")
async def handle_post(request: Request):
    try:
        # 解析收到的 JSON
        msg_data = await request.json()
        
        # 屏蔽烦人的心跳信息打印
        if msg_data.get('post_type') == 'meta_event':
            return {}
            
        # 如果是私聊消息
        if msg_data.get('post_type') == 'message' and msg_data.get('message_type') == 'private':
            sender_id = msg_data.get('user_id')
            content = msg_data.get('raw_message')
            
            print(f"[{time.strftime('%H:%M:%S')}] 收到 QQ({sender_id}) 的消息: {content}")
            
            # 避免由于配置了 reportSelfMessage 导致无限回复自己
            if sender_id != msg_data.get('self_id') and (not LISTEN_USER_QQ or sender_id in LISTEN_USER_QQ):
                reply = RULES.get(content, DEFAULT_REPLY)
                send_reply(sender_id, reply)
                
    except Exception as e:
        print(f"处理时遇到小错误: {e}")
        
    # 不管怎样都返回空字典告知 NapCat 成功收到，避免它报错
    return {}

def send_reply(user_id, message):
    api_endpoint = f"{CQHTTP_API_URL}/send_private_msg"
    payload = {
        "user_id": user_id,
        "message": message
    }
    headers = {
        # 你的配置文件里带有 token 验证，必须加上！
        "Authorization": "Bearer Uk7NjHuX8cQRnB6h"
    }
    try:
        response = requests.post(api_endpoint, json=payload, headers=headers, timeout=5)
        if response.status_code == 200:
            print(f"[{time.strftime('%H:%M:%S')}] 已成功回复 QQ({user_id}): {message}")
        else:
             print(f"[{time.strftime('%H:%M:%S')}] 回复失败，返回状态码: {response.status_code}，响应: {response.text}")
    except Exception as e:
        print(f"发送消息失败，确保 NapCat 启用了 3000 端口: {e}")

if __name__ == '__main__':
    print("====================================")
    print("🚀 强大版的 QQ 机器人监听服务已经连线启动 (端口 8080)！")
    print("====================================")
    # 启动服务
    uvicorn.run(app, host="127.0.0.1", port=8080, log_level="warning")