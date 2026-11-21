"""What's in front of the camera: one frame, described by a vision model."""
import base64

import groq

from src.config import VISION_MODEL, get_groq_client

PROMPT = (
    "This photo is from a Mac's camera. The person in it asked: {question}\n"
    "Focus on the object they hold up or point at, even if it's small or partly covered by their hand. "
    "Describe it in the third person in one or two short sentences, for example "
    "'A blue coffee mug held in the person's right hand.' No markdown or emojis. "
    "If no object is visible, say what is in front of the camera."
)
LOCAL_MODEL = "moondream"
_last = {"jpeg": None}


def last_frame():
    """The photo the last answer was based on, so the UI can show it."""
    return _last["jpeg"]


def describe(jpeg, question):
    """Ask Groq's vision model about one JPEG frame; fall back to local moondream if Groq is unreachable."""
    _last["jpeg"] = jpeg
    image = base64.b64encode(jpeg).decode()
    prompt = PROMPT.format(question=question)
    try:
        client = get_groq_client().with_options(max_retries=0)
        response = client.chat.completions.create(
            model=VISION_MODEL,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image}"}},
                ],
            }],
            max_tokens=200,
        )
        return (response.choices[0].message.content or "").strip() or "I couldn't make it out."
    except (groq.APIError, RuntimeError) as e:
        # Yerel model daha yavaş ve daha az isabetli, ama Groq'a ulaşılamazken hiç yoktan iyidir
        print(f"⚠️ Cloud vision failed, trying local {LOCAL_MODEL}: {e}")
        import ollama
        reply = ollama.chat(model=LOCAL_MODEL, messages=[{"role": "user", "content": prompt, "images": [image]}])
        return reply["message"]["content"].strip()
