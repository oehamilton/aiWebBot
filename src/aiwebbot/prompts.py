"""Prompt loading and management for system prompts used by the bot."""

import asyncio
from pathlib import Path
from typing import List, Optional
from loguru import logger
import random


class PromptManager:
	"""Manages loading and refreshing a list of system prompts from a file."""

	def __init__(self, file_path: Path, reload_interval_seconds: int = 3600) -> None:
		self.file_path = file_path
		self.reload_interval_seconds = reload_interval_seconds
		self._prompts: List[str] = []
		self._last_mtime: Optional[float] = None
		self._task: Optional[asyncio.Task] = None
		self._lock = asyncio.Lock()

	async def start(self) -> None:
		"""Load prompts initially and start background reload loop."""
		await self._reload_if_changed()
		self._task = asyncio.create_task(self._reload_loop(), name="PromptManagerReloadLoop")

	async def stop(self) -> None:
		"""Stop the background reload loop."""
		if self._task:
			self._task.cancel()
			try:
				await self._task
			except asyncio.CancelledError:
				pass
			self._task = None

	def get_random_prompt(self, fallback: str) -> str:
		"""Get a random prompt from the loaded list, or fallback if empty."""
		if not self._prompts:
			return fallback
		return random.choice(self._prompts)

	async def _reload_loop(self) -> None:
		"""Periodically check for changes and reload prompts."""
		while True:
			try:
				await self._reload_if_changed()
			except Exception as e:
				logger.warning(f"Prompt reload failed: {e}")
			await asyncio.sleep(self.reload_interval_seconds)

	async def _reload_if_changed(self) -> None:
		"""Reload prompts if the file changed since last load, or if not loaded."""
		try:
			if not self.file_path.exists():
				logger.info(f"System prompts file not found at {self.file_path}. Using fallback prompt.")
				async with self._lock:
					self._prompts = []
					self._last_mtime = None
				return

			current_mtime = self.file_path.stat().st_mtime
			if self._last_mtime is not None and current_mtime == self._last_mtime:
				return

			new_prompts = self._read_prompts_from_file(self.file_path)
			async with self._lock:
				self._prompts = new_prompts
				self._last_mtime = current_mtime

			logger.info(f"Loaded {len(new_prompts)} system prompt(s) from {self.file_path}")
		except Exception as e:
			logger.warning(f"Failed to load system prompts: {e}")

	def _read_prompts_from_file(self, path: Path) -> List[str]:
		"""Read and parse prompts from a text file (one prompt per line). Lines starting with '#' are ignored."""
		with path.open("r", encoding="utf-8") as f:
			lines = f.readlines()

		prompts: List[str] = []
		for line in lines:
			line = line.strip()
			if not line:
				continue
			if line.startswith("#"):
				continue
			prompts.append(line)
		return prompts


