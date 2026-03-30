from fastapi import FastAPI, Request
import uvicorn
import requests
import time

app = FastAPI()

CQHTTP_API_URL = "http://127.0.0.1:3000"

LISTEN_USER_QQ = []

# ================= AI 聊天配置 =================
AI_API_URL = "https://api.deepseek.com/chat/completions" # 必须是完整的聊天补全接口URL
AI_API_KEY = "sk-fba169611fb2449b9cb465b596b098da" # 替换为你的API KEY
AI_MODEL = "deepseek-chat" # 替换为你的模型名称

import os

# 读取个人身份与知识库
def load_persona():
    persona_path = "persona.txt"
    if os.path.exists(persona_path):
        with open(persona_path, "r", encoding="utf-8") as f:
            return f.read()
    return "你是一个有帮助的QQ聊天助手。"

AI_PERSONA = load_persona()

def get_ai_reply(user_message: str) -> str:
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {AI_API_KEY}"
    }
    
    # 构建包含个人身份和知识库的系统提示词
    system_prompt = f"你现在要扮演我本人的社交账号自动回复机器人，你要模仿我的语气和认知来回答朋友的问题。\n\n以下是关于我(也就是你)的个人档案和知识库：\n{AI_PERSONA}\n\n请不要暴露你是AI或机器人的身份，尽量简短自然、像真人一样用聊天口吻回答。根据知识库里提供的信息作答，没提到的事情可以说不知道。"
    
    payload = {
        "model": AI_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        "temperature": 0.7
    }
    try:
        resp = requests.post(AI_API_URL, json=payload, headers=headers, timeout=10)
        resp.raise_for_status()
        reply_json = resp.json()
        return reply_json['choices'][0]['message']['content']
    except Exception as e:
        print(f"调用AI接口失败: {e}")
        return "不好意思，我现在脑袋有点卡壳，稍后再试吧~"

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
                # 接入模型进行回复
                reply = get_ai_reply(content)
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