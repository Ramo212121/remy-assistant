"""Remy for Android: tap the mic, talk, tap again. Run on a computer with `flet run src/main.py` (text only)."""
import asyncio
import io
import wave

import flet as ft

from remy_mobile import groq_api
from remy_mobile.brain import Brain
from remy_mobile.storage import Store, temp_dir

# ─────────────────────────────────────────
# HUD PALETTE (masaüstü uygulamasıyla aynı)
# ─────────────────────────────────────────
VOID = "#03070B"
PANEL = "#07121A"
TEXT_PRIMARY = "#D8F3F8"
TEXT_DIM = "#7FA6B4"
CYAN = "#22E3F5"
GREEN = "#3DFFA2"
AMBER = "#FFB72B"
RED = "#FF4D5E"
FONT = "monospace"

VOICES = ["troy", "hannah", "austin"]
KEYS_URL = "https://console.groq.com/keys"
VOICE_TERMS_URL = "https://console.groq.com/playground?model=canopylabs%2Forpheus-v1-english"
RECORDING_NAME = "remy_command.wav"

# state → (tag, hint, color)
STATES = {
    "idle": ("READY", "TAP THE MIC OR TYPE A COMMAND", TEXT_DIM),
    "listening": ("LISTENING", "TAP THE MIC AGAIN WHEN YOU'RE DONE", GREEN),
    "hearing": ("HEARING", "TURNING YOUR VOICE INTO TEXT", AMBER),
    "thinking": ("THINKING", "WORKING ON IT", AMBER),
    "speaking": ("SPEAKING", "TAP STOP TO INTERRUPT", CYAN),
}
LOG_STYLES = {
    "user": ("USR", CYAN, "#FFFFFF"),
    "remy": ("RMY", GREEN, TEXT_PRIMARY),
    "sys": ("SYS", AMBER, AMBER),
}
MAX_ENTRIES = 80


def tint(color, opacity):
    return ft.Colors.with_opacity(opacity, color)


LINE = tint(CYAN, 0.28)


def wav_seconds(data):
    try:
        with wave.open(io.BytesIO(data)) as clip:
            return clip.getnframes() / float(clip.getframerate())
    except (wave.Error, EOFError, ZeroDivisionError):
        return 10.0


async def main(page: ft.Page):
    page.title = "Remy"
    page.bgcolor = VOID
    page.padding = 0
    page.spacing = 0
    page.theme_mode = ft.ThemeMode.DARK
    page.dark_theme = ft.Theme(color_scheme_seed=CYAN)

    store = Store()
    loop = asyncio.get_running_loop()
    on_phone = page.platform in (ft.PagePlatform.ANDROID, ft.PagePlatform.IOS)

    launcher = ft.UrlLauncher()
    page.services.append(launcher)

    def open_url(url):
        # Beyin arka plan thread'inde çalışıyor; tarayıcıyı ana döngüde açtırıyoruz
        asyncio.run_coroutine_threadsafe(launcher.launch_url(url), loop)

    brain = Brain(store, open_url)

    recorder = None
    permissions = None
    if on_phone:
        import flet_audio_recorder as far
        import flet_permission_handler as fph
        recorder = far.AudioRecorder()
        permissions = fph.PermissionHandler()
        page.services.append(recorder)
        page.services.append(permissions)

    session = {
        "state": "idle",
        "generation": 0,   # STOP her bastığında artar; eski cümleler okunmaz
        "busy": False,
        "recording": False,
        "voice_blocked": False,
        "live": None,
        "player": None,
    }
    sentences = asyncio.Queue()
    clips = asyncio.Queue()

    def refresh():
        try:
            page.update()
        except Exception as e:
            print(f"UI update skipped: {e}")

    # ─── Top bar ───
    state_dot = ft.Container(width=6, height=6, bgcolor=TEXT_DIM)
    state_tag = ft.Text("READY", size=11, weight=ft.FontWeight.W_700, color=TEXT_DIM, font_family=FONT,
                        style=ft.TextStyle(letter_spacing=1.5))
    settings_button = ft.IconButton(ft.Icons.TUNE, icon_color=TEXT_DIM, icon_size=20, tooltip="Settings")
    top_bar = ft.Container(
        content=ft.Row(
            [
                ft.Text("REMY", size=15, weight=ft.FontWeight.W_700, color=CYAN, font_family=FONT,
                        style=ft.TextStyle(letter_spacing=6)),
                ft.Container(expand=True),
                state_dot,
                state_tag,
                settings_button,
            ],
            spacing=8,
        ),
        padding=ft.Padding.only(left=16, right=4, top=10, bottom=4),
        border=ft.Border.only(bottom=ft.BorderSide(1, LINE)),
    )

    # ─── Log ───
    empty_state = ft.Container(
        content=ft.Text("NO ACTIVITY. TAP THE MIC.", size=11, color=TEXT_DIM, font_family=FONT),
        padding=ft.Padding.only(top=60),
        alignment=ft.Alignment.CENTER,
    )
    log = ft.ListView(controls=[empty_state], spacing=6, expand=True, padding=ft.Padding.symmetric(vertical=10))

    def make_entry(role, text):
        tag, tag_color, text_color = LOG_STYLES[role]
        label = ft.Text(text, size=14, color=text_color, selectable=True, expand=True)
        entry = ft.Container(
            content=ft.Row(
                [ft.Text(tag, size=11, weight=ft.FontWeight.W_700, color=tag_color, font_family=FONT), label],
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.START,
            ),
            padding=ft.Padding.symmetric(horizontal=10, vertical=8),
            border=ft.Border.only(left=ft.BorderSide(2, tag_color)),
            bgcolor=tint(tag_color, 0.06) if role == "user" else tint(PANEL, 0.75),
        )
        entry.data = label
        return entry

    def add_entry(role, text):
        if empty_state in log.controls:
            log.controls.remove(empty_state)
        entry = make_entry(role, text)
        log.controls.append(entry)
        del log.controls[:-MAX_ENTRIES]
        return entry

    async def scroll_to_end():
        await asyncio.sleep(0.1)
        await log.scroll_to(offset=-1, duration=150)

    def show(role, text):
        add_entry(role, text)
        refresh()
        page.run_task(scroll_to_end)

    # ─── State ───
    hint = ft.Text(STATES["idle"][1], size=10, color=TEXT_DIM, font_family=FONT, text_align=ft.TextAlign.CENTER,
                   style=ft.TextStyle(letter_spacing=1))
    mic_icon = ft.Icon(ft.Icons.MIC, size=34, color=VOID)
    mic_button = ft.Container(
        content=mic_icon,
        width=78, height=78, border_radius=39,
        alignment=ft.Alignment.CENTER,
        bgcolor=CYAN if on_phone else tint(TEXT_DIM, 0.4),
        ink=True,
        tooltip="Talk" if on_phone else "The mic works in the Android app",
        animate=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
    )
    stop_button = ft.Container(
        content=ft.Text("STOP", size=12, weight=ft.FontWeight.W_700, color=RED, font_family=FONT),
        padding=ft.Padding.symmetric(horizontal=16, vertical=9),
        border=ft.Border.all(1, tint(RED, 0.6)),
        bgcolor=tint(RED, 0.08),
        ink=True,
        visible=False,
    )

    def set_state(name):
        session["state"] = name
        tag, text, color = STATES[name]
        state_tag.value = tag
        state_tag.color = color
        state_dot.bgcolor = color
        hint.value = text
        hint.color = TEXT_DIM
        listening = name == "listening"
        mic_icon.icon = ft.Icons.STOP if listening else ft.Icons.MIC
        if on_phone:
            mic_button.bgcolor = GREEN if listening else CYAN
        stop_button.visible = name in ("thinking", "speaking")
        refresh()

    def settle():
        """Pick the resting state once nothing is left to do."""
        if session["recording"]:
            return
        if session["busy"]:
            set_state("thinking")
        elif session["player"] is not None or not clips.empty() or not sentences.empty():
            set_state("speaking")
        else:
            set_state("idle")

    def notify(text):
        show("sys", text)

    # ─── Speaking: one task makes audio, the other plays it, so the next sentence is ready in time ───
    def speaking_enabled():
        return (on_phone and store.settings.get("speak_replies")
                and store.settings.get("api_key") and not session["voice_blocked"])

    async def synth_worker():
        while True:
            generation, text = await sentences.get()
            if generation != session["generation"]:
                continue
            try:
                clip = await asyncio.to_thread(
                    groq_api.speech, store.settings["api_key"], text, store.settings.get("voice", "troy")
                )
            except groq_api.GroqError as e:
                if e.code == "model_terms_required":
                    session["voice_blocked"] = True
                    notify("Voice replies need a one-time step: open Settings and tap ACCEPT VOICE TERMS. Replies stay as text until then.")
                else:
                    print(f"Speech error: {e}")
                settle()
                continue
            if generation == session["generation"]:
                await clips.put((generation, clip))

    async def play_worker():
        import flet_audio as fa
        while True:
            generation, clip = await clips.get()
            if generation != session["generation"]:
                continue
            finished = asyncio.Event()

            def on_state_change(e):
                if e.state in (fa.AudioState.COMPLETED, fa.AudioState.STOPPED):
                    loop.call_soon_threadsafe(finished.set)

            player = fa.Audio(src=clip, autoplay=True, on_state_change=on_state_change)
            session["player"] = player
            set_state("speaking")
            page.services.append(player)
            refresh()
            try:
                await asyncio.wait_for(finished.wait(), timeout=wav_seconds(clip) + 3)
            except asyncio.TimeoutError:
                pass
            await release(player)
            settle()

    async def release(player):
        if session["player"] is player:
            session["player"] = None
        try:
            await player.release()
        except Exception as e:
            print(f"Audio release skipped: {e}")
        if player in page.services:
            page.services.remove(player)

    if on_phone:
        page.run_task(synth_worker)
        page.run_task(play_worker)

    def drain(queue):
        while not queue.empty():
            queue.get_nowait()

    async def stop_everything(e=None):
        session["generation"] += 1
        drain(sentences)
        drain(clips)
        player = session["player"]
        if player is not None:
            await release(player)
        settle()

    stop_button.on_click = stop_everything

    # ─── Thinking ───
    def on_sentence(generation, sentence):
        live = session["live"]
        if live is None:
            session["live"] = add_entry("remy", sentence)
        else:
            live.data.value = f"{live.data.value} {sentence}"
        refresh()
        page.run_task(scroll_to_end)
        if speaking_enabled() and generation == session["generation"]:
            sentences.put_nowait((generation, sentence))

    async def ask(text):
        if session["busy"]:
            return
        await stop_everything()
        session["busy"] = True
        session["live"] = None
        generation = session["generation"]
        show("user", text)
        set_state("thinking")

        def sentence_from_thread(sentence):
            loop.call_soon_threadsafe(on_sentence, generation, sentence)

        reply = await asyncio.to_thread(
            brain.respond, text, sentence_from_thread, lambda: generation != session["generation"]
        )
        await asyncio.sleep(0)
        live = session["live"]
        if live is not None and reply:
            live.data.value = reply
        session["live"] = None
        session["busy"] = False
        settle()

    # ─── Listening ───
    async def ensure_microphone():
        import flet_permission_handler as fph
        status = await permissions.request(fph.Permission.MICROPHONE)
        if status == fph.PermissionStatus.GRANTED:
            return True
        notify("Remy needs microphone access. Allow it in Android Settings → Apps → Remy → Permissions.")
        return False

    async def toggle_mic(e):
        if not on_phone:
            notify("The microphone works in the Android app. Type here to test.")
            return
        if not store.settings.get("api_key"):
            notify("Add your Groq API key in Settings first.")
            open_settings()
            return
        if session["busy"]:
            return

        if not session["recording"]:
            await stop_everything()
            if not await ensure_microphone():
                return
            import flet_audio_recorder as far
            path = str(temp_dir() / RECORDING_NAME)
            # Flet mutlak yolu sadece dosya zaten varsa olduğu gibi kullanıyor;
            # yoksa başına assets klasörünü ekliyor ve kayıt açılamıyor
            open(path, "wb").close()
            started = await recorder.start_recording(
                output_path=path,
                configuration=far.AudioRecorderConfiguration(
                    encoder=far.AudioEncoder.WAV, sample_rate=16000, channels=1,
                    auto_gain=True, suppress_noise=True,
                ),
            )
            if not started:
                notify("Couldn't start the microphone.")
                return
            session["recording"] = True
            set_state("listening")
            return

        session["recording"] = False
        path = await recorder.stop_recording()
        set_state("hearing")
        try:
            audio = await asyncio.to_thread(lambda: open(path, "rb").read())
            text = await asyncio.to_thread(groq_api.transcribe, store.settings["api_key"], audio, RECORDING_NAME)
        except (OSError, TypeError, groq_api.GroqError) as error:
            print(f"Transcription error: {error}")
            notify("I couldn't hear that. Try again.")
            settle()
            return
        if text.strip():
            await ask(text.strip())
        else:
            settle()

    mic_button.on_click = toggle_mic

    # ─── Typing ───
    composer = ft.TextField(
        hint_text="enter command",
        hint_style=ft.TextStyle(color=TEXT_DIM),
        color=TEXT_PRIMARY,
        cursor_color=CYAN,
        border=ft.InputBorder.NONE,
        content_padding=ft.Padding.symmetric(horizontal=2, vertical=10),
        text_size=14,
        dense=True,
        expand=True,
    )

    async def send(e):
        text = (composer.value or "").strip()
        if not text:
            return
        composer.value = ""
        refresh()
        await ask(text)

    composer.on_submit = send
    command_line = ft.Container(
        content=ft.Row(
            [
                ft.Text(">", size=14, weight=ft.FontWeight.W_700, color=CYAN, font_family=FONT),
                composer,
                ft.IconButton(ft.Icons.ARROW_UPWARD, icon_color=CYAN, icon_size=20, on_click=send, tooltip="Send"),
            ],
            spacing=6,
        ),
        padding=ft.Padding.only(left=12, right=2),
        border=ft.Border.all(1, LINE),
        bgcolor=tint(PANEL, 0.9),
    )

    # ─── Settings ───
    def open_settings(e=None):
        key_field = ft.TextField(
            label="Groq API key", value=store.settings.get("api_key", ""), password=True,
            can_reveal_password=True, border=ft.OutlineInputBorder(border_radius=2),
        )
        voice_field = ft.Dropdown(
            label="Voice", value=store.settings.get("voice", "troy"),
            options=[ft.DropdownOption(v) for v in VOICES], border=ft.OutlineInputBorder(border_radius=2),
        )
        speak_field = ft.Switch(label="Speak replies", value=bool(store.settings.get("speak_replies")), active_color=CYAN)

        def save(event):
            store.settings["api_key"] = (key_field.value or "").strip()
            store.settings["voice"] = voice_field.value or "troy"
            store.settings["speak_replies"] = bool(speak_field.value)
            session["voice_blocked"] = False
            store.save()
            page.pop_dialog()
            notify("Settings saved.")

        def forget(event):
            brain.forget()
            log.controls[:] = [empty_state]
            page.pop_dialog()
            refresh()

        def link(label, url):
            return ft.TextButton(label, on_click=lambda event: page.run_task(launcher.launch_url, url))

        page.show_dialog(ft.AlertDialog(
            title=ft.Text("SETTINGS", size=14, weight=ft.FontWeight.W_700, color=CYAN, font_family=FONT),
            content=ft.Column(
                [
                    key_field,
                    link("GET A FREE KEY", KEYS_URL),
                    voice_field,
                    speak_field,
                    link("ACCEPT VOICE TERMS", VOICE_TERMS_URL),
                    ft.Text("The key is stored only on this phone.", size=12, color=TEXT_DIM),
                ],
                tight=True, spacing=10, width=320,
            ),
            actions=[
                ft.TextButton("FORGET CHAT", on_click=forget),
                ft.TextButton("CANCEL", on_click=lambda event: page.pop_dialog()),
                ft.FilledButton("SAVE", on_click=save, bgcolor=CYAN, color=VOID,
                                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=2))),
            ],
            bgcolor=PANEL,
            shape=ft.RoundedRectangleBorder(radius=2, side=ft.BorderSide(1, LINE)),
        ))

    settings_button.on_click = open_settings

    # ─── Layout ───
    page.add(ft.SafeArea(
        expand=True,
        content=ft.Container(
            expand=True,
            bgcolor=VOID,
            image=ft.DecorationImage(src="hud_bg.png", fit=ft.BoxFit.COVER),
            content=ft.Column(
                [
                    top_bar,
                    ft.Container(content=log, expand=True, padding=ft.Padding.symmetric(horizontal=12)),
                    ft.Container(
                        content=ft.Column(
                            [
                                hint,
                                ft.Row([mic_button, stop_button], alignment=ft.MainAxisAlignment.CENTER, spacing=14),
                                command_line,
                            ],
                            spacing=10,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        padding=ft.Padding.only(left=12, right=12, top=8, bottom=12),
                    ),
                ],
                spacing=0,
                expand=True,
            ),
        ),
    ))

    for message in store.history[-20:]:
        if message.get("content"):
            add_entry("user" if message["role"] == "user" else "remy", message["content"])
    refresh()
    page.run_task(scroll_to_end)

    if not store.settings.get("api_key"):
        notify("Welcome. Open Settings (top right) and paste your Groq API key to start.")


if __name__ == "__main__":
    ft.run(main, assets_dir="assets")
