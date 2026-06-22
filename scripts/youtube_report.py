#!/usr/bin/env python3
"""
YouTube频道《真的很博通》日报 - GitHub Actions版本
从环境变量读取配置，适用于云部署
"""
import os
import sys
import re
import json
import time
import requests
from datetime import datetime

# ============ 配置（从环境变量读取） ============
CHANNEL_ID = "UCNiJNzSkfumLB7bYtXcIEmg"
CHANNEL_NAME = "真的很博通"
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
MAX_RETRIES = 3
RETRY_DELAY = 5

def log(msg, level="INFO"):
    """输出日志"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {msg}")

def send_telegram(text, retry=0):
    """发送Telegram消息"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "HTML"
        }
        
        response = requests.post(url, json=data, timeout=15)
        result = response.json()
        
        if result.get("ok"):
            log("Telegram发送成功")
            return True
        else:
            log(f"Telegram API返回错误: {result}", "ERROR")
            return False
    except Exception as e:
        if retry < MAX_RETRIES:
            log(f"Telegram发送失败，{RETRY_DELAY}秒后重试 ({retry+1}/{MAX_RETRIES}): {e}", "WARN")
            time.sleep(RETRY_DELAY)
            return send_telegram(text, retry + 1)
        else:
            log(f"Telegram发送最终失败: {e}", "ERROR")
            return False

def fetch_rss():
    """获取RSS feed"""
    rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={CHANNEL_ID}"
    
    for attempt in range(MAX_RETRIES):
        try:
            headers = {"User-Agent": "Mozilla/5.0 (compatible; YouTube Daily Report)"}
            response = requests.get(rss_url, headers=headers, timeout=20)
            
            if response.status_code != 200:
                log(f"RSS请求失败 (attempt {attempt+1}): HTTP {response.status_code}", "WARN")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
                    continue
                return None
            
            content = response.text
            
            # 检查是否是错误页面
            if "<!DOCTYPE html>" in content or "Error" in content[:200]:
                log(f"RSS返回HTML错误页面 (attempt {attempt+1})", "WARN")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
                    continue
                return None
            
            log(f"RSS获取成功 (attempt {attempt+1})")
            return content
        except Exception as e:
            log(f"RSS获取失败 (attempt {attempt+1}/{MAX_RETRIES}): {e}", "WARN")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
    
    return None

def parse_videos(content):
    """解析RSS内容"""
    entries = re.findall(r"<entry>(.*?)</entry>", content, re.DOTALL)
    
    videos = []
    for entry in entries[:15]:
        title_m = re.search(r"<title>(.*?)</title>", entry)
        vid_m = re.search(r"<yt:videoId>(.*?)</yt:videoId>", entry)
        views_m = re.search(r'views="(\d+)"', entry)
        pub_m = re.search(r"<published>(.*?)</published>", entry)
        
        if title_m and vid_m:
            published = ""
            if pub_m:
                try:
                    dt = datetime.fromisoformat(pub_m.group(1).replace("+00:00", ""))
                    published = dt.strftime("%m-%d %H:%M")
                except Exception:
                    pass
            
            videos.append({
                "title": title_m.group(1),
                "url": f"https://www.youtube.com/watch?v={vid_m.group(1)}",
                "views": views_m.group(1) if views_m else "0",
                "published": published
            })
    
    return videos

def generate_report(videos):
    """生成日报内容"""
    today = datetime.now().strftime("%Y-%m-%d")
    
    report = f"📺 YouTube频道《{CHANNEL_NAME}》日报\n"
    report += f"📅 {today}\n"
    report += "━━━━━━━━━━━━━━━━━━\n\n"
    report += f"🆕 最新{len(videos)}个视频：\n\n"
    
    for i, v in enumerate(videos, 1):
        report += f"{i}. {v['title']}\n"
        if v['published']:
            report += f"   📅 {v['published']}"
        report += f" | 👁 {v['views']}次\n"
        report += f"   🔗 {v['url']}\n\n"
    
    report += "━━━━━━━━━━━━━━━━━━\n"
    report += "💡 点击链接可直接观看视频"
    
    return report

def main():
    log("=" * 50)
    log("YouTube日报推送任务开始（GitHub Actions）")
    
    # 检查配置
    if not TELEGRAM_BOT_TOKEN:
        log("错误：未设置 TELEGRAM_BOT_TOKEN 环境变量", "ERROR")
        sys.exit(1)
    
    if not TELEGRAM_CHAT_ID:
        log("错误：未设置 TELEGRAM_CHAT_ID 环境变量", "ERROR")
        sys.exit(1)
    
    log(f"Telegram Chat ID: {TELEGRAM_CHAT_ID}")
    
    # 获取RSS
    content = fetch_rss()
    if not content:
        error_msg = f"""⚠️ YouTube日报推送失败

频道：《{CHANNEL_NAME}》
时间：{datetime.now().strftime("%Y-%m-%d %H:%M")}

YouTube RSS API暂时不可用（已重试{MAX_RETRIES}次）。
将在明天13:00自动重试。"""
        send_telegram(error_msg)
        log("RSS获取最终失败，已发送错误通知", "ERROR")
        sys.exit(1)
    
    # 解析视频
    videos = parse_videos(content)
    if not videos:
        error_msg = f"""⚠️ YouTube日报解析失败

频道：《{CHANNEL_NAME}》
时间：{datetime.now().strftime("%Y-%m-%d %H:%M")}

RSS内容解析失败，可能YouTube格式变更。"""
        send_telegram(error_msg)
        log("视频解析失败", "ERROR")
        sys.exit(1)
    
    log(f"成功解析{len(videos)}个视频")
    
    # 生成并发送日报
    report = generate_report(videos)
    success = send_telegram(report)
    
    if success:
        log("✅ 日报推送成功!")
    else:
        log("❌ 日报推送失败", "ERROR")
        sys.exit(1)

if __name__ == "__main__":
    main()
