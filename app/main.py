import flet as ft
from services.remy_service import (
    voice_chat, run_tool,
    start_wake_word_loop, stop_wake_word_loop
)


def main(page: ft.Page):
    page.title = "Remy"
    page.theme_mode = ft.ThemeMode.DARK
    page.window_width = 500
    page.window_height = 850
    page.bgcolor = "#0A0E1A"
    page.padding = 0

    # Durum
    status_text = ft.Text("Beklemede", size=14, color="#94A3B8")
    result_text = ft.Text("", size=13, color="#F1F5F9", text_align=ft.TextAlign.CENTER)

    # Callback'ler
    def on_result(user_text, reply):
        result_text.value = f"Sen: {user_text}\nRemy: {reply}"
        page.update()

    def on_status(status):
        status_text.value = status
        page.update()

    # State
    is_listening = {"value": False}

    # Mikrofon
    mic_button = ft.Container(
        content=ft.Icon(ft.Icons.MIC, size=44, color="#FFFFFF"),
        width=110,
        height=110,
        bgcolor="#6366F1",
        border_radius=55,
        alignment=ft.Alignment.CENTER,
        ink=True,
    )

    def toggle_listening(e):
        if is_listening["value"]:
            stop_wake_word_loop()
            is_listening["value"] = False
            mic_button.bgcolor = "#6366F1"
            status_text.value = "Beklemede"
        else:
            start_wake_word_loop(on_result=on_result, on_status=on_status)
            is_listening["value"] = True
            mic_button.bgcolor = "#EF4444"
            status_text.value = "🎤 'Hey Jarvis' de..."
        page.update()

    mic_button.on_click = toggle_listening

    # Araç butonları
    def tool_button(icon, label, tool_name):
        return ft.Container(
            content=ft.Column([
                ft.Icon(icon, size=24, color="#F1F5F9"),
                ft.Text(label, size=11, color="#94A3B8"),
            ], spacing=4, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            width=90,
            height=80,
            bgcolor=ft.Colors.with_opacity(0.8, "#1E293B"),
            border_radius=16,
            alignment=ft.Alignment.CENTER,
            on_click=lambda e: run_tool(
                tool_name,
                on_result=lambda n, r: on_status(f"{n}: {r[:80]}"),
                on_status=on_status
            ),
            ink=True,
        )

    tools_grid = ft.Row([
        tool_button(ft.Icons.ACCESS_TIME, "Zaman", "get_time"),
        tool_button(ft.Icons.CALENDAR_TODAY, "Tarih", "get_date"),
        tool_button(ft.Icons.PICTURE_AS_PDF, "PDF", "read_pdf"),
        tool_button(ft.Icons.LANGUAGE, "Web", "web_search"),
        tool_button(ft.Icons.EMAIL, "Mail", "read_email"),
        tool_button(ft.Icons.SCREENSHOT_MONITOR, "Ekran", "analyze_screen"),
        tool_button(ft.Icons.VOLUME_UP, "Ses", "unmute"),
        tool_button(ft.Icons.VOLUME_OFF, "Sustur", "mute"),
        tool_button(ft.Icons.LIGHT_MODE, "Parlaklık", "set_brightness"),
        tool_button(ft.Icons.ALARM, "Alarm", "set_alarm"),
    ], wrap=True, spacing=8, run_spacing=8, alignment=ft.MainAxisAlignment.CENTER)

    # İçerik
    content = ft.Column([
        ft.Container(height=40),
        ft.Text("🤖", size=60),
        ft.Text("Remy", size=32, weight=ft.FontWeight.BOLD, color="#F1F5F9"),
        ft.Text("AI Voice Assistant", size=14, color="#94A3B8"),
        ft.Container(height=40),
        mic_button,
        ft.Container(height=20),
        status_text,
        ft.Container(height=20),
        result_text,
        ft.Container(height=40),
        ft.Text("🛠️ Araçlar", size=16, weight=ft.FontWeight.BOLD, color="#F1F5F9"),
        ft.Container(height=10),
        tools_grid,
    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8, scroll=ft.ScrollMode.AUTO)

    # Gradient arka plan
    page.add(
        ft.Container(
            content=content,
            expand=True,
            padding=20,
            gradient=ft.LinearGradient(
                begin=ft.Alignment.TOP_LEFT,
                end=ft.Alignment.BOTTOM_RIGHT,
                colors=["#0A0E1A", "#1E1B4B", "#312E81"],
            ),
        ),
    )


ft.run(main)