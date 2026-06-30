import json
import os
from datetime import datetime

from common.contants import report_dir
from mcp_servers.report_server import ReportMCPClient
from ai.root_cause import RootCauseAnalyzer


class FeedbackReporter:
    """
    持续反馈层
    - 生成 HTML 摘要报告
    - AI 分析报告 (失败根因分析)
    - 历史趋势分析
    """

    def __init__(self, report_path=None):
        self.report_dir = report_path or report_dir
        self.report_client = ReportMCPClient(report_dir=self.report_dir)
        self.root_analyzer = RootCauseAnalyzer()

    def generate_ai_report(self, test_results):
        """
        生成 AI 分析报告
        :param test_results: 测试结果列表
        :return: 报告内容
        """
        summary = {
            "total": len(test_results),
            "passed": sum(1 for r in test_results if r.get("status") == "pass"),
            "failed": sum(1 for r in test_results if r.get("status") == "fail"),
            "errors": sum(1 for r in test_results if r.get("status") == "error"),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        summary["pass_rate"] = (
            f"{summary['passed'] / summary['total'] * 100:.2f}%"
            if summary["total"] > 0 else "0%"
        )

        failed_records = [r for r in test_results if r.get("status") in ("fail", "error")]
        root_cause_results = self.root_analyzer.batch_analyze(failed_records)

        report = {
            "summary": summary,
            "root_cause_analysis": root_cause_results,
            "regression_suggestion": self.root_analyzer.generate_regression_suggestion(root_cause_results),
        }

        return report

    def save_ai_report(self, report_data, filename=None):
        if filename is None:
            filename = f"{datetime.now().strftime('%Y-%m-%d_%H_%M_%S')}_ai_report.json"
        filepath = os.path.join(self.report_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        return filepath

    def get_trend(self, limit=10):
        history = self.report_client.get_history(limit)
        if not history:
            return "暂无历史数据"

        lines = ["历史趋势:", "=" * 50]
        for h in history:
            lines.append(
                f"  {h.get('begin_time', 'N/A')} | "
                f"通过率: {h.get('pass_rate', 'N/A')} | "
                f"总数: {h.get('all', 0)} | "
                f"失败: {h.get('fail', 0)} | "
                f"耗时: {h.get('runtime', 'N/A')}"
            )
        return "\n".join(lines)
