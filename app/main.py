"""Desktop entry point: python app/main.py (works from any directory)."""
import asyncio
import math
import random
import sys
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import flet as ft

from app.services.remy_service import RemyService
from src.config import ASSETS_DIR


# ─────────────────────────────────────────
# PALETTE: tek vurgu rengi, durum renkleri sadece nokta ve dalgada
# ─────────────────────────────────────────
VOID = "#05080C"
SURFACE = "#0C131A"
SURFACE_HIGH = "#121B23"
TEXT = "#E6EDF3"
MUTED = "#9AA7B4"
FAINT = "#6B7785"
ACCENT = "#22D3EE"
GREEN = "#34D399"
AMBER = "#FBBF24"
RED = "#F87171"
MONO = "Menlo"


def tint(color, opacity):
    return ft.Colors.with_opacity(opacity, color)


BORDER = tint("#FFFFFF", 0.08)
RADIUS = 10
SMOOTH = ft.Animation(250, ft.AnimationCurve.EASE_OUT)
FIELD_BORDER = ft.OutlineInputBorder(border_radius=8, side=ft.BorderSide(1, BORDER))

# state → (label, hint, color, bar height range as a share of the panel)
STATES = {
    "idle": ("Standby", "Voice is off. Type below or turn voice on.", MUTED, 0.0),
    "waiting": ("Ready", "Say \"Hey Remy\"", ACCENT, 0.12),
    "listening": ("Listening", "Go ahead, I'm listening", GREEN, 0.6),
    "thinking": ("Thinking", "Working on it", AMBER, 0.4),
    "speaking": ("Speaking", "Remy is talking", ACCENT, 1.0),
}
BUSY_STATES = ("thinking", "speaking")
MAX_ENTRIES = 100

BAR_COUNT = 32
BAR_WIDTH = 3
BAR_MAX_HEIGHT = 40
BAR_MIN_HEIGHT = 2
FRAME_SECONDS = 0.14
IDLE_SECONDS = 0.5

# role → (label, label color, text color)
LOG_STYLES = {
    "user": ("You", ACCENT, TEXT),
    "remy": ("Remy", GREEN, TEXT),
    "tool": ("System", AMBER, MUTED),
}

# Kamera: model etiketi → simge, ve hareket listesi
GESTURE_ICONS = {
    "PALM": "✋", "FIST": "✊", "THUMB UP": "👍", "POINT UP": "☝️",
    "THUMB DOWN": "👎", "VICTORY": "✌️", "LOVE": "🤟",
}
GESTURE_NAMES = {
    "PALM": "Open palm", "FIST": "Fist", "THUMB UP": "Thumb up", "POINT UP": "Pointing up",
    "THUMB DOWN": "Thumb down", "VICTORY": "Victory", "LOVE": "I love you",
}
GESTURE_LEGEND = [
    ("✋", "Wake (hold)"), ("✊", "Stop"), ("👍", "End chat"), ("☝️", "Volume up"),
    ("👎", "Volume down"), ("✌️", "Repeat"), ("🤟", "Time"), ("✋✊", "Chrome"),
]
GESTURE_HINTS = {
    "wake": "✋ Open palm: listening",
    "stop": "✊ Fist: stopped",
    "done": "👍 Thumb up: conversation ended",
    "volume_up": "☝️ Pointing up: volume up",
    "volume_down": "👎 Thumb down: volume down",
    "repeat": "✌️ Victory: repeating",
    "time": "🤟 I love you: telling the time",
    "open_chrome": "✋✊ Open-close: opening Chrome",
}
PREVIEW_WIDTH = 160
PREVIEW_HEIGHT = 120


def stamp(value=None):
    """HH:MM for a log line; value is an ISO timestamp from the database."""
    if value:
        try:
            return datetime.fromisoformat(value).strftime("%H:%M")
        except ValueError:
            return "--:--"
    return datetime.now().strftime("%H:%M")


def card(content, padding=12, visible=True):
    return ft.Container(
        content=content,
        padding=padding,
        bgcolor=tint(SURFACE, 0.72),
        border=ft.Border.all(1, BORDER),
        border_radius=RADIUS,
        blur=ft.Blur(12, 12),
        visible=visible,
    )


def main(page: ft.Page):
    page.title = "Remy"
    page.window.width = 440
    page.window.height = 900
    page.window.min_width = 400
    page.window.min_height = 680
    page.bgcolor = VOID
    page.padding = 0
    page.spacing = 0
    page.theme_mode = ft.ThemeMode.DARK
    page.dark_theme = ft.Theme(color_scheme_seed=ACCENT)

    current = {"state": "idle", "live_entry": None}

    def refresh():
        try:
            page.update()
        except Exception as e:
            # Pencere kapanırken arka plan thread'leri buraya düşebilir
            print(f"UI update skipped: {e}")

    # ─── Top bar ───
    state_dot = ft.Container(width=7, height=7, border_radius=4, bgcolor=MUTED, animate=SMOOTH)
    state_label = ft.Text("Standby", size=12, weight=ft.FontWeight.W_500, color=MUTED)
    state_pill = ft.Container(
        content=ft.Row([state_dot, state_label], spacing=7, tight=True),
        padding=ft.Padding.symmetric(horizontal=11, vertical=5),
        border_radius=20,
        bgcolor=tint(MUTED, 0.1),
        animate=SMOOTH,
    )
    clock = ft.Text("--:--", size=12, color=MUTED, font_family=MONO)

    top_bar = ft.Container(
        content=ft.Row(
            [
                ft.Text("REMY", size=14, weight=ft.FontWeight.W_700, color=ACCENT, font_family=MONO,
                        style=ft.TextStyle(letter_spacing=5)),
                ft.Container(expand=True),
                state_pill,
                clock,
            ],
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.Padding.only(left=20, right=20, top=16, bottom=14),
        border=ft.Border.only(bottom=ft.BorderSide(1, BORDER)),
        bgcolor=tint(VOID, 0.35),
        blur=ft.Blur(16, 16),
    )

    # ─── Waveform ───
    bars = [
        ft.Container(width=BAR_WIDTH, height=BAR_MIN_HEIGHT, border_radius=2, bgcolor=MUTED,
                     animate=ft.Animation(int(FRAME_SECONDS * 1000), ft.AnimationCurve.EASE_OUT))
        for _ in range(BAR_COUNT)
    ]
    hint = ft.Text(STATES["idle"][1], size=12, color=MUTED, max_lines=1,
                   overflow=ft.TextOverflow.ELLIPSIS, text_align=ft.TextAlign.CENTER)
    wave = ft.Container(
        content=ft.Column(
            [
                ft.Row(bars, spacing=4, height=BAR_MAX_HEIGHT,
                       alignment=ft.MainAxisAlignment.CENTER,
                       vertical_alignment=ft.CrossAxisAlignment.CENTER),
                hint,
            ],
            spacing=10,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.Padding.symmetric(vertical=14),
    )

    # ─── Camera (only while CAM is on) ───
    camera_image = ft.Image(src=b"", width=PREVIEW_WIDTH, height=PREVIEW_HEIGHT,
                            fit=ft.BoxFit.COVER, gapless_playback=True, border_radius=8)
    live_badge = ft.Container(
        content=ft.Row([ft.Container(width=6, height=6, border_radius=3, bgcolor=RED),
                        ft.Text("Live", size=10, weight=ft.FontWeight.W_600, color=TEXT)],
                       spacing=5, tight=True),
        padding=ft.Padding.symmetric(horizontal=7, vertical=3),
        border_radius=10,
        bgcolor=tint(VOID, 0.65),
        left=8, top=8,
    )
    gesture_name = ft.Text("No hand", size=16, weight=ft.FontWeight.W_600, color=MUTED)
    gesture_hold = ft.ProgressBar(value=0, color=ACCENT, bgcolor=tint(ACCENT, 0.12),
                                  bar_height=3, border_radius=2)

    def legend_row(icon, action):
        return ft.Row(
            [ft.Text(icon, size=11, width=26, no_wrap=True),
             ft.Text(action, size=11, color=MUTED, no_wrap=True)],
            spacing=4,
        )

    half = (len(GESTURE_LEGEND) + 1) // 2
    legend = ft.Row(
        [
            ft.Column([legend_row(*item) for item in GESTURE_LEGEND[:half]], spacing=3, expand=True),
            ft.Column([legend_row(*item) for item in GESTURE_LEGEND[half:]], spacing=3, expand=True),
        ],
        spacing=6,
        vertical_alignment=ft.CrossAxisAlignment.START,
    )
    camera_panel = card(
        ft.Row(
            [
                ft.Stack([camera_image, live_badge], width=PREVIEW_WIDTH, height=PREVIEW_HEIGHT),
                ft.Column(
                    [
                        ft.Text("Gesture", size=11, color=FAINT),
                        gesture_name,
                        gesture_hold,
                        ft.Container(height=4),
                        legend,
                    ],
                    spacing=4,
                    expand=True,
                ),
            ],
            spacing=14,
            vertical_alignment=ft.CrossAxisAlignment.START,
        ),
        padding=10,
        visible=False,
    )

    # ─── Conversation ───
    empty_state = ft.Container(
        content=ft.Column(
            [
                ft.Icon(ft.Icons.GRAPHIC_EQ, size=28, color=FAINT),
                ft.Text("Say \"Hey Remy\" or type below.", size=13, color=MUTED),
            ],
            spacing=8,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.Padding.only(top=70),
        alignment=ft.Alignment.CENTER,
    )
    log = ft.ListView(
        controls=[empty_state],
        spacing=4,
        expand=True,
        padding=ft.Padding.symmetric(vertical=8),
    )

    def make_entry(role, text, when=None, image=None):
        label, label_color, text_color = LOG_STYLES[role]
        message = ft.Text(text, size=14 if role != "tool" else 13, color=text_color, selectable=True,
                          style=ft.TextStyle(height=1.45))
        body = [message]
        if image:
            # Remy'nin "what is it?" cevabını verirken baktığı fotoğraf
            body.append(ft.Image(src=image, height=140, fit=ft.BoxFit.CONTAIN, border_radius=8))
        entry = ft.Container(
            content=ft.Row(
                [
                    ft.Column(
                        [
                            ft.Text(label, size=12, weight=ft.FontWeight.W_600, color=label_color),
                            ft.Text(stamp(when), size=10, color=FAINT, font_family=MONO),
                        ],
                        spacing=2,
                        tight=True,
                        width=52,
                    ),
                    ft.Column(body, spacing=8, expand=True, tight=True),
                ],
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.START,
            ),
            padding=ft.Padding.symmetric(horizontal=12, vertical=10),
            border_radius=8,
            bgcolor=tint(ACCENT, 0.05) if role == "user" else None,
        )
        entry.data = message
        return entry

    def append_entry(role, text, when=None, image=None):
        if empty_state in log.controls:
            log.controls.remove(empty_state)
        entry = make_entry(role, text, when, image)
        log.controls.append(entry)
        del log.controls[:-MAX_ENTRIES]
        return entry

    async def _scroll_to_end():
        # Önce yeni satırın yerleşimi hesaplansın, yoksa altı kırpılır
        await asyncio.sleep(0.1)
        await log.scroll_to(offset=-1, duration=200)

    def refresh_and_scroll():
        refresh()
        page.run_task(_scroll_to_end)

    def on_message(role, text):
        if not text:
            current["live_entry"] = None
            return
        live = current["live_entry"]
        if role == "remy" and live is not None:
            # Cümle cümle dolan satırı nihai metinle tamamla
            live.data.value = text
        else:
            append_entry(role, text)
        if role == "remy":
            current["live_entry"] = None
        refresh_and_scroll()

    def on_sentence(sentence):
        live = current["live_entry"]
        if live is None:
            current["live_entry"] = append_entry("remy", sentence)
        else:
            live.data.value = f"{live.data.value} {sentence}"
        refresh_and_scroll()

    # ─── Controls ───
    def control_button(text, icon, color=MUTED, on_click=None, expand=True):
        label = ft.Text(text, size=13, weight=ft.FontWeight.W_500, color=color)
        icon_control = ft.Icon(icon, size=17, color=color)
        button = ft.Container(
            content=ft.Row([icon_control, label], spacing=7, tight=True,
                           alignment=ft.MainAxisAlignment.CENTER),
            height=40,
            expand=expand,
            alignment=ft.Alignment.CENTER,
            padding=ft.Padding.symmetric(horizontal=12),
            border=ft.Border.all(1, BORDER),
            border_radius=8,
            bgcolor=tint(SURFACE, 0.7),
            blur=ft.Blur(10, 10),
            ink=True,
            on_click=on_click,
            animate=SMOOTH,
        )
        button.data = {"label": label, "icon": icon_control}
        return button

    def paint_toggle(button, active, on_icon, off_icon):
        """On: accent text and a faint accent fill. Off: muted."""
        color = ACCENT if active else MUTED
        parts = button.data
        parts["label"].color = color
        parts["icon"].icon = on_icon if active else off_icon
        parts["icon"].color = color
        button.border = ft.Border.all(1, tint(ACCENT, 0.45) if active else BORDER)
        button.bgcolor = tint(ACCENT, 0.14) if active else tint(SURFACE, 0.7)

    voice_button = control_button("Voice", ft.Icons.MIC_OFF)
    camera_button = control_button("Camera", ft.Icons.VIDEOCAM_OFF)
    tools_button = control_button("Tools", ft.Icons.TUNE)
    stop_button = control_button("Stop", ft.Icons.STOP_CIRCLE_OUTLINED, RED)
    stop_button.border = ft.Border.all(1, tint(RED, 0.4))
    stop_button.visible = False

    def on_state(state):
        current["state"] = state
        if state in STATES:
            label, text, color, _ = STATES[state]
            hint.value = text
            hint.color = MUTED
        else:
            label, color = "Error", RED
            hint.value = state[:90]
            hint.color = RED
        state_label.value = label
        state_label.color = color
        state_dot.bgcolor = color
        state_pill.bgcolor = tint(color, 0.12)
        for bar in bars:
            bar.bgcolor = color

        stop_button.visible = state in BUSY_STATES
        paint_toggle(voice_button, service.voice_active, ft.Icons.MIC, ft.Icons.MIC_OFF)
        refresh()

    service = RemyService(on_state=on_state, on_message=on_message, on_sentence=on_sentence)

    def on_snapshot(jpeg):
        append_entry("tool", "What Remy saw", image=jpeg)
        refresh_and_scroll()

    service.on_snapshot = on_snapshot

    def toggle_voice(e):
        if service.voice_active:
            service.stop_voice()
            on_state("idle")
        else:
            service.start_voice()
            on_state("waiting")

    def stop_speaking(e):
        service.stop_speaking()
        on_state("waiting" if service.voice_active else "idle")

    voice_button.on_click = toggle_voice
    stop_button.on_click = stop_speaking

    # ─── Camera gestures ───
    def paint_camera():
        active = service.camera_active
        paint_toggle(camera_button, active, ft.Icons.VIDEOCAM, ft.Icons.VIDEOCAM_OFF)
        camera_panel.visible = active
        if not active:
            camera_image.src = b""
            gesture_name.value = "No hand"
            gesture_name.color = MUTED
            gesture_hold.value = 0

    def on_camera_preview(jpeg, label, progress):
        camera_image.src = jpeg
        if label:
            gesture_name.value = f"{GESTURE_ICONS.get(label, '')}  {GESTURE_NAMES.get(label, label)}"
            gesture_name.color = GREEN if progress >= 1 else TEXT
        else:
            gesture_name.value = "No hand"
            gesture_name.color = MUTED
        gesture_hold.value = progress
        refresh()

    def on_gesture(action):
        if action in ("wake", "done") and not service.voice_active:
            message = "Turn voice on to use this gesture"
        else:
            message = GESTURE_HINTS[action]
        hint.value = message
        hint.color = ACCENT
        append_entry("tool", message)
        refresh_and_scroll()

    def on_camera_error(message):
        service.stop_camera()
        paint_camera()
        on_message("tool", f"Camera: {message}")

    def toggle_camera(e):
        if service.camera_active:
            service.stop_camera()
        else:
            service.start_camera(on_camera_preview, on_gesture, on_camera_error)
        paint_camera()
        refresh()

    camera_button.on_click = toggle_camera

    # ─── Waveform and clock ───
    # Dalga durumu gösteren bir animasyon, gerçek mikrofon seviyesi değil
    def animation_loop():
        rng = random.Random()
        phase = 0.0
        flat = False
        while True:
            state = current["state"]
            level = STATES[state][3] if state in STATES else 0.0
            clock.value = datetime.now().strftime("%H:%M")

            if level == 0.0:
                if not flat:
                    for bar in bars:
                        bar.height = BAR_MIN_HEIGHT
                    flat = True
                refresh()
                time.sleep(IDLE_SECONDS)
                continue

            flat = False
            phase += 0.55
            for i, bar in enumerate(bars):
                # Ortası yüksek zarf
                envelope = 1 - abs(i - (BAR_COUNT - 1) / 2) / (BAR_COUNT / 2)
                if state == "thinking":
                    shape = 0.5 + 0.5 * math.sin(i * 0.5 - phase)
                elif state == "waiting":
                    shape = 0.5 + 0.5 * math.sin(i * 0.3 + phase * 0.4)
                else:
                    shape = rng.random()
                height = BAR_MIN_HEIGHT + BAR_MAX_HEIGHT * level * envelope * shape
                bar.height = min(BAR_MAX_HEIGHT, height)
            refresh()
            time.sleep(FRAME_SECONDS)

    threading.Thread(target=animation_loop, daemon=True).start()

    # ─── Dialogs for tools that need input ───
    def open_form(title, fields, submit_label, on_submit, extra_actions=None):
        def submit(e):
            page.pop_dialog()
            on_submit()

        actions = [ft.TextButton("Cancel", on_click=lambda e: page.pop_dialog())]
        actions += extra_actions or []
        actions.append(ft.FilledButton(
            submit_label, on_click=submit, bgcolor=ACCENT, color=VOID,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
        ))
        page.show_dialog(ft.AlertDialog(
            title=ft.Text(title, size=16, weight=ft.FontWeight.W_600, color=TEXT),
            content=ft.Column(fields, tight=True, spacing=12, width=320),
            actions=actions,
            bgcolor=SURFACE_HIGH,
            shape=ft.RoundedRectangleBorder(radius=14, side=ft.BorderSide(1, BORDER)),
        ))

    def text_form(label, title, tool, arg, hint_text, submit_label="Run"):
        field = ft.TextField(label=hint_text, autofocus=True, border=FIELD_BORDER)

        def go():
            value = (field.value or "").strip()
            if value:
                service.run_tool(label, tool, {arg: value})

        field.on_submit = lambda e: (page.pop_dialog(), go())
        open_form(title, [field], submit_label, go)

    def web_action(e):
        text_form("Web", "Search the web", "web_search", "query", "Search for", "Search")

    def pdf_action(e):
        text_form("PDF", "Read a PDF", "read_pdf", "file_path", "File in the Remy folder, e.g. report.pdf", "Read")

    def slider_form(label, title, tool, value, extra_actions=None):
        slider = ft.Slider(min=0, max=100, divisions=20, value=value, label="{value}%",
                           active_color=ACCENT, thumb_color=ACCENT)

        open_form(
            title, [slider], "Set",
            lambda: service.run_tool(label, tool, {"level": int(slider.value)}),
            extra_actions,
        )

    def volume_action(e):
        def quiet(tool, label):
            def handler(event):
                page.pop_dialog()
                service.run_tool(label, tool)
            return handler

        slider_form("Volume", "Volume", "set_volume", 50, [
            ft.TextButton("Mute", on_click=quiet("mute", "Volume")),
            ft.TextButton("Unmute", on_click=quiet("unmute", "Volume")),
        ])

    def brightness_action(e):
        slider_form("Brightness", "Brightness", "set_brightness", 50)

    def alarm_action(e):
        when = ft.TextField(label="Time (HH:MM)", value="07:00", border=FIELD_BORDER)
        message = ft.TextField(label="Message", value="Wake up!", border=FIELD_BORDER)
        open_form("Set an alarm", [when, message], "Set", lambda: service.run_tool(
            "Alarm", "set_alarm", {"alarm_time": when.value, "message": message.value}
        ))

    def reminder_action(e):
        default = (datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M")
        when = ft.TextField(label="When (YYYY-MM-DDTHH:MM)", value=default, border=FIELD_BORDER)
        content = ft.TextField(label="Remind me to...", autofocus=True, border=FIELD_BORDER)

        def go():
            if (content.value or "").strip():
                service.run_tool("Reminder", "set_reminder", {
                    "remind_at": when.value, "content": content.value.strip()
                })

        open_form("Set a reminder", [content, when], "Set", go)

    def quick(label, tool):
        return lambda e: service.run_tool(label, tool)

    def tool_key(text, icon, handler):
        return ft.Container(
            content=ft.Column(
                [ft.Icon(icon, size=18, color=TEXT), ft.Text(text, size=11, color=MUTED)],
                spacing=5,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            height=58,
            expand=True,
            border_radius=8,
            ink=True,
            on_click=handler,
            tooltip=text,
        )

    # Araçlar varsayılan olarak gizli, ekranı kalabalık etmesin
    tools_panel = card(
        ft.Column(
            [
                ft.Row(
                    [
                        tool_key("Time", ft.Icons.SCHEDULE, quick("Time", "get_time")),
                        tool_key("Date", ft.Icons.EVENT, quick("Date", "get_date")),
                        tool_key("Web", ft.Icons.PUBLIC, web_action),
                        tool_key("PDF", ft.Icons.DESCRIPTION_OUTLINED, pdf_action),
                        tool_key("Mail", ft.Icons.MAIL_OUTLINE, quick("Mail", "read_email")),
                    ],
                    spacing=4,
                ),
                ft.Row(
                    [
                        tool_key("Screen", ft.Icons.MONITOR, quick("Screen", "analyze_screen")),
                        tool_key("Volume", ft.Icons.VOLUME_UP_OUTLINED, volume_action),
                        tool_key("Bright", ft.Icons.LIGHT_MODE_OUTLINED, brightness_action),
                        tool_key("Alarm", ft.Icons.ALARM, alarm_action),
                        tool_key("Remind", ft.Icons.NOTIFICATIONS_NONE, reminder_action),
                    ],
                    spacing=4,
                ),
            ],
            spacing=4,
        ),
        padding=6,
        visible=False,
    )

    def toggle_tools(e):
        tools_panel.visible = not tools_panel.visible
        paint_toggle(tools_button, tools_panel.visible, ft.Icons.CLOSE, ft.Icons.TUNE)
        tools_button.data["label"].value = "Close" if tools_panel.visible else "Tools"
        refresh_and_scroll()

    tools_button.on_click = toggle_tools

    # ─── Composer ───
    composer = ft.TextField(
        hint_text="Message Remy",
        hint_style=ft.TextStyle(color=FAINT),
        color=TEXT,
        cursor_color=ACCENT,
        border=ft.InputBorder.NONE,
        content_padding=ft.Padding.symmetric(horizontal=4, vertical=12),
        text_size=14,
        dense=True,
        expand=True,
    )

    def send(e):
        text = (composer.value or "").strip()
        if not text:
            return
        composer.value = ""
        current["live_entry"] = None
        refresh()
        service.send_text(text)

    composer.on_submit = send

    send_button = ft.Container(
        content=ft.Icon(ft.Icons.ARROW_UPWARD_ROUNDED, size=18, color=VOID),
        width=34, height=34, border_radius=17,
        bgcolor=ACCENT,
        alignment=ft.Alignment.CENTER,
        ink=True,
        on_click=send,
        tooltip="Send",
    )
    composer_bar = ft.Container(
        content=ft.Row([composer, send_button], spacing=8,
                       vertical_alignment=ft.CrossAxisAlignment.CENTER),
        padding=ft.Padding.only(left=14, right=6, top=4, bottom=4),
        bgcolor=tint(SURFACE, 0.78),
        blur=ft.Blur(12, 12),
        border=ft.Border.all(1, BORDER),
        border_radius=RADIUS,
    )

    layout = ft.Column(
        [
            top_bar,
            ft.Container(
                content=ft.Column(
                    [
                        wave,
                        camera_panel,
                        log,
                        ft.Row([voice_button, camera_button, tools_button, stop_button], spacing=8),
                        tools_panel,
                        composer_bar,
                    ],
                    spacing=10,
                    expand=True,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                ),
                padding=ft.Padding.only(left=16, right=16, top=4, bottom=16),
                expand=True,
            ),
        ],
        spacing=0,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
    )

    page.add(ft.Container(
        content=layout,
        bgcolor=VOID,
        image=ft.DecorationImage(src="aurora_bg.png", fit=ft.BoxFit.COVER),
        expand=True,
    ))

    for role, text, when in service.history():
        if text:
            append_entry("user" if role == "user" else "remy", text, when)
    refresh_and_scroll()

    service.start_background()

    # Masada açık dururken seslenince duysun, butona basmak gerekmesin
    service.start_voice()
    on_state("waiting")


if __name__ == "__main__":
    ft.run(main, assets_dir=str(ASSETS_DIR))
