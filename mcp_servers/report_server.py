import json
import os
import requests
from datetime import datetime


class ReportMCPClient:
    """
    报告分析 MCP 客户端
    暴露的能力:
    - collect_result: 收集测试结果
    - get_summary: 获取执行摘要
    - get_history: 获取历史趋势
    - export_report: 导出报告
    - notify_wecom: 推送结果到企业微信群机器人
    """

    def __init__(self, report_dir="reports", history_file=None,
                 wecom_webhook=None, wecom_mentioned_list=None,
                 wecom_mentioned_mobile_list=None):
        self.report_dir = os.path.abspath(report_dir)
        self.history_file = history_file or os.path.join(self.report_dir, "history.json")
        os.makedirs(self.report_dir, exist_ok=True)
        self._current_results = []
        self.wecom_webhook = wecom_webhook
        self.wecom_mentioned_list = wecom_mentioned_list or []
        self.wecom_mentioned_mobile_list = wecom_mentioned_mobile_list or []

    def collect_result(self, test_name, status, duration=0, error_msg=None, response=None, request_info=None):
        """
        收集单条测试结果
        :param test_name: 用例名称
        :param status: pass / fail / error / skip
        :param duration: 执行耗时 (秒)
        :param error_msg: 失败信息
        :param response: 接口响应
        :param request_info: 请求信息
        """
        result = {
            "test_name": test_name,
            "status": status,
            "duration": round(duration, 3),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        if error_msg:
            result["error_msg"] = error_msg
        if response:
            result["response"] = response
        if request_info:
            result["request"] = request_info

        self._current_results.append(result)
        return result

    def get_summary(self):
        """
        获取当前执行摘要
        :return: 汇总统计
        """
        total = len(self._current_results)
        passed = sum(1 for r in self._current_results if r["status"] == "pass")
        failed = sum(1 for r in self._current_results if r["status"] == "fail")
        errors = sum(1 for r in self._current_results if r["status"] == "error")
        skipped = sum(1 for r in self._current_results if r["status"] == "skip")
        total_duration = sum(r["duration"] for r in self._current_results)

        pass_rate = f"{passed / total * 100:.2f}" if total > 0 else "0.00"

        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "skipped": skipped,
            "pass_rate": pass_rate,
            "total_duration": round(total_duration, 3),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    def get_history(self, limit=20):
        """
        获取历史趋势数据
        :param limit: 返回最近 N 次执行记录
        :return: 历史列表
        """
        if not os.path.exists(self.history_file):
            return []
        with open(self.history_file, "r", encoding="utf-8") as f:
            history = json.load(f)
        return history[-limit:]

    def save_to_history(self):
        """
        保存当前结果到历史记录
        """
        summary = self.get_summary()
        summary["results"] = self._current_results

        history = []
        if os.path.exists(self.history_file):
            with open(self.history_file, "r", encoding="utf-8") as f:
                history = json.load(f)

        history_entry = {
            "success": summary["passed"],
            "all": summary["total"],
            "fail": summary["failed"],
            "skip": summary["skipped"],
            "error": summary["errors"],
            "runtime": f"{summary['total_duration']} S",
            "begin_time": summary["timestamp"],
            "pass_rate": summary["pass_rate"],
        }
        history.append(history_entry)

        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)

        return history_entry

    def get_failed_details(self):
        """
        获取所有失败用例详情 (供 AI 分析)
        """
        return [r for r in self._current_results if r["status"] in ("fail", "error")]

    def export_json_report(self, filename=None):
        """
        导出 JSON 结构化报告
        """
        if filename is None:
            filename = f"{datetime.now().strftime('%Y-%m-%d_%H_%M_%S')}_report.json"
        filepath = os.path.join(self.report_dir, filename)

        report = {
            "summary": self.get_summary(),
            "results": self._current_results,
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        return filepath

    def reset(self):
        self._current_results = []

    # ── 企业微信通知 ──────────────────────────────────────────────

    def _build_wecom_markdown(self, summary, env_name="", analysis_results=None):
        """
        构建 markdown 类型消息

        企业微信 markdown 语法子集:
        - 标题 (### 三级)
        - 加粗 (**bold**)
        - 引用 (> text)
        - 字体颜色: info(绿) / comment(灰) / warning(橙红)
        - @成员: <@userid> (仅支持 userid, 不支持手机号)

        :param summary: get_summary() 返回的字典
        :param env_name: 环境名称
        :param analysis_results: RootCauseAnalyzer.batch_analyze() 返回的分析结果列表
        :return: markdown content 字符串
        """
        total = summary["total"]
        passed = summary["passed"]
        failed = summary["failed"]
        errors = summary["errors"]
        skipped = summary["skipped"]
        pass_rate = summary["pass_rate"]
        duration = summary["total_duration"]
        timestamp = summary["timestamp"]

        if float(pass_rate) >= 100:
            status_text = "<font color=\"info\">全部通过</font>"
        elif float(pass_rate) >= 80:
            status_text = f"<font color=\"warning\">部分失败({failed}条)</font>"
        else:
            status_text = f"<font color=\"warning\">大量失败({failed}条)</font>"

        env_line = f"\n> 测试环境：<font color=\"comment\">{env_name}</font>" if env_name else ""

        lines = [
            f"### CRM 接口自动化测试报告 {status_text}",
            f"> 执行时间：<font color=\"comment\">{timestamp}</font>{env_line}",
            f"> 总用例数：**{total}** | 通过：**{passed}** | 失败：**{failed}** | 错误：**{errors}** | 跳过：**{skipped}**",
            f"> 通过率：**{pass_rate}%** | 耗时：**{duration}s**",
        ]

        failed_cases = self.get_failed_details()
        if failed_cases:
            lines.append("")
            lines.append(f"> 失败用例明细（共 {len(failed_cases)} 条）：")
            for fc in failed_cases[:10]:
                err_short = (fc.get("error_msg") or "")[:60]
                lines.append(f"> - {fc['test_name']}：{err_short}")
            if len(failed_cases) > 10:
                lines.append(f"> - ...还有 {len(failed_cases) - 10} 条")

        if analysis_results:
            lines.append("")
            lines.append("> **失败诊断：**")
            for r in analysis_results[:5]:
                label = r.get("category_label", "")
                suggestion = r.get("suggestion", "")
                assertion = r.get("assertion_detail", "")
                history = r.get("history_status", "")
                risk = r.get("risk_level", "")
                risk_color = "warning" if risk == "high" else "comment"
                lines.append(f"> <font color=\"{risk_color}\">[{label}]</font> {r['test_name']}")
                if assertion:
                    lines.append(f">   断言: {assertion[:60]}")
                if suggestion:
                    lines.append(f">   建议: {suggestion[:60]}")
                if history:
                    lines.append(f">   历史: {history}")
            if len(analysis_results) > 5:
                lines.append(f"> ...还有 {len(analysis_results) - 5} 条")

        if self.wecom_mentioned_list:
            mention_line = " ".join(f"<@{uid}>" for uid in self.wecom_mentioned_list)
            lines.append("")
            lines.append(mention_line)

        return "\n".join(lines)

    def _build_wecom_template_card(self, summary, env_name=""):
        """
        构建 text_notice 模板卡片消息

        模板卡片比 markdown 展示效果更专业，支持:
        - 卡片来源样式
        - 关键数据高亮
        - 水平信息列表
        - 跳转链接

        :param summary: get_summary() 返回的字典
        :param env_name: 环境名称
        :return: template_card payload dict
        """
        passed = summary["passed"]
        failed = summary["failed"]
        pass_rate = summary["pass_rate"]
        duration = summary["total_duration"]
        timestamp = summary["timestamp"]
        total = summary["total"]
        skipped = summary["skipped"]
        errors = summary["errors"]

        if float(pass_rate) >= 100:
            main_desc = "所有用例全部通过"
        elif float(pass_rate) >= 80:
            main_desc = f"有 {failed} 条用例失败，请关注"
        else:
            main_desc = f"有 {failed} 条用例失败，通过率仅 {pass_rate}%，请立即处理"

        horizontal_list = [
            {"keyname": "通过", "value": str(passed)},
            {"keyname": "失败", "value": str(failed)},
            {"keyname": "跳过", "value": str(skipped)},
            {"keyname": "耗时", "value": f"{duration}s"},
        ]
        if env_name:
            horizontal_list.insert(0, {"keyname": "环境", "value": env_name})

        failed_cases = self.get_failed_details()
        quote_text = ""
        if failed_cases:
            lines = []
            for fc in failed_cases[:5]:
                err_short = (fc.get("error_msg") or "失败")[:40]
                lines.append(f"{fc['test_name']}：{err_short}")
            if len(failed_cases) > 5:
                lines.append(f"...还有 {len(failed_cases) - 5} 条失败")
            quote_text = "\n".join(lines)

        card = {
            "card_type": "text_notice",
            "source": {
                "desc": "CRM接口自动化",
                "desc_color": 0,
            },
            "main_title": {
                "title": f"测试报告 通过率 {pass_rate}%",
                "desc": main_desc,
            },
            "emphasis_content": {
                "title": f"{passed}/{total}",
                "desc": "通过/总数",
            },
            "sub_title_text": f"执行时间: {timestamp}",
            "horizontal_content_list": horizontal_list,
            "card_action": {
                "type": 1,
                "url": "https://work.weixin.qq.com",
            },
        }

        if quote_text:
            card["quote_area"] = {
                "type": 0,
                "title": "失败用例",
                "quote_text": quote_text,
            }

        return card

    def _send_wecom(self, url, payload):
        """
        发送企业微信消息的底层方法

        :param url: webhook 地址
        :param payload: 消息体 dict
        :return: dict {"success": bool, "response": dict}
        """
        try:
            resp = requests.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
            result = resp.json()
            success = result.get("errcode") == 0
            return {"success": success, "response": result}
        except requests.exceptions.RequestException as e:
            return {"success": False, "response": {"error": str(e)}}

    def notify_wecom_markdown(self, webhook_url=None, env_name="", analysis_results=None):
        """
        推送 markdown 格式测试报告

        适用场景: 通用消息，支持 <@userid> @群成员
        文档: https://developer.work.weixin.qq.com/document/path/91770#markdown类型

        :param webhook_url: 不传则使用初始化时配置的 wecom_webhook
        :param env_name: 环境名称
        :param analysis_results: 根因分析结果列表
        :return: dict {"success": bool, "response": dict}
        """
        url = webhook_url or self.wecom_webhook
        if not url:
            return {"success": False, "response": {"error": "未配置企业微信 Webhook 地址"}}

        summary = self.get_summary()
        content = self._build_wecom_markdown(summary, env_name, analysis_results)

        payload = {
            "msgtype": "markdown",
            "markdown": {
                "content": content,
            },
        }

        return self._send_wecom(url, payload)

    def notify_wecom_text(self, webhook_url=None, env_name=""):
        """
        推送 text 格式测试报告

        适用场景: 需要 @手机号 的场景
        text 类型独有 mentioned_mobile_list 字段，支持通过手机号@群成员
        文档: https://developer.work.weixin.qq.com/document/path/91770#文本类型

        :param webhook_url: 不传则使用初始化时配置的 wecom_webhook
        :param env_name: 环境名称
        :return: dict {"success": bool, "response": dict}
        """
        url = webhook_url or self.wecom_webhook
        if not url:
            return {"success": False, "response": {"error": "未配置企业微信 Webhook 地址"}}

        summary = self.get_summary()
        total = summary["total"]
        passed = summary["passed"]
        failed = summary["failed"]
        errors = summary["errors"]
        skipped = summary["skipped"]
        pass_rate = summary["pass_rate"]
        duration = summary["total_duration"]
        timestamp = summary["timestamp"]

        lines = [
            f"CRM 接口自动化测试报告",
            f"执行时间: {timestamp}",
        ]
        if env_name:
            lines.append(f"测试环境: {env_name}")
        lines.append(f"总数: {total} | 通过: {passed} | 失败: {failed} | 错误: {errors} | 跳过: {skipped}")
        lines.append(f"通过率: {pass_rate}% | 耗时: {duration}s")

        failed_cases = self.get_failed_details()
        if failed_cases:
            lines.append(f"\n失败用例 ({len(failed_cases)} 条):")
            for fc in failed_cases[:10]:
                err_short = (fc.get("error_msg") or "失败")[:50]
                lines.append(f"  - {fc['test_name']}: {err_short}")

        content = "\n".join(lines)

        text_payload = {
            "content": content,
        }

        if self.wecom_mentioned_list:
            text_payload["mentioned_list"] = self.wecom_mentioned_list
        if self.wecom_mentioned_mobile_list:
            text_payload["mentioned_mobile_list"] = self.wecom_mentioned_mobile_list

        payload = {
            "msgtype": "text",
            "text": text_payload,
        }

        return self._send_wecom(url, payload)

    def notify_wecom_template_card(self, webhook_url=None, env_name=""):
        """
        推送 text_notice 模板卡片测试报告

        适用场景: 展示效果最专业，有关键数据高亮、水平信息列表
        注意: 模板卡片不支持 @成员
        文档: https://developer.work.weixin.qq.com/document/path/91770#文本通知模版卡片

        :param webhook_url: 不传则使用初始化时配置的 wecom_webhook
        :param env_name: 环境名称
        :return: dict {"success": bool, "response": dict}
        """
        url = webhook_url or self.wecom_webhook
        if not url:
            return {"success": False, "response": {"error": "未配置企业微信 Webhook 地址"}}

        summary = self.get_summary()
        template_card = self._build_wecom_template_card(summary, env_name)

        payload = {
            "msgtype": "template_card",
            "template_card": template_card,
        }

        return self._send_wecom(url, payload)

    def notify_wecom(self, webhook_url=None, env_name="", msg_type="markdown", analysis_results=None):
        """
        推送测试结果到企业微信群机器人 (统一入口)

        支持三种消息类型:
        - markdown: 默认，支持 <@userid> @群成员，展示较丰富
        - text: 纯文本，支持 mentioned_mobile_list 通过手机号@群成员
        - template_card: 模板卡片，展示效果最专业，不支持@成员

        :param webhook_url: 不传则使用初始化时配置的 wecom_webhook
        :param env_name: 环境名称
        :param msg_type: 消息类型 "markdown" / "text" / "template_card"
        :param analysis_results: 根因分析结果列表 (markdown 类型会展示)
        :return: dict {"success": bool, "response": dict}
        """
        if msg_type == "text":
            return self.notify_wecom_text(webhook_url, env_name)
        elif msg_type == "template_card":
            return self.notify_wecom_template_card(webhook_url, env_name)
        else:
            return self.notify_wecom_markdown(webhook_url, env_name, analysis_results)
