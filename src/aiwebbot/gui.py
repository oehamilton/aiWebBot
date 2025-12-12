"""GUI interface for AI Web Bot monitoring and control."""

import asyncio
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, scrolledtext, ttk
from typing import Optional
import time

from loguru import logger


class BotGUI:
    """GUI interface for monitoring and controlling the AI Web Bot."""

    def __init__(self, bot, config_path=None):
        """Initialize the GUI with a reference to the bot."""
        self.bot = bot
        self.config_path = config_path  # Store config file path for saving
        self.root = tk.Tk()
        self.root.title("AI Web Bot - Control Panel")
        self.root.geometry("900x600")  # Smaller default size
        self.root.minsize(600, 400)  # Minimum window size
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Set up GUI update callback
        self.bot.gui_callback = self.update_display
        
        # Create scrollable frame
        self.create_scrollable_frame()
        
        # Create main interface
        self.create_widgets()
        
        # Start update loop
        self.update_display()
        self.root.after(1000, self.update_loop)  # Update every second
    
    def create_scrollable_frame(self):
        """Create a scrollable frame using Canvas and Scrollbar."""
        # Create main container
        container = ttk.Frame(self.root)
        container.pack(fill=tk.BOTH, expand=True)
        
        # Create canvas with scrollbar
        self.canvas = tk.Canvas(container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        # Configure scrollable frame
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        # Create window in canvas
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        
        # Configure scrollbar
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack canvas and scrollbar
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind mousewheel to canvas
        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
        # Bind mousewheel for Windows and Linux
        self.canvas.bind_all("<MouseWheel>", _on_mousewheel)
        # Bind mousewheel for Mac (Button-4 and Button-5)
        self.canvas.bind_all("<Button-4>", lambda e: self.canvas.yview_scroll(-1, "units"))
        self.canvas.bind_all("<Button-5>", lambda e: self.canvas.yview_scroll(1, "units"))
        
        # Update canvas width when window is resized
        def configure_canvas_width(event):
            canvas_width = event.width
            self.canvas.itemconfig(self.canvas_window, width=canvas_width)
        
        self.canvas.bind('<Configure>', configure_canvas_width)
        
    def create_widgets(self):
        """Create and layout all GUI widgets."""
        # Main container with padding - now uses scrollable_frame instead of root
        main_frame = ttk.Frame(self.scrollable_frame, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.scrollable_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        
        # Title and Bot Status
        title_frame = ttk.Frame(main_frame)
        title_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        title_frame.columnconfigure(0, weight=1)
        
        title_label = ttk.Label(title_frame, text="AI Web Bot Control Panel", font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, sticky=tk.W)
        
        # Bot status indicator
        self.bot_status_label = ttk.Label(title_frame, text="Status: Running", font=("Arial", 10, "bold"), foreground="green")
        self.bot_status_label.grid(row=0, column=1, sticky=tk.E, padx=(20, 0))
        
        # Stop/Start button
        self.stop_button = ttk.Button(title_frame, text="Stop Bot", command=self.stop_bot)
        self.stop_button.grid(row=0, column=2, sticky=tk.E, padx=(10, 0))
        
        # Status section
        status_frame = ttk.LabelFrame(main_frame, text="Status", padding="10")
        status_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        status_frame.columnconfigure(1, weight=1)
        
        # Last new post
        ttk.Label(status_frame, text="Last New Post:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky=tk.W, pady=2)
        self.last_post_label = ttk.Label(status_frame, text="None", wraplength=600, foreground="gray")
        self.last_post_label.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=2)
        
        ttk.Label(status_frame, text="Timestamp:", font=("Arial", 9)).grid(row=1, column=0, sticky=tk.W, pady=2)
        self.last_post_time_label = ttk.Label(status_frame, text="N/A", foreground="gray")
        self.last_post_time_label.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=2)
        
        # Last reply
        ttk.Label(status_frame, text="Last Reply:", font=("Arial", 10, "bold")).grid(row=2, column=0, sticky=tk.W, pady=2)
        self.last_reply_label = ttk.Label(status_frame, text="None", wraplength=600, foreground="gray")
        self.last_reply_label.grid(row=2, column=1, sticky=tk.W, padx=(10, 0), pady=2)
        
        ttk.Label(status_frame, text="Timestamp:", font=("Arial", 9)).grid(row=3, column=0, sticky=tk.W, pady=2)
        self.last_reply_time_label = ttk.Label(status_frame, text="N/A", foreground="gray")
        self.last_reply_time_label.grid(row=3, column=1, sticky=tk.W, padx=(10, 0), pady=2)
        
        # Cooldown timer
        cooldown_frame = ttk.LabelFrame(main_frame, text="Cooldown Timer", padding="10")
        cooldown_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=5)
        cooldown_frame.columnconfigure(1, weight=1)
        
        self.cooldown_label = ttk.Label(cooldown_frame, text="Ready to post/reply", font=("Arial", 12, "bold"), foreground="green")
        self.cooldown_label.grid(row=0, column=0, columnspan=2, pady=5)
        
        self.cooldown_progress = ttk.Progressbar(cooldown_frame, mode='determinate', length=400)
        self.cooldown_progress.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # Statistics section
        stats_frame = ttk.LabelFrame(main_frame, text="Statistics", padding="10")
        stats_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=5)
        stats_frame.columnconfigure(1, weight=1)
        stats_frame.columnconfigure(3, weight=1)
        
        ttk.Label(stats_frame, text="Total New Posts:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky=tk.W, pady=2)
        self.total_posts_label = ttk.Label(stats_frame, text="0", font=("Arial", 12))
        self.total_posts_label.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=2)
        # Actual ratio display to the right of count
        self.actual_ratio_label = ttk.Label(stats_frame, text="(N/A)", font=("Arial", 9), foreground="gray")
        self.actual_ratio_label.grid(row=0, column=2, sticky=tk.W, padx=(20, 0), pady=2)
        
        ttk.Label(stats_frame, text="Total Replies:", font=("Arial", 10, "bold")).grid(row=1, column=0, sticky=tk.W, pady=2)
        self.total_replies_label = ttk.Label(stats_frame, text="0", font=("Arial", 12))
        self.total_replies_label.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=2)
        
        # Ratio comparison indicator
        ttk.Label(stats_frame, text="Ratio Status:", font=("Arial", 10, "bold")).grid(row=2, column=0, sticky=tk.W, pady=2)
        self.ratio_status_label = ttk.Label(stats_frame, text="N/A", font=("Arial", 10))
        self.ratio_status_label.grid(row=2, column=1, sticky=tk.W, padx=(10, 0), pady=2)
        
        # System Prompts section
        prompts_frame = ttk.LabelFrame(main_frame, text="System Prompts", padding="10")
        prompts_frame.grid(row=4, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        prompts_frame.columnconfigure(0, weight=1)
        prompts_frame.rowconfigure(1, weight=0)  # Don't expand reply prompt row
        prompts_frame.rowconfigure(3, weight=0)  # Don't expand post prompt row - use fixed height
        main_frame.rowconfigure(4, weight=0)  # Don't let prompts frame expand, use fixed size
        
        # Reply prompt
        ttk.Label(prompts_frame, text="Reply Prompt:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky=tk.W, pady=2)
        self.reply_prompt_text = scrolledtext.ScrolledText(prompts_frame, height=3, wrap=tk.WORD, width=80)
        self.reply_prompt_text.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        
        # Post prompt
        ttk.Label(prompts_frame, text="New Post Prompt:", font=("Arial", 10, "bold")).grid(row=2, column=0, sticky=tk.W, pady=2)
        self.post_prompt_text = scrolledtext.ScrolledText(prompts_frame, height=3, wrap=tk.WORD, width=80)
        self.post_prompt_text.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=5)
        
        # Update prompts button - make sure it's visible with proper padding
        update_prompts_btn = ttk.Button(prompts_frame, text="Update Prompts", command=self.update_prompts)
        update_prompts_btn.grid(row=4, column=0, pady=(15, 5), sticky=tk.W)
        
        # Cooldown settings section
        cooldown_settings_frame = ttk.LabelFrame(main_frame, text="Cooldown Settings", padding="10")
        cooldown_settings_frame.grid(row=5, column=0, sticky=(tk.W, tk.E), pady=5)
        cooldown_settings_frame.columnconfigure(1, weight=1)
        cooldown_settings_frame.columnconfigure(3, weight=1)
        
        ttk.Label(cooldown_settings_frame, text="Min Cooldown (seconds):").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.min_cooldown_var = tk.StringVar(value=str(self.bot.config.timing.min_post_reply_cooldown_seconds))
        min_cooldown_entry = ttk.Entry(cooldown_settings_frame, textvariable=self.min_cooldown_var, width=15)
        min_cooldown_entry.grid(row=0, column=1, sticky=tk.W, padx=5)
        
        ttk.Label(cooldown_settings_frame, text="Max Cooldown (seconds):").grid(row=0, column=2, sticky=tk.W, padx=5)
        self.max_cooldown_var = tk.StringVar(value=str(self.bot.config.timing.max_post_reply_cooldown_seconds))
        max_cooldown_entry = ttk.Entry(cooldown_settings_frame, textvariable=self.max_cooldown_var, width=15)
        max_cooldown_entry.grid(row=0, column=3, sticky=tk.W, padx=5)
        
        update_cooldown_btn = ttk.Button(cooldown_settings_frame, text="Update Cooldown Range", command=self.update_cooldown)
        update_cooldown_btn.grid(row=0, column=4, padx=10)
        
        # Post to Reply Ratio section
        ratio_frame = ttk.LabelFrame(main_frame, text="Post to Reply Ratio", padding="10")
        ratio_frame.grid(row=6, column=0, sticky=(tk.W, tk.E), pady=5)
        ratio_frame.columnconfigure(1, weight=1)
        
        ttk.Label(ratio_frame, text="New Post Probability (0.0 - 1.0):").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.post_ratio_var = tk.StringVar(value=str(self.bot.post_to_reply_ratio))
        self.post_ratio_entry = ttk.Entry(ratio_frame, textvariable=self.post_ratio_var, width=15)
        self.post_ratio_entry.grid(row=0, column=1, sticky=tk.W, padx=5)
        
        # Display current ratio as percentage
        self.ratio_display_label = ttk.Label(ratio_frame, text="", font=("Arial", 9))
        self.ratio_display_label.grid(row=0, column=2, sticky=tk.W, padx=10)
        
        update_ratio_btn = ttk.Button(ratio_frame, text="Update Ratio", command=self.update_post_ratio)
        update_ratio_btn.grid(row=0, column=3, padx=10)
        
        # AI Model Settings section
        ai_settings_frame = ttk.LabelFrame(main_frame, text="AI Model Settings", padding="10")
        ai_settings_frame.grid(row=7, column=0, sticky=(tk.W, tk.E), pady=5)
        ai_settings_frame.columnconfigure(1, weight=1)
        
        # Model selection dropdown
        ttk.Label(ai_settings_frame, text="AI Model:").grid(row=0, column=0, sticky=tk.W, padx=5)
        # Get model from bot or config, with fallback
        current_model = getattr(self.bot, 'ai_model', None) or getattr(self.bot.config, 'ai_model', 'grok-4-1-fast-reasoning')
        self.model_var = tk.StringVar(value=current_model)
        model_options = [
            "grok-4-1-fast-reasoning",
            "grok-4-1-fast-non-reasoning",
            "grok-code-fast-1",
            "grok-4-fast-reasoning",
            "grok-4-fast-non-reasoning",
            "grok-4-0709",
            "grok-3-mini",
            "grok-3",
            "grok-2-vision-1212"
        ]
        self.model_dropdown = ttk.Combobox(ai_settings_frame, textvariable=self.model_var, values=model_options, state="readonly", width=30)
        self.model_dropdown.grid(row=0, column=1, sticky=tk.W, padx=5)
        
        # Temperature slider
        ttk.Label(ai_settings_frame, text="Temperature:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        temp_frame = ttk.Frame(ai_settings_frame)
        temp_frame.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        temp_frame.columnconfigure(1, weight=1)
        
        # Get temperature from bot or config, with fallback
        current_temp = getattr(self.bot, 'temperature', None)
        if current_temp is None:
            current_temp = getattr(self.bot.config, 'temperature', 0.80)
        self.temperature_var = tk.DoubleVar(value=current_temp)
        self.temp_label = ttk.Label(temp_frame, text="Creative", font=("Arial", 9))
        self.temp_label.grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        
        self.temperature_scale = ttk.Scale(temp_frame, from_=0.0, to=2.0, variable=self.temperature_var, 
                                          orient=tk.HORIZONTAL, length=300, command=self.update_temp_label)
        self.temperature_scale.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        
        # Track when user is interacting with the slider to prevent auto-updates
        self._temp_slider_active = False
        self._temp_slider_last_release_time = 0
        
        def on_slider_press(e):
            self._temp_slider_active = True
            self._temp_slider_last_release_time = 0
        
        def on_slider_release(e):
            # Don't immediately allow updates - give user time to click save button
            self._temp_slider_active = False
            self._temp_slider_last_release_time = time.time()
        
        def on_slider_motion(e):
            self._temp_slider_active = True
            self._temp_slider_last_release_time = 0
        
        self.temperature_scale.bind("<ButtonPress-1>", on_slider_press)
        self.temperature_scale.bind("<ButtonRelease-1>", on_slider_release)
        self.temperature_scale.bind("<B1-Motion>", on_slider_motion)
        
        self.temp_value_label = ttk.Label(temp_frame, text="0.80", font=("Arial", 9))
        self.temp_value_label.grid(row=0, column=2, sticky=tk.W, padx=(5, 0))
        
        strict_label = ttk.Label(temp_frame, text="Strict", font=("Arial", 8), foreground="gray")
        strict_label.grid(row=1, column=1, sticky=tk.W, padx=5)
        
        creative_label = ttk.Label(temp_frame, text="Creative", font=("Arial", 8), foreground="gray")
        creative_label.grid(row=1, column=1, sticky=tk.E, padx=5)
        
        update_ai_btn = ttk.Button(ai_settings_frame, text="Update AI Settings", command=self.update_ai_settings)
        update_ai_btn.grid(row=2, column=0, columnspan=2, pady=(10, 0))
        
        # Log Viewer section
        log_frame = ttk.LabelFrame(main_frame, text="Logs", padding="10")
        log_frame.grid(row=8, column=0, sticky=(tk.W, tk.E), pady=5)
        
        view_logs_btn = ttk.Button(log_frame, text="View Log Files", command=self.view_logs)
        view_logs_btn.grid(row=0, column=0, sticky=tk.W)
        
        self.log_path_label = ttk.Label(log_frame, text="", font=("Arial", 8), foreground="gray")
        self.log_path_label.grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        
    def update_temp_label(self, value=None):
        """Update temperature label based on slider value."""
        temp = self.temperature_var.get()
        self.temp_value_label.config(text=f"{temp:.2f}")
        
        # Update descriptive label
        if temp < 0.5:
            self.temp_label.config(text="Very Strict", foreground="blue")
        elif temp < 1.0:
            self.temp_label.config(text="Strict", foreground="green")
        elif temp < 1.5:
            self.temp_label.config(text="Balanced", foreground="orange")
        else:
            self.temp_label.config(text="Creative", foreground="red")
        
    def update_display(self):
        """Update all display elements with current bot state."""
        # Update last new post
        if self.bot.last_new_post_text:
            self.last_post_label.config(text=self.bot.last_new_post_text[:100] + ("..." if len(self.bot.last_new_post_text) > 100 else ""), foreground="black")
        else:
            self.last_post_label.config(text="None", foreground="gray")
            
        if self.bot.last_new_post_timestamp:
            self.last_post_time_label.config(text=self.bot.last_new_post_timestamp, foreground="black")
        else:
            self.last_post_time_label.config(text="N/A", foreground="gray")
        
        # Update last reply
        if self.bot.last_reply_text:
            self.last_reply_label.config(text=self.bot.last_reply_text[:100] + ("..." if len(self.bot.last_reply_text) > 100 else ""), foreground="black")
        else:
            self.last_reply_label.config(text="None", foreground="gray")
            
        if self.bot.last_reply_timestamp:
            self.last_reply_time_label.config(text=self.bot.last_reply_timestamp, foreground="black")
        else:
            self.last_reply_time_label.config(text="N/A", foreground="gray")
        
        # Update statistics
        self.total_posts_label.config(text=str(self.bot.total_new_posts))
        self.total_replies_label.config(text=str(self.bot.total_replies))
        
        # Calculate and display actual ratio (to the right of counts)
        total_actions = self.bot.total_new_posts + self.bot.total_replies
        if total_actions > 0:
            actual_post_ratio = self.bot.total_new_posts / total_actions
            actual_reply_ratio = self.bot.total_replies / total_actions
            self.actual_ratio_label.config(
                text=f"({actual_post_ratio * 100:.1f}% posts, {actual_reply_ratio * 100:.1f}% replies)",
                foreground="black"
            )
            
            # Compare actual ratio to desired ratio and show status
            if hasattr(self.bot, 'post_to_reply_ratio'):
                desired_ratio = self.bot.post_to_reply_ratio
                ratio_diff = actual_post_ratio - desired_ratio
                
                # Determine what action should be taken
                if abs(ratio_diff) < 0.05:  # Within 5% tolerance
                    self.ratio_status_label.config(
                        text="Balanced (within tolerance)",
                        foreground="green"
                    )
                elif ratio_diff > 0.05:  # Too many posts, need more replies
                    self.ratio_status_label.config(
                        text=f"Need more replies (diff: {ratio_diff * 100:+.1f}%)",
                        foreground="orange"
                    )
                else:  # Too many replies, need more posts
                    self.ratio_status_label.config(
                        text=f"Need more posts (diff: {ratio_diff * 100:+.1f}%)",
                        foreground="orange"
                    )
            else:
                self.ratio_status_label.config(text="N/A", foreground="gray")
        else:
            self.actual_ratio_label.config(text="(No actions yet)", foreground="gray")
            self.ratio_status_label.config(text="N/A", foreground="gray")
        
        # Update cooldown timer
        can_post, seconds_remaining = self.bot.can_post_or_reply()
        if can_post:
            self.cooldown_label.config(text="Ready to post/reply", foreground="green")
            self.cooldown_progress['value'] = 100
        else:
            minutes = int(seconds_remaining // 60)
            seconds = int(seconds_remaining % 60)
            self.cooldown_label.config(text=f"Cooldown: {minutes}m {seconds}s remaining", foreground="orange")
            if self.bot.current_cooldown_duration:
                progress = ((self.bot.current_cooldown_duration - seconds_remaining) / self.bot.current_cooldown_duration) * 100
                self.cooldown_progress['value'] = progress
            else:
                self.cooldown_progress['value'] = 0
        
        # Update prompts display (read from file)
        self.update_prompts_display()
        
        # Update bot status
        if hasattr(self.bot, 'running'):
            if self.bot.running:
                self.bot_status_label.config(text="Status: Running", foreground="green")
                self.stop_button.config(text="Stop Bot", state="normal")
            else:
                self.bot_status_label.config(text="Status: Stopped", foreground="red")
                self.stop_button.config(text="Bot Stopped", state="disabled")
        
        # Update post-to-reply ratio display
        if hasattr(self.bot, 'post_to_reply_ratio'):
            ratio = self.bot.post_to_reply_ratio
            post_percent = ratio * 100
            reply_percent = (1.0 - ratio) * 100
            self.ratio_display_label.config(text=f"Current: {post_percent:.1f}% new posts, {reply_percent:.1f}% replies")
            # Only update the entry field if it doesn't have focus (user isn't editing it)
            if hasattr(self, 'post_ratio_entry'):
                try:
                    if self.post_ratio_entry.focus_get() != self.post_ratio_entry:
                        self.post_ratio_var.set(str(ratio))
                except (KeyError, AttributeError):
                    # Focus check failed (e.g., dropdown menu open), don't update
                    pass
        
        # Update AI model and temperature display
        if hasattr(self.bot, 'ai_model'):
            if hasattr(self, 'model_dropdown'):
                # Check focus safely - Combobox dropdown can cause KeyError
                try:
                    focused = self.root.focus_get()
                    if focused != self.model_dropdown:
                        self.model_var.set(self.bot.ai_model)
                except (KeyError, AttributeError):
                    # Dropdown menu is open or focus check failed, don't update
                    pass
        
        if hasattr(self.bot, 'temperature'):
            # Only update temperature slider if user is not currently interacting with it
            if not hasattr(self, 'temperature_scale'):
                return
            
            # Check if slider is being actively used (tracked via event bindings)
            if not hasattr(self, '_temp_slider_active'):
                self._temp_slider_active = False
            if not hasattr(self, '_temp_slider_last_release_time'):
                self._temp_slider_last_release_time = 0
            
            # Only update if slider is not being actively dragged/adjusted
            # AND enough time has passed since last release (give user time to click save)
            current_time = time.time()
            time_since_release = current_time - self._temp_slider_last_release_time if self._temp_slider_last_release_time > 0 else 999
            
            if not self._temp_slider_active and time_since_release > 10.0:  # 10 second grace period to allow time to click save
                # Also check focus as a backup (safely handle focus_get errors)
                try:
                    focused = self.root.focus_get()
                    if focused != self.temperature_scale:
                        self.temperature_var.set(self.bot.temperature)
                        self.update_temp_label()
                except (KeyError, AttributeError):
                    # Focus check failed (e.g., dropdown menu open), don't update
                    pass
        
        # Update log path display
        log_path = self.bot.config.logging.file_path if self.bot.config.logging.file_path else None
        if log_path and Path(log_path).exists():
            self.log_path_label.config(text=f"Log file: {log_path}", foreground="black")
        else:
            self.log_path_label.config(text="Log file: Not configured or not found", foreground="gray")
        
    def update_prompts_display(self):
        """Update the prompts display from the prompts file."""
        try:
            # Read prompts from the prompt manager if available
            if hasattr(self.bot, 'prompt_manager'):
                # Get the first prompt from each list, or use fallback
                from .bot import SYSTEM_PROMPT, POST_SYSTEM_PROMPT
                
                reply_prompts = self.bot.prompt_manager._reply_prompts
                post_prompts = self.bot.prompt_manager._post_prompts
                
                reply_prompt = reply_prompts[0] if reply_prompts else SYSTEM_PROMPT
                post_prompt = post_prompts[0] if post_prompts else POST_SYSTEM_PROMPT
            else:
                # Fallback: read from file directly
                prompts_file = self.bot.config.system_prompts_path
                if not prompts_file:
                    prompts_file = Path("config/system_prompts.txt")
                
                reply_prompt = ""
                post_prompt = ""
                
                if prompts_file.exists():
                    with open(prompts_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Parse using the same logic as PromptManager
                    current_section = "general"
                    current_prompt = []
                    reply_prompts = []
                    post_prompts = []
                    
                    for line in content.split('\n'):
                        line_stripped = line.strip()
                        if line_stripped.lower().startswith("# reply prompt"):
                            if current_prompt:
                                prompt_text = '\n'.join(current_prompt).strip()
                                if prompt_text:
                                    if current_section == "reply":
                                        reply_prompts.append(prompt_text)
                                    elif current_section == "post":
                                        post_prompts.append(prompt_text)
                                current_prompt = []
                            current_section = "reply"
                        elif line_stripped.lower().startswith("# post prompt"):
                            if current_prompt:
                                prompt_text = '\n'.join(current_prompt).strip()
                                if prompt_text:
                                    if current_section == "reply":
                                        reply_prompts.append(prompt_text)
                                    elif current_section == "post":
                                        post_prompts.append(prompt_text)
                                current_prompt = []
                            current_section = "post"
                        elif line_stripped.startswith("#") or not line_stripped:
                            if not line_stripped and current_prompt:
                                prompt_text = '\n'.join(current_prompt).strip()
                                if prompt_text:
                                    if current_section == "reply":
                                        reply_prompts.append(prompt_text)
                                    elif current_section == "post":
                                        post_prompts.append(prompt_text)
                                current_prompt = []
                        else:
                            current_prompt.append(line)
                    
                    if current_prompt:
                        prompt_text = '\n'.join(current_prompt).strip()
                        if prompt_text:
                            if current_section == "reply":
                                reply_prompts.append(prompt_text)
                            elif current_section == "post":
                                post_prompts.append(prompt_text)
                    
                    reply_prompt = reply_prompts[0] if reply_prompts else ""
                    post_prompt = post_prompts[0] if post_prompts else ""
                
                # Fallback to bot.py constants if file doesn't exist or is empty
                if not reply_prompt:
                    from .bot import SYSTEM_PROMPT
                    reply_prompt = SYSTEM_PROMPT
                if not post_prompt:
                    from .bot import POST_SYSTEM_PROMPT
                    post_prompt = POST_SYSTEM_PROMPT
            
            # Update text widgets only if they don't have focus (user isn't editing them)
            if not hasattr(self, 'reply_prompt_text') or not self.reply_prompt_text.focus_get() == self.reply_prompt_text:
                self.reply_prompt_text.delete(1.0, tk.END)
                self.reply_prompt_text.insert(1.0, reply_prompt.strip())
            
            if not hasattr(self, 'post_prompt_text') or not self.post_prompt_text.focus_get() == self.post_prompt_text:
                self.post_prompt_text.delete(1.0, tk.END)
                self.post_prompt_text.insert(1.0, post_prompt.strip())
        except Exception as e:
            logger.debug(f"Failed to update prompts display: {e}")
    
    def update_prompts(self):
        """Update the prompts file with new values from GUI."""
        try:
            reply_prompt = self.reply_prompt_text.get(1.0, tk.END).strip()
            post_prompt = self.post_prompt_text.get(1.0, tk.END).strip()
            
            if not reply_prompt or not post_prompt:
                messagebox.showerror("Error", "Prompts cannot be empty")
                return
            
            # Update the prompts file
            prompts_file = self.bot.config.system_prompts_path
            if not prompts_file:
                prompts_file = Path("config/system_prompts.txt")
            
            # Ensure directory exists
            prompts_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Write prompts to file (reply first, then post)
            with open(prompts_file, 'w', encoding='utf-8') as f:
                f.write("# Reply prompt - used for generating replies to posts\n")
                f.write(reply_prompt + "\n")
                f.write("\n# Post prompt - used for generating new posts\n")
                f.write(post_prompt + "\n")
            
            # Also update the bot.py constants (for immediate use)
            # Note: This modifies the source code, which may not be ideal
            # For now, we'll just update the file and let the prompt manager reload it
            logger.info(f"Updated prompts file: {prompts_file}")
            
            # Trigger prompt reload (run in bot's event loop if available)
            if hasattr(self.bot, 'prompt_manager'):
                # Try to reload prompts in the bot's event loop
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # Event loop is running, schedule the reload as a task
                        asyncio.create_task(self.bot.prompt_manager._reload_if_changed())
                    else:
                        # No running loop, run it directly
                        asyncio.run(self.bot.prompt_manager._reload_if_changed())
                except (RuntimeError, Exception) as reload_error:
                    # No event loop exists or other error, try to create one and run
                    try:
                        asyncio.run(self.bot.prompt_manager._reload_if_changed())
                    except Exception as e:
                        logger.warning(f"Could not trigger prompt reload: {e}")
            
            messagebox.showinfo("Success", "Prompts updated successfully!\nThe bot will use the new prompts on the next reload cycle.")
            
        except Exception as e:
            logger.error(f"Failed to update prompts: {e}")
            messagebox.showerror("Error", f"Failed to update prompts: {e}")
    
    def _save_config(self):
        """Save the current config to file if config path is available."""
        if self.config_path:
            try:
                self.bot.config.to_file(self.config_path)
                logger.info(f"Configuration saved to {self.config_path}")
            except Exception as e:
                logger.warning(f"Failed to save config to {self.config_path}: {e}")
        else:
            logger.debug("No config file path available, skipping config save")
    
    def stop_bot(self):
        """Stop the bot gracefully."""
        if messagebox.askyesno("Stop Bot", "Are you sure you want to stop the bot?\nThis will stop all automation."):
            try:
                # Set running flag to False to stop the main loop
                self.bot.running = False
                
                # Schedule async stop in the event loop
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # Create a task to stop the bot
                        asyncio.create_task(self.bot.stop())
                    else:
                        # If no running loop, run stop directly
                        asyncio.run(self.bot.stop())
                except RuntimeError:
                    # No event loop, create one
                    try:
                        asyncio.run(self.bot.stop())
                    except Exception as stop_error:
                        logger.warning(f"Could not stop bot gracefully: {stop_error}")
                        # At least set running to False
                        self.bot.running = False
                except Exception as stop_error:
                    logger.warning(f"Could not stop bot gracefully: {stop_error}")
                    # At least set running to False
                    self.bot.running = False
                
                logger.info("Bot stop requested from GUI")
                messagebox.showinfo("Bot Stopped", "The bot has been stopped.")
                
            except Exception as e:
                logger.error(f"Failed to stop bot: {e}")
                messagebox.showerror("Error", f"Failed to stop bot: {e}")
    
    def update_post_ratio(self):
        """Update the post-to-reply ratio from GUI value."""
        try:
            ratio = float(self.post_ratio_var.get())
            
            if ratio < 0.0 or ratio > 1.0:
                messagebox.showerror("Error", "Ratio must be between 0.0 and 1.0")
                return
            
            # Update bot ratio
            self.bot.post_to_reply_ratio = ratio
            # Update config
            self.bot.config.post_to_reply_ratio = ratio
            
            # Save config to file if path is available
            self._save_config()
            
            post_percent = ratio * 100
            reply_percent = (1.0 - ratio) * 100
            logger.info(f"Updated post-to-reply ratio: {ratio} ({post_percent:.1f}% new posts, {reply_percent:.1f}% replies)")
            messagebox.showinfo("Success", f"Post-to-reply ratio updated to {post_percent:.1f}% new posts, {reply_percent:.1f}% replies")
            
        except ValueError:
            messagebox.showerror("Error", "Invalid ratio value. Please enter a number between 0.0 and 1.0.")
        except Exception as e:
            logger.error(f"Failed to update post-to-reply ratio: {e}")
            messagebox.showerror("Error", f"Failed to update ratio: {e}")
    
    def update_cooldown(self):
        """Update the cooldown range from GUI values."""
        try:
            min_cooldown = float(self.min_cooldown_var.get())
            max_cooldown = float(self.max_cooldown_var.get())
            
            if min_cooldown < 0 or max_cooldown < 0:
                messagebox.showerror("Error", "Cooldown values must be positive")
                return
            
            if min_cooldown > max_cooldown:
                messagebox.showerror("Error", "Minimum cooldown must be less than or equal to maximum cooldown")
                return
            
            # Update bot config
            self.bot.config.timing.min_post_reply_cooldown_seconds = min_cooldown
            self.bot.config.timing.max_post_reply_cooldown_seconds = max_cooldown
            
            # Save config to file if path is available
            self._save_config()
            
            logger.info(f"Updated cooldown range: {min_cooldown}s - {max_cooldown}s")
            messagebox.showinfo("Success", f"Cooldown range updated to {min_cooldown}s - {max_cooldown}s")
            
        except ValueError:
            messagebox.showerror("Error", "Invalid cooldown values. Please enter numbers.")
        except Exception as e:
            logger.error(f"Failed to update cooldown: {e}")
            messagebox.showerror("Error", f"Failed to update cooldown: {e}")
    
    def update_ai_settings(self):
        """Update AI model and temperature from GUI values."""
        try:
            model = self.model_var.get()
            temperature = self.temperature_var.get()
            
            if temperature < 0.0 or temperature > 2.0:
                messagebox.showerror("Error", "Temperature must be between 0.0 and 2.0")
                return
            
            # Update bot
            self.bot.ai_model = model
            self.bot.temperature = temperature
            
            # Update config
            self.bot.config.ai_model = model
            self.bot.config.temperature = temperature
            
            # Save config to file if path is available
            self._save_config()
            
            logger.info(f"Updated AI settings: model={model}, temperature={temperature:.2f}")
            messagebox.showinfo("Success", f"AI settings updated:\nModel: {model}\nTemperature: {temperature:.2f}")
            
        except Exception as e:
            logger.error(f"Failed to update AI settings: {e}")
            messagebox.showerror("Error", f"Failed to update AI settings: {e}")
    
    def view_logs(self):
        """Open a window to view log files."""
        log_window = tk.Toplevel(self.root)
        log_window.title("Log File Viewer")
        log_window.geometry("800x600")
        
        # Get log file path
        log_path = self.bot.config.logging.file_path if self.bot.config.logging.file_path else None
        
        # If no log path configured, try to find log files
        if not log_path or not Path(log_path).exists():
            # Try to find log files in common locations
            possible_paths = [
                Path("logs"),
                Path.home() / ".aiwebbot" / "logs",
                Path.cwd() / "logs"
            ]
            
            log_files = []
            for path in possible_paths:
                if path.exists() and path.is_dir():
                    log_files.extend(list(path.glob("*.log")))
            
            if not log_files:
                # Show message that no logs found
                no_logs_label = ttk.Label(log_window, text="No log files found.\n\nLog file path is not configured or log files don't exist.", 
                                         font=("Arial", 10), justify=tk.CENTER)
                no_logs_label.pack(expand=True, fill=tk.BOTH, padx=20, pady=20)
                return
            
            # If multiple log files, show selection
            if len(log_files) > 1:
                selection_frame = ttk.Frame(log_window, padding="10")
                selection_frame.pack(fill=tk.X)
                
                ttk.Label(selection_frame, text="Select log file:", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
                log_file_var = tk.StringVar(value=str(log_files[-1]))  # Default to most recent
                log_file_combo = ttk.Combobox(selection_frame, textvariable=log_file_var, 
                                             values=[str(f) for f in sorted(log_files, key=lambda x: x.stat().st_mtime, reverse=True)],
                                             state="readonly", width=60)
                log_file_combo.pack(side=tk.LEFT, padx=5)
                
                def load_selected_log():
                    load_log_file(log_file_var.get())
                
                ttk.Button(selection_frame, text="Load", command=load_selected_log).pack(side=tk.LEFT, padx=5)
                log_path = log_files[-1]  # Default to most recent
            else:
                log_path = log_files[0]
        
        # Create text widget with scrollbar
        text_frame = ttk.Frame(log_window)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        log_text = scrolledtext.ScrolledText(text_frame, wrap=tk.WORD, yscrollcommand=scrollbar.set)
        log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=log_text.yview)
        
        def load_log_file(file_path):
            """Load log file content into text widget."""
            try:
                log_text.delete(1.0, tk.END)
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    # Read last 10000 lines to avoid loading huge files
                    lines = f.readlines()
                    if len(lines) > 10000:
                        lines = lines[-10000:]
                        log_text.insert(1.0, f"[Showing last 10,000 lines of {len(lines)} total lines]\n\n")
                    log_text.insert(tk.END, ''.join(lines))
                log_text.see(tk.END)  # Scroll to bottom
            except Exception as e:
                log_text.delete(1.0, tk.END)
                log_text.insert(1.0, f"Error loading log file: {e}")
        
        # Load the log file
        if log_path:
            load_log_file(log_path)
        
        # Add refresh button
        button_frame = ttk.Frame(log_window)
        button_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(button_frame, text="Refresh", command=lambda: load_log_file(log_path) if log_path else None).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Close", command=log_window.destroy).pack(side=tk.RIGHT, padx=5)
    
    def update_loop(self):
        """Periodic update loop for the GUI."""
        self.update_display()
        self.root.after(1000, self.update_loop)  # Update every second
    
    def on_closing(self):
        """Handle window closing event."""
        if messagebox.askokcancel("Quit", "Do you want to quit the GUI?\nThe bot will continue running in the background."):
            self.root.destroy()
    
    def run(self):
        """Start the GUI main loop."""
        self.root.mainloop()


def run_gui(bot, config_path=None):
    """Run the GUI in a separate thread."""
    def gui_thread():
        gui = BotGUI(bot, config_path=config_path)
        gui.run()
    
    thread = threading.Thread(target=gui_thread, daemon=True)
    thread.start()
    return thread

