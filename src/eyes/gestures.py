"""Hand gestures from the Mac's camera. Frames are processed on this machine; none are stored or sent."""
import collections
import math
import threading
import time
import urllib.request

from src.config import GESTURE_MODEL

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/gesture_recognizer/"
    "gesture_recognizer/float16/latest/gesture_recognizer.task"
)
FRAME_SECONDS = 1 / 15       # model kare başına ~14 ms; 15 fps yeterli ve işlemciyi yormaz
PREVIEW_SECONDS = 0.25       # arayüze saniyede 4 küçük önizleme
PROCESS_WIDTH = 320
MAX_READ_FAILURES = 50
SNAPSHOT_SECONDS = 0.5      # "what is it?" için son kare bu sıklıkla saklanır
SNAPSHOT_WIDTH = 640
SNAPSHOT_MAX_AGE = 2.0
SNAPSHOT_HISTORY = 12        # 12 × 0,5 sn = son 6 saniye
QUESTION_LEAD_SECONDS = 1.5  # cümle metne çevrilene kadar geçen süre; kare sorunun ortasından seçilir
CAMERA_HELP = "Allow camera access for the app you started Remy from: System Settings → Privacy & Security → Camera."

# MediaPipe hareket adı → Remy komutu
ACTIONS = {
    "Open_Palm": "wake",
    "Closed_Fist": "stop",
    "Thumb_Up": "done",
    "Pointing_Up": "volume_up",
    "Thumb_Down": "volume_down",
    "Victory": "repeat",
    "ILoveYou": "time",
}
LABELS = {
    "Open_Palm": "PALM", "Closed_Fist": "FIST", "Thumb_Up": "THUMB UP", "Pointing_Up": "POINT UP",
    "Thumb_Down": "THUMB DOWN", "Victory": "VICTORY", "ILoveYou": "LOVE",
}


# Hareket dizisi: avucu kısa açıp hemen yumruk yapmak
OPEN_CLOSE_ACTION = "open_chrome"


class GestureFilter:
    """Turns noisy per-frame guesses into single commands.

    A gesture must be held for `hold_seconds` (the palm for `wake_hold_seconds`),
    fires once per hold, and two commands are at least `cooldown_seconds` apart.

    Open-close: a short palm that didn't wake Remy, followed within
    `combo_window_seconds` by a fist, means OPEN_CLOSE_ACTION instead of "stop".
    The palm's longer hold is what keeps the two apart.
    """

    def __init__(self, hold_seconds=0.4, wake_hold_seconds=0.8, cooldown_seconds=1.5, min_score=0.6,
                 combo_window_seconds=1.0, combo_min_palm_seconds=0.15, combo_fist_seconds=0.2):
        self.hold_seconds = hold_seconds
        self.wake_hold_seconds = wake_hold_seconds
        self.cooldown_seconds = cooldown_seconds
        self.min_score = min_score
        self.combo_window_seconds = combo_window_seconds
        self.combo_min_palm_seconds = combo_min_palm_seconds
        self.combo_fist_seconds = combo_fist_seconds
        self._name = None
        self._since = 0.0
        self._fired = False
        self._last_fire = -math.inf
        self._palm_released_at = -math.inf
        self._palm_was_short = False

    def update(self, name, score, now):
        """Feed one frame's best guess. Returns an action name or None."""
        if name not in ACTIONS or score < self.min_score:
            name = None
        if name != self._name:
            if self._name == "Open_Palm":
                # Avuç bırakıldı: uyandırmadıysa ve çok kısa değilse aç-kapa'nın ilk yarısı olabilir
                self._palm_released_at = now
                self._palm_was_short = not self._fired and now - self._since >= self.combo_min_palm_seconds
            self._name, self._since, self._fired = name, now, False
        if name is None or self._fired:
            return None

        held = now - self._since
        open_close = (name == "Closed_Fist" and self._palm_was_short
                      and now - self._palm_released_at <= self.combo_window_seconds)
        if open_close:
            action = OPEN_CLOSE_ACTION if held >= self.combo_fist_seconds else None
        else:
            needed = self.wake_hold_seconds if name == "Open_Palm" else self.hold_seconds
            action = ACTIONS[name] if held >= needed else None

        if action is None or now - self._last_fire < self.cooldown_seconds:
            return None
        self._fired = True
        self._last_fire = now
        if action == OPEN_CLOSE_ACTION:
            self._palm_was_short = False
        return action

    def progress(self, now):
        """How far the current hold is towards firing, 0..1, for the UI."""
        if self._name is None or self._fired:
            return 0.0
        open_close = (self._name == "Closed_Fist" and self._palm_was_short
                      and now - self._palm_released_at <= self.combo_window_seconds)
        if open_close:
            needed = self.combo_fist_seconds
        elif self._name == "Open_Palm":
            needed = self.wake_hold_seconds
        else:
            needed = self.hold_seconds
        return min(1.0, (now - self._since) / needed)


# Kamera açıkken son kareler burada durur; sadece bellekte, diske yazılmaz
_snapshots = collections.deque(maxlen=SNAPSHOT_HISTORY)  # (monotonic time, jpeg)
_snapshot_lock = threading.Lock()
_question = {"time": None}


def _encode_snapshot(cv2, frame):
    height, width = frame.shape[:2]
    if width > SNAPSHOT_WIDTH:
        frame = cv2.resize(frame, (SNAPSHOT_WIDTH, int(height * SNAPSHOT_WIDTH / width)))
    ok, jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
    return jpeg.tobytes() if ok else None


def latest_frame(max_age=SNAPSHOT_MAX_AGE, at=None):
    """A frame from a running GestureWatcher: the one nearest `at` (a time.monotonic() value),
    or the newest. None if CAM is off or nothing is close enough."""
    with _snapshot_lock:
        frames = list(_snapshots)
    if not frames:
        return None
    if at is not None:
        taken, jpeg = min(frames, key=lambda frame: abs(frame[0] - at))
        return jpeg if abs(taken - at) <= max_age else None
    taken, jpeg = frames[-1]
    return jpeg if time.monotonic() - taken <= max_age else None


def mark_question():
    """Call right after a spoken question is transcribed, so the photo shows what was held up while asking."""
    _question["time"] = time.monotonic() - QUESTION_LEAD_SECONDS


def question_frame(max_wait=15.0):
    """The frame from while the last spoken question was asked; the newest frame for typed questions."""
    asked, _question["time"] = _question["time"], None
    if asked is not None and time.monotonic() - asked <= max_wait:
        frame = latest_frame(at=asked)
        if frame:
            return frame
    return latest_frame()


def capture_frame(camera_index=0, warmup_frames=10):
    """Open the camera for one picture when CAM is off. The first frames are dark, so skip a few."""
    import cv2
    camera = cv2.VideoCapture(camera_index)
    try:
        if not camera.isOpened():
            return None
        frame = None
        for _ in range(warmup_frames):
            ok, image = camera.read()
            if ok:
                frame = image
        return _encode_snapshot(cv2, frame) if frame is not None else None
    finally:
        camera.release()


def ensure_model():
    """Download the 8 MB model once."""
    if GESTURE_MODEL.exists() and GESTURE_MODEL.stat().st_size > 1_000_000:
        return GESTURE_MODEL
    GESTURE_MODEL.parent.mkdir(parents=True, exist_ok=True)
    partial = GESTURE_MODEL.with_suffix(".part")
    urllib.request.urlretrieve(MODEL_URL, partial)
    partial.replace(GESTURE_MODEL)
    return GESTURE_MODEL


class GestureWatcher:
    def __init__(self, on_action, on_preview=None, on_error=None, camera_index=0):
        """
        on_action(action): a value of ACTIONS
        on_preview(jpeg_bytes, label, progress): a small mirrored frame, what the model sees,
            and how far the current hold is towards firing (0..1)
        on_error(message): the camera or the model couldn't start
        """
        self._on_action = on_action
        self._on_preview = on_preview
        self._on_error = on_error
        self._camera_index = camera_index
        self._running = False
        self._thread = None

    @property
    def running(self):
        return self._running

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def _fail(self, message):
        print(f"⚠️ Camera: {message}")
        self._running = False
        if self._on_error:
            self._on_error(message)

    def _run(self):
        # Ağır kütüphaneler sadece kamera açılınca yüklenir
        import cv2
        import mediapipe as mp
        from mediapipe.tasks import python as mp_tasks
        from mediapipe.tasks.python import vision

        try:
            model = ensure_model()
        except OSError as e:
            self._fail(f"Couldn't download the gesture model: {e}")
            return

        recognizer = vision.GestureRecognizer.create_from_options(vision.GestureRecognizerOptions(
            base_options=mp_tasks.BaseOptions(model_asset_path=str(model)),
            running_mode=vision.RunningMode.VIDEO,
            num_hands=1,
        ))
        camera = cv2.VideoCapture(self._camera_index)
        if not camera.isOpened():
            recognizer.close()
            self._fail(f"Camera unavailable. {CAMERA_HELP}")
            return

        print("📷 Camera on: watching for gestures")
        gesture_filter = GestureFilter()
        started = time.monotonic()
        last_preview = 0.0
        failures = 0
        try:
            while self._running:
                tick = time.monotonic()
                ok, frame = camera.read()
                if not ok:
                    failures += 1
                    if failures > MAX_READ_FAILURES:
                        self._fail(f"Camera stopped sending frames. {CAMERA_HELP}")
                        break
                    time.sleep(0.1)
                    continue
                failures = 0

                # Ayna görüntüsü: sağ elini kaldırınca ekranda da sağda görünsün
                # Görsel model için aynalanmamış kare: üzerindeki yazılar düz okunsun
                if not _snapshots or tick - _snapshots[-1][0] >= SNAPSHOT_SECONDS:
                    jpeg = _encode_snapshot(cv2, frame)
                    if jpeg:
                        with _snapshot_lock:
                            _snapshots.append((tick, jpeg))

                frame = cv2.flip(frame, 1)
                height, width = frame.shape[:2]
                small = cv2.resize(frame, (PROCESS_WIDTH, int(height * PROCESS_WIDTH / width)))
                rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
                result = recognizer.recognize_for_video(
                    mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), int((tick - started) * 1000)
                )

                name, score = "None", 0.0
                if result.gestures and result.gestures[0]:
                    best = result.gestures[0][0]
                    name, score = best.category_name, best.score

                action = gesture_filter.update(name, score, tick)
                if action:
                    print(f"✋ Gesture: {name} → {action}")
                    self._on_action(action)

                if self._on_preview and tick - last_preview >= PREVIEW_SECONDS:
                    last_preview = tick
                    encoded, jpeg = cv2.imencode(".jpg", small, [cv2.IMWRITE_JPEG_QUALITY, 60])
                    if encoded:
                        self._on_preview(jpeg.tobytes(), LABELS.get(name, ""), gesture_filter.progress(tick))

                time.sleep(max(0.0, FRAME_SECONDS - (time.monotonic() - tick)))
        finally:
            with _snapshot_lock:
                _snapshots.clear()
            camera.release()
            recognizer.close()
            print("📷 Camera off")
