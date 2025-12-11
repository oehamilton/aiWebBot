"""Prompt loading and management for system prompts used by the bot."""

import asyncio
from pathlib import Path
from typing import List, Optional, Tuple
from loguru import logger
import random


class PromptManager:
	"""Manages loading and refreshing a list of system prompts from a file."""

	def __init__(self, file_path: Path, reload_interval_seconds: int = 3600) -> None:
		self.file_path = file_path
		self.reload_interval_seconds = reload_interval_seconds
		self._prompts: List[str] = []
		self._reply_prompts: List[str] = []
		self._post_prompts: List[str] = []
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

	def get_random_prompt(self, fallback: str, prompt_type: str = "general") -> str:
		"""Get a random prompt from the loaded list, or fallback if empty.
		
		Args:
			fallback: Default prompt to use if no prompts are loaded
			prompt_type: Type of prompt to get - "reply", "post", or "general" (default)
		"""
		if prompt_type == "reply":
			if self._reply_prompts:
				return random.choice(self._reply_prompts)
		elif prompt_type == "post":
			if self._post_prompts:
				return random.choice(self._post_prompts)
		
		# Fallback to general prompts list or fallback
		if self._prompts:
			return random.choice(self._prompts)
		return fallback

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

			new_prompts, new_reply_prompts, new_post_prompts = self._read_prompts_from_file(self.file_path)
			async with self._lock:
				self._prompts = new_prompts
				self._reply_prompts = new_reply_prompts
				self._post_prompts = new_post_prompts
				self._last_mtime = current_mtime

			total = len(new_prompts) + len(new_reply_prompts) + len(new_post_prompts)
			logger.info(f"Loaded {total} system prompt(s) from {self.file_path} ({len(new_reply_prompts)} reply, {len(new_post_prompts)} post, {len(new_prompts)} general)")
		except Exception as e:
			logger.warning(f"Failed to load system prompts: {e}")

	def _read_prompts_from_file(self, path: Path) -> Tuple[List[str], List[str], List[str]]:
		"""Read and parse prompts from a text file.
		
		Supports section-based prompts:
		- Lines starting with '# Reply prompt' start the reply prompts section
		- Lines starting with '# Post prompt' start the post prompts section
		- Other lines starting with '#' are ignored
		- Empty lines separate prompts
		
		Returns:
			Tuple of (general_prompts, reply_prompts, post_prompts)
		"""
		with path.open("r", encoding="utf-8") as f:
			content = f.read()

		general_prompts: List[str] = []
		reply_prompts: List[str] = []
		post_prompts: List[str] = []
		
		current_section = "general"  # general, reply, or post
		current_prompt = []
		
		lines = content.split('\n')
		for line in lines:
			line_stripped = line.strip()
			
			# Check for section markers
			if line_stripped.lower().startswith("# reply prompt"):
				# Save current prompt if any
				if current_prompt:
					prompt_text = '\n'.join(current_prompt).strip()
					if prompt_text:
						if current_section == "reply":
							reply_prompts.append(prompt_text)
						elif current_section == "post":
							post_prompts.append(prompt_text)
						else:
							general_prompts.append(prompt_text)
					current_prompt = []
				current_section = "reply"
				continue
			elif line_stripped.lower().startswith("# post prompt"):
				# Save current prompt if any
				if current_prompt:
					prompt_text = '\n'.join(current_prompt).strip()
					if prompt_text:
						if current_section == "reply":
							reply_prompts.append(prompt_text)
						elif current_section == "post":
							post_prompts.append(prompt_text)
						else:
							general_prompts.append(prompt_text)
					current_prompt = []
				current_section = "post"
				continue
			elif line_stripped.startswith("#"):
				# Comment line, ignore
				continue
			elif not line_stripped:
				# Empty line - end of current prompt if we have content
				if current_prompt:
					prompt_text = '\n'.join(current_prompt).strip()
					if prompt_text:
						if current_section == "reply":
							reply_prompts.append(prompt_text)
						elif current_section == "post":
							post_prompts.append(prompt_text)
						else:
							general_prompts.append(prompt_text)
					current_prompt = []
			else:
				# Content line
				current_prompt.append(line)
		
		# Don't forget the last prompt
		if current_prompt:
			prompt_text = '\n'.join(current_prompt).strip()
			if prompt_text:
				if current_section == "reply":
					reply_prompts.append(prompt_text)
				elif current_section == "post":
					post_prompts.append(prompt_text)
				else:
					general_prompts.append(prompt_text)
		
		return general_prompts, reply_prompts, post_prompts


