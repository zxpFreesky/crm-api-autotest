# coding=utf-8
import os
import smtplib  # 连接服务器模块
# 普通文本邮件
from email.mime.text import MIMEText
# 添加附件模块
from email.mime.multipart import MIMEMultipart


# 获取最新文件
def get_new_file(dir):
    files = os.listdir(dir)
    # 根据时间倒序
    files.sort(key=lambda fn: os.path.getmtime(dir + '\\' + fn))
    # print(new_path)

    # print(os.path.isdir(new_path))
    if os.path.isfile(os.path.join(dir, files[-1])):
        return os.path.join(dir, files[-2])
    else:
        # 递归要注意闭包问题，否则会返回None
        return get_new_file(os.path.join(dir, files[-2]))


sender = "1169459364@qq.com"
pwd = "hhezdtbcamyuhabb"
receivers = ["326186713@qq.com", "1169459364@qq.com"]
body = '这是自动化测试邮件，请勿回复，祝工作愉快'


def send_mail(title, user, pwd, receiver, file=None):
    msg = MIMEMultipart()
    msg["subject"] = title
    msg["from"] = user
    msg['To'] = ','.join(receivers)
    # 文字部分
    part = MIMEText(body)
    msg.attach(part)  # 将文字添加到邮件实例

    # 附件
    if file:
        with open(file, "rb")as fp:
            attach = fp.read()
        att = MIMEText(attach, 'base64', 'utf-8')
        att["Content-Type"] = "application/octet-stream"
        att["Content-Disposition"] = 'attachment; filename="{}"'.format(os.path.basename(file))
        msg.attach(att)

    try:
        m = smtplib.SMTP_SSL("smtp.qq.com")  # 连接服务器
        m.login(sender, pwd)  # 登录服务器
        m.sendmail(sender, msg['To'].split(','), msg.as_string())  # 发送
        m.quit()
        print("邮件发送成功")
    except smtplib.SMTPException as e:
        print('except:%s' % e)


if __name__ == "__main__":
    import json

    send_mail("测试一下", sender, pwd, receivers, get_new_file("../report/"))
