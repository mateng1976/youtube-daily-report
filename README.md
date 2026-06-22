# YouTube 频道日报 - 自动推送

每天自动获取《真的很博通》YouTube 频道最新视频，并推送到 Telegram。

## 功能

- ✅ 每天 13:00（北京时间）自动推送
- ✅ 获取最新 15 个视频
- ✅ 自动重试机制（3次）
- ✅ 错误通知
- ✅ 云端运行，无需开机

## 配置

### GitHub Secrets

在仓库 Settings → Secrets and variables → Actions 中添加：

| Secret 名称 | 说明 |
|-------------|------|
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token |
| `TELEGRAM_CHAT_ID` | Telegram Chat ID |

### 修改推送时间

编辑 `.github/workflows/daily-report.yml`：

```yaml
on:
  schedule:
    # UTC 时间 = 北京时间 - 8小时
    - cron: '0 5 * * *'  # 13:00 北京时间
```

## 监控

- **Actions 页面**：查看运行日志
- **手动触发**：Actions → Run workflow

## 文件结构

```
.github/
  workflows/
    daily-report.yml    # GitHub Actions 配置
scripts/
  youtube_report.py     # Python 脚本
README.md               # 说明文档
```
