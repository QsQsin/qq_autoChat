from fastapi import FastAPI, Request
import uvicorn
import requests
import time
import os
import random

app = FastAPI()

CQHTTP_API_URL = "http://127.0.0.1:3000"

LISTEN_USER_QQ = []

# ================= AI 聊天配置 =================
AI_API_URL = "https://api.deepseek.com/chat/completions" # 必须是完整的聊天补全接口URL
AI_API_KEY = "sk-fba169611fb2449b9cb465b596b098da" # 替换为你的API KEY
AI_MODEL = "deepseek-chat" # 替换为你的模型名称

import os

# 构建系统提示词
def get_system_prompt():
    persona_path = "persona.txt"
    persona = "你是一个有帮助的QQ聊天助手。"
    if os.path.exists(persona_path):
        with open(persona_path, "r", encoding="utf-8") as f:
            persona = f.read()

    # 动态读取所有表情包分类
    memes_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memes")
    meme_categories = []
    if os.path.exists(memes_dir):
        # 获取 memes 下所有的文件夹（即分类）
        meme_categories = [d for d in os.listdir(memes_dir) if os.path.isdir(os.path.join(memes_dir, d))]

    category_list_str = "、".join(meme_categories) if meme_categories else "无"

    system_prompt = f"""你现在要扮演我本人的社交账号自动回复机器人，你要模仿我的语气和认知来回答朋友的问题。

以下是关于我(也就是你)的个人档案和知识库：
{persona}

【表情包发送规则】
你现在拥有发送本地表情包的能力！
我现在的本地表情包库有以下分类：[{category_list_str}]

如果当前的聊天语境非常适合发表情包烘托气氛（比如搞笑、无奈、开心、嘲讽），你可以根据情绪从上面的【分类】中选择一个最合适的，然后在回复中输出一个特殊的格式：[表情包:分类名] 。
例如，你想发一个搞笑的表情，你可以回复：这太草了 [表情包:搞笑]
注意：
1. 只能使用上面列表里存在的分类名！不能自己发明！
2. 保持真人聊天的频率，不要每句话都带表情包，看情况加！

请不要暴露你是AI或机器人的身份，尽量简短自然、像真人一样聊天。"""
    
    return system_prompt

def get_ai_reply(user_message: str) -> str:
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {AI_API_KEY}"
    }
    
    payload = {
        "model": AI_MODEL,
        "messages": [
            {"role": "system", "content": get_system_prompt()},
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
import re

# =======================================================
def process_reply_for_memes(reply_text: str) -> str:
    """处理带有 [表情包:分类] 标记的回复，替换为该分类下的本地真实表情包"""
    MEMES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memes")
    
    # 查找所有类似 [表情包:搞笑] 的标记
    matches = re.findall(r'\[表情包:(.*?)\]', reply_text)
    
    for category in matches:
        category_dir = os.path.join(MEMES_DIR, category)
        replaced = False
        
        # 检查分类文件夹是否存在
        if os.path.exists(category_dir) and os.path.isdir(category_dir):
            valid_images = [f for f in os.listdir(category_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp'))]
            if valid_images:
                # 在对应分类下随机抽取一张
                chosen_image = random.choice(valid_images)
                abs_path = os.path.join(category_dir, chosen_image).replace("\\", "/")
                # 构造 CQ 码形式的图片
                cq_image = f"[CQ:image,file=file:///{abs_path}]"
                
                # 替换文本中的标记 (只替换一个该分类的标记)
                reply_text = reply_text.replace(f"[表情包:{category}]", cq_image, 1)
                replaced = True
                
        if not replaced:
             # 如果文件夹不存在或没图片，直接把标记删掉免得露馅
             reply_text = reply_text.replace(f"[表情包:{category}]", "")
             
    # 保险起见，把所有没被正则捕获处理干净的残留表情包标记清理掉
    reply_text = re.sub(r'\[表情包.*?\]', '', reply_text)
        
    return reply_text.strip()

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
                raw_reply = get_ai_reply(content)
                # 处理可能带有的表情包发送需求
                final_reply = process_reply_for_memes(raw_reply)
                
                send_reply(sender_id, final_reply)
                
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