# email_service.py
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from loguru import logger

# 从 settings.py 导入配置
from common.global_variant import config

# 创建一个 ConnectionConfig 对象
conf = ConnectionConfig(
    MAIL_USERNAME=config.get('yeah_mail.from'),  # 发件人邮箱地址
    MAIL_PASSWORD=config.email.secret,
    MAIL_FROM=config.get('yeah_mail.from'),
    MAIL_PORT=config.email.port,
    MAIL_FROM_NAME=config.email.from_name,  # 发件人邮箱地址
    MAIL_SERVER=config.email.server,
    MAIL_STARTTLS=False,
    MAIL_SSL_TLS=True,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
)

EMAIL_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang='zh-CN'>
<head>
    <meta charset='UTF-8'>
    <meta name='viewport' content='width=device-width, initial-scale=1.0'>
    <title>身份认证</title>
</head>
<body style='margin: 0; padding: 0; font-family: "Courier New', Courier, monospace; background-color: #1a1a1a;"">
    <table border='0' cellpadding='0' cellspacing='0' width="100%">
        <tr>
            <td style='padding: 40px 10px;'>
                <table align='center' border='0' cellpadding='0' cellspacing='0' width='600' style='max-width: 600px; border-collapse: collapse;'>
                    <tr>
                        <td align='center' style='padding-bottom: 20px;'>
                            <h2 style='color: #00ffff; font-weight: normal; letter-spacing: 2px; margin: 0;'>尊敬的: {email}</h2>
                        </td>
                    </tr>
                    <tr>
                        <td style='background-color: #2a2a2a; border: 1px solid #444444; border-radius: 5px; padding: 30px;'>
                            <table border='0' cellpadding='0' cellspacing='0' width='100%'>
                                <tr>
                                    <td align='center' style='color: #cccccc; font-size: 16px;'>
                                        <p style='margin: 0;'>{gree}</p>
                                    </td>
                                </tr>
                                <tr>
                                    <td align='left' style='padding: 30px 0;'>
                                        <div style='background-color: #111111; padding: 15px; border-radius: 5px;'>
                                            <pre style='font-size: 14px; font-weight: bold; color: #00ff7f; margin: 0; letter-spacing: 1px; text-shadow: 0 0 4px rgba(0, 255, 127, 0.5);'>{content}</pre>
                                        </div>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""


async def send_email(email: str, subject: str, content: str, is_code: bool = True):
    """
    发送邮件的通用函数。

    Args:
        recipients (List[str]): 收件人邮箱列表。
        subject (str): 邮件主题。
        body (str): 邮件内容 (可以是HTML或纯文本)。
    """
    if is_code:
        body = EMAIL_HTML_TEMPLATE.format(email=email, gree='您的验证码已生成:', content=content)
    else:
        body = EMAIL_HTML_TEMPLATE.format(email=email, gree='感谢您的使用:', content=content)
    message = MessageSchema(subject=subject, recipients=[email], body=body, subtype="html")  # 收件人列表  # 或者 "plain"

    fm = FastMail(conf)
    try:
        await fm.send_message(message)
        logger.success(f"邮件已成功发送至: {email}")
        return True
    except Exception as e:
        logger.error(f"邮件发送失败: {e}")
        return False
