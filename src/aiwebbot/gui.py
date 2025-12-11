"""GUI interface for AI Web Bot monitoring and control."""

import asyncio
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, scrolledtext, ttk
from typing import Optional

from loguru import logger


class BotGUI:
    """GUI interface for monitoring and controlling the AI Web Bot."""

    def __init__(self, bot):
        """Initialize the GUI with a reference to the bot."""
        self.bot = bot
        self.root = tk.Tk()
        self.root.title("AI Web Bot - Control Panel")
        self.root.geometry("900x800")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Set up GUI update callback
        self.bot.gui_callback = self.update_display
        
        # Create main interface
        self.create_widgets()
        
        # Start update loop
        self.update_display()
        self.root.after(1000, self.update_loop)  # Update every second
        
    def create_widgets(self):
        """Create and layout all GUI widgets."""
        # Main container with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="AI Web Bot Control Panel", font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, pady=(0, 20))
        
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
        
        ttk.Label(stats_frame, text="Total New Posts:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky=tk.W, pady=2)
        self.total_posts_label = ttk.Label(stats_frame, text="0", font=("Arial", 12))
        self.total_posts_label.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=2)
        
        ttk.Label(stats_frame, text="Total Replies:", font=("Arial", 10, "bold")).grid(row=1, column=0, sticky=tk.W, pady=2)
        self.total_replies_label = ttk.Label(stats_frame, text="0", font=("Arial", 12))
        self.total_replies_label.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=2)
        
        # System Prompts section
        prompts_frame = ttk.LabelFrame(main_frame, text="System Prompts", padding="10")
        prompts_frame.grid(row=4, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        prompts_frame.columnconfigure(0, weight=1)
        prompts_frame.rowconfigure(1, weight=1)
        prompts_frame.rowconfigure(3, weight=1)
        main_frame.rowconfigure(4, weight=1)
        
        # Reply prompt
        ttk.Label(prompts_frame, text="Reply Prompt:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky=tk.W, pady=2)
        self.reply_prompt_text = scrolledtext.ScrolledText(prompts_frame, height=4, wrap=tk.WORD, width=80)
        self.reply_prompt_text.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        # Post prompt
        ttk.Label(prompts_frame, text="New Post Prompt:", font=("Arial", 10, "bold")).grid(row=2, column=0, sticky=tk.W, pady=2)
        self.post_prompt_text = scrolledtext.ScrolledText(prompts_frame, height=4, wrap=tk.WORD, width=80)
        self.post_prompt_text.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        # Update prompts button
        update_prompts_btn = ttk.Button(prompts_frame, text="Update Prompts", command=self.update_prompts)
        update_prompts_btn.grid(row=4, column=0, pady=10)
        
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
            
            # Update text widgets
            self.reply_prompt_text.delete(1.0, tk.END)
            self.reply_prompt_text.insert(1.0, reply_prompt.strip())
            
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
                # Schedule reload in the bot's event loop
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.create_task(self.bot.prompt_manager._reload_if_changed())
                    else:
                        # If no running loop, create a new one temporarily
                        asyncio.run(self.bot.prompt_manager._reload_if_changed())
                except RuntimeError:
                    # No event loop, create one
                    try:
                        asyncio.run(self.bot.prompt_manager._reload_if_changed())
                    except Exception as reload_error:
                        logger.warning(f"Could not trigger prompt reload: {reload_error}")
                except Exception as reload_error:
                    logger.warning(f"Could not trigger prompt reload: {reload_error}")
            
            messagebox.showinfo("Success", "Prompts updated successfully!\nThe bot will use the new prompts on the next reload cycle.")
            
        except Exception as e:
            logger.error(f"Failed to update prompts: {e}")
            messagebox.showerror("Error", f"Failed to update prompts: {e}")
    
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
            
            logger.info(f"Updated cooldown range: {min_cooldown}s - {max_cooldown}s")
            messagebox.showinfo("Success", f"Cooldown range updated to {min_cooldown}s - {max_cooldown}s")
            
        except ValueError:
            messagebox.showerror("Error", "Invalid cooldown values. Please enter numbers.")
        except Exception as e:
            logger.error(f"Failed to update cooldown: {e}")
            messagebox.showerror("Error", f"Failed to update cooldown: {e}")
    
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


def run_gui(bot):
    """Run the GUI in a separate thread."""
    def gui_thread():
        gui = BotGUI(bot)
        gui.run()
    
    thread = threading.Thread(target=gui_thread, daemon=True)
    thread.start()
    return thread

