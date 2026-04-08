"""微信推送通知（使用pushplus）"""
import requests
from config import PUSHPLUS_TOKEN
from utils.logger import setup_logger

logger = setup_logger("notifier")


def send_wechat(title: str, content: str) -> bool:
    """
    通过pushplus发送微信推送
    注册地址: https://www.pushplus.plus/
    :param title: 消息标题
    :param content: 消息内容（支持HTML）
    :return: 是否发送成功
    """
    if not PUSHPLUS_TOKEN:
        logger.warning("未配置PUSHPLUS_TOKEN，跳过微信推送")
        print(f"[本地提醒] {title}\n{content}")
        return False

    url = "http://www.pushplus.plus/send"
    payload = {
        "token": PUSHPLUS_TOKEN,
        "title": title,
        "content": content,
        "template": "html",
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        data = resp.json()
        if data.get("code") == 200:
            logger.info(f"微信推送成功: {title}")
            return True
        else:
            logger.error(f"微信推送失败: {data}")
            return False
    except Exception as e:
        logger.error(f"微信推送异常: {e}")
        return False


def format_signal_message(signals: list[dict]) -> str:
    """将信号列表格式化为HTML消息"""
    if not signals:
        return "<p>今日无交易信号</p>"

    buy_signals = [s for s in signals if s["action"] == "建议买入"]
    if not buy_signals:
        return "<p>今日无买入信号（所有品种评分未达阈值）</p>"

    html = "<h3>🔔 国债逆回购信号提醒</h3>"
    html += "<table border='1' cellpadding='5' cellspacing='0'>"
    html += "<tr><th>品种</th><th>利率%</th><th>评分</th><th>预期收益</th><th>原因</th></tr>"

    for s in buy_signals:
        reasons = "、".join(s["reasons"]) if s["reasons"] else "-"
        html += (
            f"<tr>"
            f"<td>{s['name']}({s['symbol']})</td>"
            f"<td>{s['rate']:.2f}</td>"
            f"<td>{s['score']:.0f}</td>"
            f"<td>{s['expected_profit']:.4f}元</td>"
            f"<td>{reasons}</td>"
            f"</tr>"
        )

    html += "</table>"
    html += f"<p>本金: 3000元 | 模式: 虚拟交易</p>"
    return html
