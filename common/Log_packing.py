import logging
import logging.handlers
import time
import os

from .contants import log_dir
from .get_config import GetConfig

_config = GetConfig()


class Log:
    """
    日志模块 — 按日滚动的日志记录器
    
    核心特性:
    - 按日期生成日志文件 (如 2026年05月15日.log)
    - 支持控制台 + 文件双输出
    - 文件大小限制 (10MB)，保留最近 20 个备份
    - 日志级别可配置 (DEBUG/INFO/WARNING/ERROR)
    
    使用方式:
        log = Log()
        log.info("正常日志")
        log.warning("警告信息")
        log.error("错误信息")
        log.debug("调试信息")
    """
    def __init__(self):
        self.logname = os.path.join(
            log_dir,
            '%s.log' % time.strftime('%Y{n}_%m{y}_%d{r}').format(n='年', y='月', r='日')
        )
        self.logger = logging.getLogger()
        self.logger.setLevel(_config.get_value('level', 'logger').upper())
        self.formatter = logging.Formatter(_config.get_value('format', 'formatter'))

    def _console(self, level, message):
        fh = logging.handlers.RotatingFileHandler(
            self.logname, maxBytes=10 * 1024 * 1024, encoding='utf-8', backupCount=20
        )
        fh.setLevel(_config.get_value('level', 'fh').upper())
        fh.setFormatter(self.formatter)
        self.logger.addHandler(fh)

        ch = logging.StreamHandler()
        ch.setLevel(_config.get_value('level', 'ch').upper())
        ch.setFormatter(self.formatter)
        self.logger.addHandler(ch)

        if level == 'info':
            self.logger.info(message)
        elif level == 'warning':
            self.logger.warning(message)
        elif level == 'debug':
            self.logger.debug(message)
        elif level == 'error':
            self.logger.error(message)

        self.logger.removeHandler(ch)
        self.logger.removeHandler(fh)
        fh.close()

    def debug(self, message):
        self._console('debug', message)

    def info(self, message):
        self._console('info', message)

    def warning(self, message):
        self._console('warning', message)

    def error(self, message):
        self._console('error', message)


if __name__ == '__main__':
    log = Log()
    log.info('开始测试')
    log.warning('退车，请注意')
    log.info('----test over------')
