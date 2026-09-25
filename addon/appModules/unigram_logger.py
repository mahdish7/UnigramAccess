# -*- coding:utf-8 -*-
import os
import logging
from logHandler import log as nvda_log
from .cnf import conf

addon_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
log_file_path = os.path.join(addon_dir, "unigram_access.log")

class UnigramLogger:
	def __init__(self):
		self.file_logger = logging.getLogger("UnigramAccess")
		self.file_logger.propagate = False # Prevent bubbling up to root logger
		self.file_handler = None
		self.update_log_level()

	def update_log_level(self):
		level_str = conf.get("custom_log_level")
		if level_str == "disabled":
			self.disable_file_logging()
			return

		levels = {
			"debug": logging.DEBUG,
			"info": logging.INFO,
			"warning": logging.WARNING,
			"error": logging.ERROR,
		}
		
		# Fallback to DEBUG if unknown
		lvl = levels.get(level_str, logging.DEBUG)
		self.file_logger.setLevel(lvl)
		self.enable_file_logging()

	def enable_file_logging(self):
		if not self.file_handler:
			self.file_logger.handlers.clear()
			self.file_handler = logging.FileHandler(log_file_path, encoding="utf-8")
			formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
			self.file_handler.setFormatter(formatter)
			self.file_logger.addHandler(self.file_handler)

	def disable_file_logging(self):
		if self.file_handler:
			self.file_logger.removeHandler(self.file_handler)
			self.file_handler.close()
			self.file_handler = None

	def _log(self, level_name, msg, exc_info=False):
		# 1. Log to NVDA standard log
		try:
			if level_name == 'debug':
				nvda_log.debug(msg, exc_info=exc_info)
			elif level_name == 'debugWarning':
				if hasattr(nvda_log, 'debugWarning'):
					nvda_log.debugWarning(msg, exc_info=exc_info)
				else:
					nvda_log.warning(msg, exc_info=exc_info)
			elif level_name == 'debugException':
				if hasattr(nvda_log, 'debugException'):
					nvda_log.debugException(msg, exc_info=exc_info)
				else:
					nvda_log.debug(msg, exc_info=True)
			elif level_name == 'info':
				nvda_log.info(msg, exc_info=exc_info)
			elif level_name == 'warning':
				nvda_log.warning(msg, exc_info=exc_info)
			elif level_name == 'error':
				nvda_log.error(msg, exc_info=exc_info)
			elif level_name == 'critical':
				nvda_log.critical(msg, exc_info=exc_info)
		except Exception:
			pass

		# 2. Log to dedicated file if enabled
		if self.file_handler:
			try:
				if level_name in ('debug', 'debugWarning', 'debugException'):
					self.file_logger.debug(msg, exc_info=exc_info)
				elif level_name == 'info':
					self.file_logger.info(msg, exc_info=exc_info)
				elif level_name == 'warning':
					self.file_logger.warning(msg, exc_info=exc_info)
				elif level_name == 'error':
					self.file_logger.error(msg, exc_info=exc_info)
				elif level_name == 'critical':
					self.file_logger.critical(msg, exc_info=exc_info)
			except Exception:
				pass

	def debug(self, msg, exc_info=False): self._log('debug', msg, exc_info)
	def debugWarning(self, msg, exc_info=False): self._log('debugWarning', msg, exc_info)
	def debugException(self, msg, exc_info=True): self._log('debugException', msg, exc_info)
	def info(self, msg, exc_info=False): self._log('info', msg, exc_info)
	def warning(self, msg, exc_info=False): self._log('warning', msg, exc_info)
	def error(self, msg, exc_info=False): self._log('error', msg, exc_info)
	def critical(self, msg, exc_info=False): self._log('critical', msg, exc_info)
	
	def open_log_file(self):
		try:
			if not os.path.exists(log_file_path):
				open(log_file_path, 'a').close()
			os.startfile(log_file_path)
		except Exception as e:
			nvda_log.error(f"Error opening log file: {e}")

	def clear_log_file(self):
		# To avoid PermissionError, temporarily detach and close the handler
		was_enabled = self.file_handler is not None
		if was_enabled:
			self.disable_file_logging()
			
		try:
			with open(log_file_path, 'w', encoding="utf-8") as f:
				f.write("")
		except Exception as e:
			nvda_log.error(f"Error clearing log file: {e}")
			
		if was_enabled:
			self.enable_file_logging()

ulog = UnigramLogger()
