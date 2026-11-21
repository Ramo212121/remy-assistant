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
# HUD PALETTE
# ─────────────────────────────────────────
VOID = "#03070B"
PANEL = "#07121A"
TEXT_PRIMARY = "#D8F3F8"
TEXT_DIM = "#7FA6B4"
CYAN = "#22E3F5"
GREEN = "#3DFFA2"
AMBER = "#FFB72B"
RED = "#FF4D5E"
FONT = "Menlo"


def tint(color, opacity):
    return ft.Colors.with_opacity(opacity, color)


LINE = tint(CYAN, 0.28)
FIELD_BORDER = ft.OutlineInputBorder(border_radius=2, side=ft.BorderSide(1, LINE))
SQUARE = ft.RoundedRectangleBorder(radius=2)
SMOOTH = ft.Animation(300, ft.AnimationCurve.EASE_OUT)

# state → (tag, hint, color, bar height range as a share of the panel)
STATES = {
    "idle": ("STANDBY", "VOICE OFF. TYPE A COMMAND OR ENABLE VOICE.", TEXT_DIM, 0.0),
    "waiting": ("WAKE WORD", "SAY \"HEY REMY\"", CYAN, 0.12),
    "listening": ("LISTENING", "GO AHEAD, I'M LISTENING", GREEN, 0.6),
    "thinking": ("PROCESSING", "WORKING ON IT", AMBER, 0.4),
    "speaking": ("SPEAKING", "REMY IS TALKING", CYAN, 1.0),
}
BUSY_STATES = ("thinking", "speaking")
MAX_ENTRIES = 100

BAR_COUNT = 40
BAR_MAX_HEIGHT = 46
BAR_MIN_HEIGHT = 2
FRAME_SECONDS = 0.14
IDLE_SECONDS = 0.5
WAVE_HEIGHT = 92
SCAN_STEP = 9

# role → (tag, tag color, text color)
LOG_STYLES = {
    "user": ("USR", CYAN, "#FFFFFF"),
    "remy": ("RMY", GREEN, TEXT_PRIMARY),
    "tool": ("SYS", AMBER, AMBER),
}

# Kamera: model etiketi → simge, ve hareket listesi
GESTURE_ICONS = {
    "PALM": "✋", "FIST": "✊", "THUMB UP": "👍", "POINT UP": "☝️",
    "THUMB DOWN": "👎", "VICTORY": "✌️", "LOVE": "🤟",
}
GESTURE_LEGEND = [
    ("✋", "hold", "wake"), ("✊", "", "stop"), ("👍", "", "end chat"), ("☝️", "", "vol +"),
    ("👎", "", "vol −"), ("✌️", "", "repeat"), ("🤟", "", "time"), ("✋✊", "quick", "Chrome"),
]
GESTURE_HINTS = {
    "wake": "✋ PALM: LISTENING",
    "stop": "✊ FIST: STOPPED",
    "done": "👍 THUMB UP: CONVERSATION ENDED",
    "volume_up": "☝️ POINT UP: VOLUME UP",
    "volume_down": "👎 THUMB DOWN: VOLUME DOWN",
    "repeat": "✌️ VICTORY: REPEATING",
    "time": "🤟 LOVE: TELLING THE TIME",
    "open_chrome": "✋→✊ OPEN-CLOSE: OPENING CHROME",
}
PREVIEW_WIDTH = 168
PREVIEW_HEIGHT = 126


def stamp(value=None):
    """HH:MM for a log line; value is an ISO timestamp from the database."""
    if value:
        try:
            return datetime.fromisoformat(value).strftime("%H:%M")
        except ValueError:
            return "--:--"
    return datetime.now().strftime("%H:%M")


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
    page.dark_theme = ft.Theme(color_scheme_seed=CYAN, font_family=FONT)

    current = {"state": "idle", "live_entry": None}

    def refresh():
        try:
            page.update()
        except Exception as e:
            # Pencere kapanırken arka plan thread'leri buraya düşebilir
            print(f"UI update skipped: {e}")

    def corner(color=CYAN, size=10, **position):
        """One L-shaped bracket. position: left/right + top/bottom."""
        side = ft.BorderSide(1.5, color)
        none = ft.BorderSide(0, "transparent")
        return ft.Container(
            width=size, height=size,
            border=ft.Border(
                left=side if "left" in position else none,
                right=side if "right" in position else none,
                top=side if "top" in position else none,
                bottom=side if "bottom" in position else none,
            ),
            **position,
        )

    def brackets(color=CYAN, size=10):
        return [
            corner(color, size, left=0, top=0), corner(color, size, right=0, top=0),
            corner(color, size, left=0, bottom=0), corner(color, size, right=0, bottom=0),
        ]

    # ─── Top bar ───
    state_tag = ft.Text(STATES["idle"][0], size=11, weight=ft.FontWeight.W_700,
                        color=STATES["idle"][2], style=ft.TextStyle(letter_spacing=1.5))
    state_dot = ft.Container(width=6, height=6, bgcolor=STATES["idle"][2], animate=SMOOTH)
    state_chip = ft.Container(
        content=ft.Row([state_dot, state_tag], spacing=7, tight=True),
        padding=ft.Padding.symmetric(horizontal=9, vertical=4),
        border=ft.Border.all(1, tint(TEXT_DIM, 0.4)),
        animate=SMOOTH,
    )
    clock = ft.Text("--:--:--", size=11, color=TEXT_DIM)

    top_bar = ft.Container(
        content=ft.Row(
            [
                ft.Text("REMY", size=15, weight=ft.FontWeight.W_700, color=CYAN,
                        style=ft.TextStyle(letter_spacing=6)),
                ft.Container(expand=True),
                state_chip,
                clock,
            ],
            spacing=10,
        ),
        padding=ft.Padding.only(left=16, right=16, top=14, bottom=11),
        border=ft.Border.only(bottom=ft.BorderSide(1, LINE)),
    )

    # ─── Waveform panel ───
    bars = [
        ft.Container(width=4, height=BAR_MIN_HEIGHT, bgcolor=STATES["idle"][2],
                     animate=ft.Animation(int(FRAME_SECONDS * 1000), ft.AnimationCurve.EASE_OUT))
        for _ in range(BAR_COUNT)
    ]
    hint = ft.Text(STATES["idle"][1], size=10, color=TEXT_DIM, max_lines=1,
                   overflow=ft.TextOverflow.ELLIPSIS, style=ft.TextStyle(letter_spacing=1))

    # Aktifken panelin içinde yukarıdan aşağı inen ince tarama çizgisi
    scan_line = ft.Container(
        left=0, right=0, top=0, height=2, bgcolor=tint(CYAN, 0.0),
        animate_position=ft.Animation(int(FRAME_SECONDS * 1000), ft.AnimationCurve.LINEAR),
    )
    wave_frame = ft.Container(
        content=ft.Stack(
            [
                ft.Container(
                    left=0, right=0, top=0, bottom=0,
                    content=ft.Column(
                        [
                            ft.Row(bars, spacing=3, height=BAR_MAX_HEIGHT,
                                   alignment=ft.MainAxisAlignment.CENTER,
                                   vertical_alignment=ft.CrossAxisAlignment.CENTER),
                            hint,
                        ],
                        spacing=6,
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ),
                scan_line,
                *brackets(),
            ],
        ),
        height=WAVE_HEIGHT,
        bgcolor=tint(PANEL, 0.7),
        border=ft.Border.all(1, tint(CYAN, 0.0)),
        animate=SMOOTH,
    )

    # ─── Camera panel (only while CAM is on) ───
    camera_image = ft.Image(src=b"", width=PREVIEW_WIDTH, height=PREVIEW_HEIGHT,
                            fit=ft.BoxFit.COVER, gapless_playback=True)
    camera_live = ft.Text("● LIVE", size=9, weight=ft.FontWeight.W_700, color=RED)
    gesture_name = ft.Text("NO HAND", size=17, weight=ft.FontWeight.W_700, color=TEXT_DIM,
                           style=ft.TextStyle(letter_spacing=1))
    gesture_hold = ft.ProgressBar(value=0, color=CYAN, bgcolor=tint(CYAN, 0.12), bar_height=3)
    def legend_row(icon, note, action):
        return ft.Row(
            [
                ft.Text(icon, size=12, width=30, no_wrap=True),
                ft.Text(action.upper(), size=10, color=TEXT_PRIMARY, weight=ft.FontWeight.W_600, no_wrap=True),
                ft.Text(note, size=9, color=TEXT_DIM, no_wrap=True),
            ],
            spacing=3,
        )

    # İki sütun: panel kısa kalsın, konuşma alanından yer çalmasın
    half = (len(GESTURE_LEGEND) + 1) // 2
    legend = ft.Row(
        [
            ft.Column([legend_row(*item) for item in GESTURE_LEGEND[:half]], spacing=2, expand=True),
            ft.Column([legend_row(*item) for item in GESTURE_LEGEND[half:]], spacing=2, expand=True),
        ],
        spacing=4,
        vertical_alignment=ft.CrossAxisAlignment.START,
    )
    camera_panel = ft.Container(
        content=ft.Row(
            [
                ft.Stack(
                    [
                        camera_image,
                        ft.Container(content=camera_live, left=6, top=5),
                        *brackets(GREEN, 12),
                    ],
                    width=PREVIEW_WIDTH, height=PREVIEW_HEIGHT,
                ),
                ft.Column(
                    [
                        ft.Text("GESTURE", size=9, color=TEXT_DIM, style=ft.TextStyle(letter_spacing=2)),
                        gesture_name,
                        gesture_hold,
                        ft.Container(height=2),
                        legend,
                    ],
                    spacing=3,
                    expand=True,
                ),
            ],
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.START,
        ),
        padding=8,
        bgcolor=tint(PANEL, 0.8),
        border=ft.Border.all(1, tint(GREEN, 0.4)),
        visible=False,
    )

    # ─── Log ───
    empty_state = ft.Container(
        content=ft.Text("NO ACTIVITY. AWAITING INPUT.", size=11, color=TEXT_DIM),
        padding=ft.Padding.only(top=60),
        alignment=ft.Alignment.CENTER,
    )
    log = ft.ListView(
        controls=[empty_state],
        spacing=8,
        expand=True,
        padding=ft.Padding.symmetric(vertical=10),
    )

    def make_entry(role, text, when=None, image=None):
        tag, tag_color, text_color = LOG_STYLES[role]
        label = ft.Text(text, size=14, color=text_color, selectable=True,
                        style=ft.TextStyle(height=1.4))
        body = [label]
        if image:
            # Remy'nin "what is it?" cevabını verirken baktığı fotoğraf
            body.append(ft.Image(src=image, height=130, fit=ft.BoxFit.CONTAIN, border_radius=2))
        entry = ft.Container(
            content=ft.Row(
                [
                    ft.Column(
                        [
                            ft.Text(tag, size=11, weight=ft.FontWeight.W_700, color=tag_color),
                            ft.Text(stamp(when), size=9, color=TEXT_DIM),
                        ],
                        spacing=1,
                        tight=True,
                    ),
                    ft.Column(body, spacing=6, expand=True, tight=True),
                ],
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.START,
            ),
            padding=ft.Padding.only(left=12, right=12, top=9, bottom=9),
            border=ft.Border.only(left=ft.BorderSide(2, tag_color)),
            bgcolor=tint(tag_color, 0.07) if role == "user" else tint(PANEL, 0.6),
        )
        entry.data = label
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
    def hud_button(text, color=CYAN, icon=None, on_click=None, expand=False):
        label = ft.Text(text, size=11, weight=ft.FontWeight.W_700, color=color,
                        style=ft.TextStyle(letter_spacing=1))
        icon_control = ft.Icon(icon, size=15, color=color) if icon else None
        button = ft.Container(
            content=ft.Row([c for c in (icon_control, label) if c], spacing=6, tight=True,
                           alignment=ft.MainAxisAlignment.CENTER),
            height=36,
            expand=expand,
            alignment=ft.Alignment.CENTER,
            padding=ft.Padding.symmetric(horizontal=10),
            border=ft.Border.all(1, tint(color, 0.55)),
            bgcolor=tint(color, 0.06),
            ink=True,
            on_click=on_click,
            animate=SMOOTH,
        )
        button.data = {"label": label, "icon": icon_control}
        return button

    def paint_toggle(button, name, active, on_icon, off_icon):
        """ON: green with a soft glow. OFF: dim."""
        color = GREEN if active else TEXT_DIM
        parts = button.data
        parts["label"].value = f"{name} {'ON' if active else 'OFF'}"
        parts["label"].color = color
        parts["icon"].icon = on_icon if active else off_icon
        parts["icon"].color = color
        button.border = ft.Border.all(1, tint(color, 0.6 if active else 0.35))
        button.bgcolor = tint(color, 0.1 if active else 0.03)
        button.shadow = ft.BoxShadow(blur_radius=12, color=tint(GREEN, 0.25)) if active else None

    voice_button = hud_button("VOICE OFF", TEXT_DIM, ft.Icons.MIC_OFF, expand=True)
    camera_button = hud_button("CAM OFF", TEXT_DIM, ft.Icons.VIDEOCAM_OFF, expand=True)
    tools_button = hud_button("TOOLS", CYAN, ft.Icons.TUNE, expand=True)
    stop_button = hud_button("STOP", RED, ft.Icons.STOP_CIRCLE, expand=True)
    stop_button.visible = False

    def on_state(state):
        current["state"] = state
        if state in STATES:
            tag, text, color, _ = STATES[state]
            state_tag.value = tag
            hint.value = text
            hint.color = TEXT_DIM
        else:
            tag, color = "ERROR", RED
            state_tag.value = tag
            hint.value = state[:70].upper()
            hint.color = RED
        state_tag.color = color
        state_dot.bgcolor = color
        state_chip.border = ft.Border.all(1, tint(color, 0.5))
        for bar in bars:
            bar.bgcolor = color

        # Aktif durumlarda panel durum renginde hafifçe parlar
        active_state = state in STATES and state != "idle"
        wave_frame.border = ft.Border.all(1, tint(color, 0.45 if active_state else 0.0))
        wave_frame.shadow = ft.BoxShadow(blur_radius=22, color=tint(color, 0.22)) if active_state else None
        scan_line.bgcolor = tint(color, 0.35 if active_state else 0.0)

        stop_button.visible = state in BUSY_STATES
        paint_toggle(voice_button, "VOICE", service.voice_active, ft.Icons.MIC, ft.Icons.MIC_OFF)
        refresh()

    service = RemyService(on_state=on_state, on_message=on_message, on_sentence=on_sentence)

    def on_snapshot(jpeg):
        append_entry("tool", "What Remy saw:", image=jpeg)
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
        paint_toggle(camera_button, "CAM", active, ft.Icons.VIDEOCAM, ft.Icons.VIDEOCAM_OFF)
        camera_panel.visible = active
        if not active:
            camera_image.src = b""
            gesture_name.value = "NO HAND"
            gesture_name.color = TEXT_DIM
            gesture_hold.value = 0

    def on_camera_preview(jpeg, label, progress):
        camera_image.src = jpeg
        if label:
            gesture_name.value = f"{GESTURE_ICONS.get(label, '')} {label}"
            gesture_name.color = GREEN if progress >= 1 else CYAN
        else:
            gesture_name.value = "NO HAND"
            gesture_name.color = TEXT_DIM
        gesture_hold.value = progress
        refresh()

    def on_gesture(action):
        if action in ("wake", "done") and not service.voice_active:
            message = "Turn voice on to use this gesture"
        else:
            message = GESTURE_HINTS[action]
        hint.value = message.upper()
        hint.color = CYAN
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

    # ─── Waveform, scan line and clock ───
    # Dalga durumu gösteren bir animasyon, gerçek mikrofon seviyesi değil
    def animation_loop():
        rng = random.Random()
        phase = 0.0
        flat = False
        scan = 0
        while True:
            state = current["state"]
            level = STATES[state][3] if state in STATES else 0.0
            clock.value = datetime.now().strftime("%H:%M:%S")

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

            scan = (scan + SCAN_STEP) % (WAVE_HEIGHT - 2)
            scan_line.top = scan
            refresh()
            time.sleep(FRAME_SECONDS)

    threading.Thread(target=animation_loop, daemon=True).start()

    # ─── Dialogs for tools that need input ───
    def open_form(title, fields, submit_label, on_submit, extra_actions=None):
        def submit(e):
            page.pop_dialog()
            on_submit()

        actions = [ft.TextButton("CANCEL", on_click=lambda e: page.pop_dialog())]
        actions += extra_actions or []
        actions.append(ft.FilledButton(
            submit_label.upper(), on_click=submit, bgcolor=CYAN, color=VOID,
            style=ft.ButtonStyle(shape=SQUARE),
        ))
        page.show_dialog(ft.AlertDialog(
            title=ft.Text(title.upper(), size=14, weight=ft.FontWeight.W_700, color=CYAN,
                          style=ft.TextStyle(letter_spacing=2)),
            content=ft.Column(fields, tight=True, spacing=12, width=320),
            actions=actions,
            bgcolor=PANEL,
            shape=ft.RoundedRectangleBorder(radius=2, side=ft.BorderSide(1, LINE)),
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
                           active_color=CYAN, thumb_color=CYAN)

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
            ft.TextButton("MUTE", on_click=quiet("mute", "Volume")),
            ft.TextButton("UNMUTE", on_click=quiet("unmute", "Volume")),
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

    def tool_key(text, tooltip, icon, handler):
        key = hud_button(text, TEXT_DIM, icon, on_click=handler, expand=True)
        key.tooltip = tooltip
        return key

    # Araçlar varsayılan olarak gizli, ekranı kalabalık etmesin
    tools_panel = ft.Column(
        [
            ft.Row(
                [
                    tool_key("TIME", "Time", ft.Icons.SCHEDULE, quick("Time", "get_time")),
                    tool_key("DATE", "Date", ft.Icons.EVENT, quick("Date", "get_date")),
                    tool_key("WEB", "Web", ft.Icons.PUBLIC, web_action),
                    tool_key("PDF", "PDF", ft.Icons.DESCRIPTION, pdf_action),
                    tool_key("MAIL", "Mail", ft.Icons.MAIL_OUTLINE, quick("Mail", "read_email")),
                ],
                spacing=6,
            ),
            ft.Row(
                [
                    tool_key("SCRN", "Screen", ft.Icons.MONITOR, quick("Screen", "analyze_screen")),
                    tool_key("VOL", "Volume", ft.Icons.VOLUME_UP, volume_action),
                    tool_key("BRGT", "Bright", ft.Icons.LIGHT_MODE, brightness_action),
                    tool_key("ALRM", "Alarm", ft.Icons.ALARM, alarm_action),
                    tool_key("RMND", "Remind", ft.Icons.NOTIFICATIONS_NONE, reminder_action),
                ],
                spacing=6,
            ),
        ],
        spacing=6,
        visible=False,
    )

    def toggle_tools(e):
        tools_panel.visible = not tools_panel.visible
        parts = tools_button.data
        parts["label"].value = "CLOSE" if tools_panel.visible else "TOOLS"
        parts["icon"].icon = ft.Icons.CLOSE if tools_panel.visible else ft.Icons.TUNE
        refresh_and_scroll()

    tools_button.on_click = toggle_tools

    # ─── Command line ───
    composer = ft.TextField(
        hint_text="enter command",
        hint_style=ft.TextStyle(color=TEXT_DIM),
        color=TEXT_PRIMARY,
        cursor_color=CYAN,
        border=ft.InputBorder.NONE,
        content_padding=ft.Padding.symmetric(horizontal=2, vertical=10),
        text_size=13,
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

    command_line = ft.Container(
        content=ft.Row(
            [
                ft.Text(">", size=14, weight=ft.FontWeight.W_700, color=CYAN),
                composer,
                hud_button("SEND", CYAN, ft.Icons.SEND, on_click=send),
            ],
            spacing=8,
        ),
        padding=ft.Padding.only(left=12, right=5, top=4, bottom=4),
        border=ft.Border.all(1, LINE),
        bgcolor=tint(PANEL, 0.85),
    )

    layout = ft.Column(
        [
            top_bar,
            ft.Container(
                content=ft.Column(
                    [
                        wave_frame,
                        camera_panel,
                        log,
                        ft.Row([voice_button, camera_button, tools_button, stop_button], spacing=6),
                        tools_panel,
                        command_line,
                    ],
                    spacing=10,
                    expand=True,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                ),
                padding=ft.Padding.only(left=14, right=14, top=14, bottom=14),
                expand=True,
            ),
        ],
        spacing=0,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
    )

    page.add(ft.Container(
        content=layout,
        bgcolor=VOID,
        image=ft.DecorationImage(src="hud_bg.png", fit=ft.BoxFit.COVER),
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
