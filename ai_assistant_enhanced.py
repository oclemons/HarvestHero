"""
ai_assistant_enhanced.py — Premium conversational AI interface.

Provides an immersive conversational AI experience with:
- Conversation panel with Level 3 Hero Mirror glass effect
- Message display (user right, AI left)
- Suggested prompts
- Follow-up suggestions
- Processing state animation
- Conversation management
"""

import customtkinter as ctk
from typing import Callable, Optional, List
import threading
from glass_effects_premium import GlassEffectManager
from theme import (
    BG_BASE, BG_SURFACE, BG_ELEVATED, BG_HOVER,
    ACCENT, ACCENT_GREEN, ACCENT_MUTED,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    FONT_FAMILY, BORDER_COLOR, BORDER_SUBTLE,
)


class ConversationMessage(ctk.CTkFrame):
    """Single message in conversation."""

    def __init__(self, parent, text: str, is_user: bool = False, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self._build(text, is_user)

    def _build(self, text: str, is_user: bool):
        """Build message layout."""
        # Message bubble
        bubble_color = ACCENT if is_user else BG_ELEVATED
        text_color = "white" if is_user else TEXT_PRIMARY
        anchor = "e" if is_user else "w"

        bubble = ctk.CTkFrame(
            self, fg_color=bubble_color, corner_radius=12,
            border_width=1, border_color=BORDER_SUBTLE
        )
        bubble.pack(anchor=anchor, padx=12, pady=6, fill="x")

        ctk.CTkLabel(
            bubble, text=text, wraplength=400,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=text_color, fg_color="transparent",
            justify="left"
        ).pack(padx=12, pady=8)


class PromptChip(ctk.CTkButton):
    """Suggested prompt chip."""

    def __init__(self, parent, text: str, on_click: Callable, **kwargs):
        super().__init__(
            parent, text=text, command=lambda: on_click(text),
            fg_color=BG_ELEVATED, hover_color=BG_HOVER,
            text_color=TEXT_PRIMARY, border_width=1, border_color=BORDER_COLOR,
            corner_radius=20, height=32,
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            **kwargs
        )


class ConversationPanel(ctk.CTkFrame):
    """Premium conversational AI interface."""

    def __init__(self, parent, db, on_send: Optional[Callable] = None, **kwargs):
        super().__init__(parent, fg_color=BG_BASE, **kwargs)
        self.db = db
        self.on_send = on_send
        self.messages = []
        self._glass_manager = GlassEffectManager({
            "name": "Harvest Day",
            "BG_ELEVATED": BG_ELEVATED,
            "BORDER_SUBTLE": BORDER_SUBTLE,
            "BORDER_COLOR": BORDER_COLOR,
            "TEXT_PRIMARY": TEXT_PRIMARY,
            "TEXT_SECONDARY": TEXT_SECONDARY,
        })
        self._build()

    def _build(self):
        """Build the conversation panel."""
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(16, 12))

        ctk.CTkLabel(
            header, text="Harvest AI Assistant",
            font=ctk.CTkFont(family=FONT_FAMILY, size=16, weight="bold"),
            text_color=TEXT_PRIMARY, fg_color="transparent"
        ).pack(anchor="w", side="left")

        # New conversation button
        ctk.CTkButton(
            header, text="+ New", width=80, height=32,
            fg_color=ACCENT, hover_color=ACCENT,
            text_color="white", font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            command=self._new_conversation
        ).pack(anchor="e", side="right")

        # Messages area (Level 3 Hero Mirror)
        messages_container = self._glass_manager.create_hero_mirror_panel(
            self, fg_color=BG_ELEVATED, corner_radius=16
        )
        messages_container.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        self.messages_frame = ctk.CTkScrollableFrame(
            messages_container, fg_color="transparent"
        )
        self.messages_frame.pack(fill="both", expand=True, padx=12, pady=12)

        # Suggested prompts
        self._build_suggested_prompts()

        # Input area
        self._build_input_area()

    def _build_suggested_prompts(self):
        """Build suggested prompts section."""
        prompts_label = ctk.CTkLabel(
            self.messages_frame, text="Suggested prompts:",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            text_color=TEXT_SECONDARY, fg_color="transparent"
        )
        prompts_label.pack(anchor="w", pady=(0, 8))

        prompts = [
            "What items are low in stock?",
            "Show me recent distributions",
            "How many clients visited today?",
            "What's our inventory status?",
        ]

        prompts_frame = ctk.CTkFrame(self.messages_frame, fg_color="transparent")
        prompts_frame.pack(fill="x", pady=(0, 16))

        for prompt in prompts:
            chip = PromptChip(prompts_frame, prompt, self._on_prompt_click)
            chip.pack(side="left", padx=4, pady=2)

    def _build_input_area(self):
        """Build input area."""
        input_frame = ctk.CTkFrame(self, fg_color="transparent")
        input_frame.pack(fill="x", padx=16, pady=(0, 16))

        # Input field
        self.input_entry = ctk.CTkEntry(
            input_frame, placeholder_text="Ask me anything...",
            height=40, fg_color=BG_ELEVATED, border_color=BORDER_COLOR,
            text_color=TEXT_PRIMARY, placeholder_text_color=TEXT_MUTED,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11)
        )
        self.input_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.input_entry.bind("<Return>", lambda e: self._send_message())

        # Send button
        self.send_btn = ctk.CTkButton(
            input_frame, text="Send →", width=80, height=40,
            fg_color=ACCENT, hover_color=ACCENT,
            text_color="white", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            command=self._send_message
        )
        self.send_btn.pack(side="right")

    def _on_prompt_click(self, prompt: str):
        """Handle prompt chip click."""
        self.input_entry.delete(0, "end")
        self.input_entry.insert(0, prompt)
        self._send_message()

    def _send_message(self):
        """Send a message."""
        text = self.input_entry.get().strip()
        if not text:
            return

        # Add user message
        self.add_message(text, is_user=True)
        self.input_entry.delete(0, "end")

        # Show processing state
        self.send_btn.configure(state="disabled", text="Processing...")

        # Call the callback
        if self.on_send:
            def _process():
                try:
                    response = self.on_send(text)
                    self.add_message(response, is_user=False)
                except Exception as e:
                    self.add_message(f"Error: {str(e)}", is_user=False)
                finally:
                    self.send_btn.configure(state="normal", text="Send →")

            thread = threading.Thread(target=_process, daemon=True)
            thread.start()

    def add_message(self, text: str, is_user: bool = False):
        """Add a message to the conversation."""
        message = ConversationMessage(self.messages_frame, text, is_user=is_user)
        message.pack(fill="x", pady=4)
        self.messages.append((text, is_user))

        # Scroll to bottom
        self.messages_frame._parent_canvas.yview_moveto(1.0)

    def _new_conversation(self):
        """Start a new conversation."""
        for widget in self.messages_frame.winfo_children():
            widget.destroy()
        self.messages.clear()

        # Add welcome message
        welcome = "Hello! I'm Harvest AI. How can I help you manage your pantry today?"
        self.add_message(welcome, is_user=False)

        # Show suggested prompts again
        self._build_suggested_prompts()

    def clear(self):
        """Clear all messages."""
        for widget in self.messages_frame.winfo_children():
            widget.destroy()
        self.messages.clear()
