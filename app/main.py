import base64
import threading
import time
from pathlib import Path
import flet as ft
from services.remy_service import (
    voice_chat, run_tool,
    start_wake_word_loop, stop_wake_word_loop
)


# ─── Path setup ───
APP_DIR = Path(__file__).parent
PROJECT_ROOT = APP_DIR.parent
ASSETS_DIR = PROJECT_ROOT / "assets"

with open(ASSETS_DIR / "logo_base64.txt", "r") as f:
    LOGO_BASE64 = f.read().strip()


# ─────────────────────────────────────────
# APPLE MONOCHROME PALETTE
# ─────────────────────────────────────────
TEXT_PRIMARY = "#1C1C1E"
TEXT_SECONDARY = "#8E8E93"
TEXT_TERTIARY = "#C7C7CC"

ACCENT = "#007AFF"
ACCENT_DARK = "#0051D5"

CARD_BG = "#FFFFFF"
RED = "#FF3B30"
GREEN = "#34C759"
GRAY = "#8E8E93"


def main(page: ft.Page):
    page.title = "Remy"
    page.window_width = 420
    page.window_height = 880
    page.window_min_width = 380
    page.window_min_height = 650
    page.bgcolor = "#F2F2F7"
    page.padding = 0
    page.spacing = 0
    page.horizontal_alignment = ft.CrossAxisAlignment.STRETCH
    page.vertical_alignment = ft.MainAxisAlignment.START

    state = {
        "is_listening": False,
        "mode": "idle",
        "conversation_active": False,
    }

    # ─────────────────────────────────────────
    # HEADER — logo + "Remy"
    # ─────────────────────────────────────────
    header = ft.Container(
        content=ft.Row(
            [
                ft.Image(
                    src=LOGO_BASE64,
                    width=28,
                    height=28,
                    fit=ft.BoxFit.CONTAIN,
                ),
                ft.Container(width=10),
                ft.Text(
                    "Remy",
                    size=18,
                    weight=ft.FontWeight.W_600,
                    color=TEXT_PRIMARY,
                ),
            ],
            spacing=0,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.Padding.only(left=24, right=24, top=20, bottom=12),
    )

    # ─────────────────────────────────────────
    # STATUS
    # ─────────────────────────────────────────
    status_text = ft.Text(
        "Ready",
        size=13,
        color=TEXT_SECONDARY,
        text_align=ft.TextAlign.CENTER,
    )

    # ─────────────────────────────────────────
    # MICROPHONE
    # ─────────────────────────────────────────
    mic_icon = ft.Icon(ft.Icons.MIC, size=42, color="#FFFFFF")

    mic_button = ft.Container(
        content=mic_icon,
        width=110,
        height=110,
        border_radius=55,
        alignment=ft.Alignment.CENTER,
        ink=True,
        gradient=ft.LinearGradient(
            begin=ft.Alignment.TOP_LEFT,
            end=ft.Alignment.BOTTOM_RIGHT,
            colors=[ACCENT, ACCENT_DARK],
        ),
        shadow=ft.BoxShadow(
            blur_radius=24,
            spread_radius=1,
            color=ft.Colors.with_opacity(0.35, ACCENT),
            offset=ft.Offset(0, 6),
        ),
        animate=ft.Animation(300, ft.AnimationCurve.EASE_OUT),
        animate_scale=ft.Animation(300, ft.AnimationCurve.EASE_OUT),
    )

    pulse_ring = ft.Container(
        width=110,
        height=110,
        border_radius=55,
        bgcolor=ft.Colors.with_opacity(0.0, ACCENT),
        animate=ft.Animation(800, ft.AnimationCurve.EASE_IN_OUT),
    )

    # ✅ Stack genişliği mic_button ile AYNI (110) — kayma yok
    mic_stack = ft.Stack(
        [pulse_ring, mic_button],
        width=110,
        height=110,
    )

    # ─────────────────────────────────────────
    # TRANSCRIPT
    # ─────────────────────────────────────────
    transcript_column = ft.Column(
        [],
        spacing=8,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
    )

    def add_message(role, text):
        is_user = role == "user"
        bubble = ft.Container(
            content=ft.Text(
                text,
                size=13,
                color="#FFFFFF" if is_user else TEXT_PRIMARY,
                selectable=True,
            ),
            padding=ft.Padding.symmetric(horizontal=14, vertical=10),
            border_radius=ft.BorderRadius.only(
                top_left=18, top_right=18,
                bottom_left=18 if is_user else 4,
                bottom_right=4 if is_user else 18,
            ),
            bgcolor=ACCENT if is_user else CARD_BG,
            margin=ft.Margin.only(
                left=60 if is_user else 0,
                right=0 if is_user else 60,
            ),
            shadow=ft.BoxShadow(
                blur_radius=6,
                color=ft.Colors.with_opacity(0.05, "#000000"),
                offset=ft.Offset(0, 2),
            ),
        )
        transcript_column.controls.append(bubble)
        if len(transcript_column.controls) > 10:
            transcript_column.controls = transcript_column.controls[-10:]
        try:
            page.update()
        except:
            pass

    # ─────────────────────────────────────────
    # CALLBACKS
    # ─────────────────────────────────────────
    def on_result(user_text, reply):
        add_message("user", user_text)
        add_message("remy", reply)

    def on_status(status):
        if "Say 'Hey Jarvis'" in status or "💤" in status:
            set_mode("idle")
            status_text.value = "Say 'Hey Jarvis' to wake me"
        elif "Conversation mode ON" in status or "🎤 Conversation" in status:
            set_mode("conversation")
            status_text.value = "Conversation mode"
        elif "Listening" in status or "🎤" in status:
            set_mode("listening")
            status_text.value = "Listening..."
        elif "Speaking" in status or "🔊" in status:
            set_mode("speaking")
            status_text.value = "Speaking..."
        elif "Thinking" in status or "⏳" in status:
            set_mode("speaking")
            status_text.value = "Thinking..."
        elif "Ready" in status:
            set_mode("idle")
            status_text.value = "Ready"
        else:
            status_text.value = status[:60]
        try:
            page.update()
        except:
            pass

    # ─────────────────────────────────────────
    # MODE CHANGER
    # ─────────────────────────────────────────
    def set_mode(mode):
        state["mode"] = mode

        if mode == "idle":
            mic_button.gradient = ft.LinearGradient(
                begin=ft.Alignment.TOP_LEFT,
                end=ft.Alignment.BOTTOM_RIGHT,
                colors=[ACCENT, ACCENT_DARK],
            )
            mic_button.shadow = ft.BoxShadow(
                blur_radius=24, spread_radius=1,
                color=ft.Colors.with_opacity(0.35, ACCENT),
                offset=ft.Offset(0, 6),
            )
            pulse_ring.bgcolor = ft.Colors.with_opacity(0.0, ACCENT)

        elif mode == "listening":
            mic_button.gradient = ft.LinearGradient(
                begin=ft.Alignment.TOP_LEFT,
                end=ft.Alignment.BOTTOM_RIGHT,
                colors=["#34C759", "#00A650"],
            )
            mic_button.shadow = ft.BoxShadow(
                blur_radius=28, spread_radius=3,
                color=ft.Colors.with_opacity(0.45, GREEN),
                offset=ft.Offset(0, 6),
            )
            pulse_ring.bgcolor = ft.Colors.with_opacity(0.15, GREEN)

        elif mode == "speaking":
            mic_button.gradient = ft.LinearGradient(
                begin=ft.Alignment.TOP_LEFT,
                end=ft.Alignment.BOTTOM_RIGHT,
                colors=[ACCENT, ACCENT_DARK],
            )
            mic_button.shadow = ft.BoxShadow(
                blur_radius=28, spread_radius=3,
                color=ft.Colors.with_opacity(0.45, ACCENT),
                offset=ft.Offset(0, 6),
            )
            pulse_ring.bgcolor = ft.Colors.with_opacity(0.15, ACCENT)

        elif mode == "conversation":
            mic_button.gradient = ft.LinearGradient(
                begin=ft.Alignment.TOP_LEFT,
                end=ft.Alignment.BOTTOM_RIGHT,
                colors=[ACCENT, ACCENT_DARK],
            )
            mic_button.shadow = ft.BoxShadow(
                blur_radius=28, spread_radius=3,
                color=ft.Colors.with_opacity(0.45, ACCENT),
                offset=ft.Offset(0, 6),
            )
            pulse_ring.bgcolor = ft.Colors.with_opacity(0.12, ACCENT)

        try:
            page.update()
        except:
            pass

    # ─────────────────────────────────────────
    # PULSE ANIMATION
    # ─────────────────────────────────────────
    def pulse_animation():
        while True:
            try:
                if state["mode"] in ("listening", "speaking", "conversation"):
                    ring_color = GREEN if state["mode"] == "listening" else ACCENT
                    pulse_ring.scale = 1.20
                    pulse_ring.bgcolor = ft.Colors.with_opacity(0.20, ring_color)
                    page.update()
                    time.sleep(0.75)

                    pulse_ring.scale = 1.0
                    pulse_ring.bgcolor = ft.Colors.with_opacity(0.06, ring_color)
                    page.update()
                    time.sleep(0.75)
                else:
                    time.sleep(0.3)
            except:
                time.sleep(0.5)

    threading.Thread(target=pulse_animation, daemon=True).start()

    # ─────────────────────────────────────────
    # MIC TOGGLE
    # ─────────────────────────────────────────
    def toggle_listening(e):
        if state["is_listening"]:
            stop_wake_word_loop()
            state["is_listening"] = False
            state["conversation_active"] = False
            set_mode("idle")
            status_text.value = "Ready"
            transcript_column.controls.clear()
        else:
            start_wake_word_loop(on_result=on_result, on_status=on_status)
            state["is_listening"] = True
            state["conversation_active"] = True
            set_mode("conversation")
            status_text.value = "Say 'Hey Jarvis' to start"
        try:
            page.update()
        except:
            pass

    mic_button.on_click = toggle_listening

    # ─────────────────────────────────────────
    # TOOL BUTTONS
    # ─────────────────────────────────────────
    def tool_button(icon, label, tool_name):
        return ft.Container(
            content=ft.Column(
                [
                    ft.Container(
                        content=ft.Icon(icon, size=20, color=TEXT_PRIMARY),
                        width=50,
                        height=50,
                        border_radius=16,
                        alignment=ft.Alignment.CENTER,
                        bgcolor=CARD_BG,
                        shadow=ft.BoxShadow(
                            blur_radius=8,
                            color=ft.Colors.with_opacity(0.05, "#000000"),
                            offset=ft.Offset(0, 2),
                        ),
                    ),
                    ft.Container(height=6),
                    ft.Text(
                        label,
                        size=10,
                        color=TEXT_SECONDARY,
                        weight=ft.FontWeight.W_500,
                    ),
                ],
                spacing=0,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            width=70,
            height=86,
            alignment=ft.Alignment.CENTER,
            on_click=lambda e: run_tool(
                tool_name,
                on_result=lambda n, r: on_status(f"{n}: {r[:60]}"),
                on_status=on_status,
            ),
            ink=True,
            border_radius=14,
        )

    tools_grid = ft.Row(
        [
            tool_button(ft.Icons.ACCESS_TIME, "Time", "get_time"),
            tool_button(ft.Icons.CALENDAR_TODAY, "Date", "get_date"),
            tool_button(ft.Icons.PICTURE_AS_PDF, "PDF", "read_pdf"),
            tool_button(ft.Icons.LANGUAGE, "Web", "web_search"),
            tool_button(ft.Icons.EMAIL, "Mail", "read_email"),
            tool_button(ft.Icons.SCREENSHOT_MONITOR, "Screen", "analyze_screen"),
            tool_button(ft.Icons.VOLUME_UP, "Volume", "unmute"),
            tool_button(ft.Icons.VOLUME_OFF, "Mute", "mute"),
            tool_button(ft.Icons.LIGHT_MODE, "Bright", "set_brightness"),
            tool_button(ft.Icons.ALARM, "Alarm", "set_alarm"),
        ],
        wrap=True,
        spacing=4,
        run_spacing=4,
        alignment=ft.MainAxisAlignment.CENTER,
    )

    # ─────────────────────────────────────────
    # STOP BUTTON
    # ─────────────────────────────────────────
    def stop_speaking(e):
        set_mode("listening")
        status_text.value = "Interrupted"
        page.update()

    stop_button = ft.Container(
        content=ft.Row(
            [
                ft.Icon(ft.Icons.STOP_CIRCLE, size=14, color=RED),
                ft.Text(
                    "Stop",
                    size=12,
                    color=RED,
                    weight=ft.FontWeight.W_500,
                ),
            ],
            spacing=6,
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            tight=True,
        ),
        padding=ft.Padding.symmetric(horizontal=16, vertical=6),
        border_radius=16,
        bgcolor=ft.Colors.with_opacity(0.10, RED),
        on_click=stop_speaking,
        ink=True,
    )

    # ─────────────────────────────────────────
    # CONTROL BLOCK — mic + status + stop, ALL IN ONE COLUMN
    # ─────────────────────────────────────────
    # ✅ Tek Column içinde, horizontal_alignment=CENTER ile
    #    üçü de aynı dikey eksende hizalı
    control_block = ft.Column(
        [
            mic_stack,
            ft.Container(height=14),
            status_text,
            ft.Container(height=10),
            stop_button,
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=0,
    )

    # ─────────────────────────────────────────
    # MAIN LAYOUT
    # ─────────────────────────────────────────
    content = ft.Column(
        [
            # Header
            header,

            # ✅ control_block'u Row içinde ortala
            ft.Container(height=16),
            ft.Row(
                [control_block],
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            ft.Container(height=20),

            # Chat history (flexible area)
            ft.Container(
                content=transcript_column,
                expand=True,
                padding=ft.Padding.symmetric(horizontal=20),
            ),

            # Tools section (bottom, anchored)
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text(
                            "Quick Actions",
                            size=12,
                            color=TEXT_TERTIARY,
                            weight=ft.FontWeight.W_500,
                        ),
                        ft.Container(height=10),
                        tools_grid,
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=0,
                ),
                padding=ft.Padding.only(left=12, right=12, bottom=20, top=12),
            ),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        spacing=0,
        expand=True,
    )

    page.add(content)


ft.run(main, assets_dir=str(ASSETS_DIR))