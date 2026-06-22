#!/usr/bin/env python3
"""
YouTube频道《真的很博通》日报 - GitHub Actions版本
只推送当天更新的视频
"""
import os
import sys
import re
import json
import time
import requests
from datetime import datetime, timezone, timedelta

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
            "text": text
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

def parse_today_videos(content):
    """解析RSS内容，只返回当天的视频"""
    entries = re.findall(r"<entry>(.*?)</entry>", content, re.DOTALL)
    
    # 获取今天的日期（北京时间，UTC+8）
    beijing_tz = timezone(timedelta(hours=8))
    today = datetime.now(beijing_tz).date()
    
    log(f"查询日期: {today}")
    
    videos = []
    for entry in entries:
        title_m = re.search(r"<title>(.*?)</title>", entry)
        vid_m = re.search(r"<yt:videoId>(.*?)</yt:videoId>", entry)
        views_m = re.search(r'views="(\d+)"', entry)
        pub_m = re.search(r"<published>(.*?)</published>", entry)
        
        if title_m and vid_m and pub_m:
            # 解析发布时间
            try:
                pub_str = pub_m.group(1)
                pub_dt = datetime.fromisoformat(pub_str.replace("+00:00", "+00:00"))
                pub_date = pub_dt.astimezone(beijing_tz).date()
                
                # 只保留当天的视频
                if pub_date == today:
                    published = pub_dt.astimezone(beijing_tz).strftime("%H:%M")
                    
                    videos.append({
                        "title": title_m.group(1),
                        "url": f"https://www.youtube.com/watch?v={vid_m.group(1)}",
                        "views": views_m.group(1) if views_m else "0",
                        "published": published
                    })
                    log(f"找到今日视频: {title_m.group(1)[:50]}...")
            except Exception as e:
                log(f"解析日期失败: {e}", "WARN")
                continue
    
    return videos

def generate_report(videos):
    """生成日报内容"""
    today = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d")
    
    if not videos:
        # 当天无更新
        report = f"📺 YouTube频道《{CHANNEL_NAME}》日报\n"
        report += f"📅 {today}\n"
        report += "━━━━━━━━━━━━━━━━━━\n\n"
        report += "😴 今日无更新\n\n"
        report += "频道今天没有发布新视频。\n\n"
        report += "━━━━━━━━━━━━━━━━━━\n"
        report += "💡 点击链接访问频道: https://www.youtube.com/@zhendehenbotong"
    else:
        # 有更新
        report = f"📺 YouTube频道《{CHANNEL_NAME}》日报\n"
        report += f"📅 {today}\n"
        report += "━━━━━━━━━━━━━━━━━━\n\n"
        report += f"🆕 今日更新 {len(videos)} 个视频：\n\n"
        
        for i, v in enumerate(videos, 1):
            report += f"{i}. {v['title']}\n"
            report += f"   ⏰ {v['published']}"
            report += f" | 👁 {v['views']}次\n"
            report += f"   🔗 {v['url']}\n\n"
        
        report += "━━━━━━━━━━━━━━━━━━\n"
        report += "💡 点击链接可直接观看视频"
    
    return report

def main():
    log("=" * 50)
    log("YouTube日报推送任务开始（GitHub Actions）")
    log(f"模式: 只推送当天更新的视频")
    
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
    
    # 解析当天视频
    videos = parse_today_videos(content)
    log(f"今日视频数量: {len(videos)}")
    
    # 生成并发送日报
    report = generate_report(videos)
    success = send_telegram(report)
    
    if success:
        log("✅ 日报推送成功!")
        if videos:
            log(f"推送了 {len(videos)} 个今日视频")
        else:
            log("今日无更新，已发送无更新通知")
    else:
        log("❌ 日报推送失败", "ERROR")
        sys.exit(1)

if __name__ == "__main__":
    main()
