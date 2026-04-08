"""集成测试：真实调用 pushplus 发送微信消息"""
import unittest
from monitor.notifier import send_wechat


class TestWechatReal(unittest.TestCase):
    """实际调用 pushplus 接口，验证微信能否收到消息"""

    def test_real_send(self):
        """发送一条真实的测试消息到微信"""
        result = send_wechat(
            title="🔔 推送测试",
            content="<p>这是一条来自自动化测试的消息，收到说明推送功能正常。</p>",
        )
        self.assertTrue(result, "微信推送失败，请检查 PUSHPLUS_TOKEN 是否正确")


if __name__ == "__main__":
    unittest.main()
