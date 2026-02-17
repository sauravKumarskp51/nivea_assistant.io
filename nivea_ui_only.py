import os
import openai
from queue import Queue

import datetime
import logging
import speech_recognition as sr
import pyttsx3
import webbrowser
import sys
import time
import threading

import spotipy

from spotipy.oauth2 import SpotifyOAuth, SpotifyOauthError
from spotipy.exceptions import SpotifyException

import urllib.parse








# --------- LOGGING SETUP ----------
logging.getLogger("kivy").setLevel(logging.INFO)

# comtypes (pyttsx3 / SAPI) debug band
logging.getLogger("comtypes").setLevel(logging.ERROR)
logging.getLogger("comtypes.client").setLevel(logging.ERROR)

# Spotipy / HTTP libs ke DEBUG logs band
logging.getLogger("spotipy").setLevel(logging.WARNING)
logging.getLogger("spotipy.client").setLevel(logging.WARNING)
logging.getLogger("spotipy.oauth2").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)




# OpenAI config - set these as environment variables for safety
OPENAI_API_KEY = os.environ.get("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")  # REQUIRED
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")  # optional, change if you like

if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY
else:
    print("WARNING: OPENAI_API_KEY not set — GPT features disabled.")






# A small queue to ensure we don't spam the API from parallel threads
_gpt_lock = threading.Lock()
_gpt_last_call = 0.0
GPT_MIN_INTERVAL = 1.0  # seconds between calls (simple throttling)

def gpt_query(prompt: str, max_tokens: int = 600) -> str:
    """
    Synchronous call to OpenAI. Call from a background thread.
    Returns assistant text or error string.
    """
    if not OPENAI_API_KEY:
        return "GPT is not configured. Please set OPENAI_API_KEY."

    global _gpt_last_call
    with _gpt_lock:
        elapsed = time.time() - _gpt_last_call
        if elapsed < GPT_MIN_INTERVAL:
            time.sleep(GPT_MIN_INTERVAL - elapsed)
        _gpt_last_call = time.time()

    try:
        resp = openai.ChatCompletion.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": (
                    "You are Nivea Assistant — concise, polite, helpful. "
                    "When asked to write or transform text, provide the result only, "
                    "and when asked for step-by-step, include numbered steps."
                )},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=0.7,
        )
        # prefer the first assistant message
        text = resp["choices"][0]["message"]["content"].strip()
        return text
    except Exception as e:
        ui_log(f"GPT error: {e}")
        return "Sorry, I couldn't reach the AI service right now."




def run_gpt_and_reply(prompt: str):
    """Run GPT in background thread and then speak+show the reply (safe for calling from UI thread)."""
    def _task():
        # show a short UI hint immediately
        ui_log("Assistant: Thinking...")
        reply = gpt_query(prompt)
        # display & speak
        ui_log("Assistant: " + reply)
        speak(reply)
    threading.Thread(target=_task, daemon=True).start()









# --------- KIVY IMPORTS ----------
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.slider import Slider
from kivy.uix.image import Image, AsyncImage
from kivy.properties import StringProperty, BooleanProperty
from kivy.clock import Clock
from kivy.graphics import Color, RoundedRectangle
from kivy.uix.behaviors import ButtonBehavior


# ---------- SPOTIFY CONFIG ----------
SPOTIFY_CLIENT_ID = "42a64a2a568148319ea6f376056e3bbc"
SPOTIFY_CLIENT_SECRET = "151ccf8055bb4aaf9c6277664468a499"
SPOTIFY_REDIRECT_URI = "http://127.0.0.1:8888/callback"
SPOTIFY_SCOPE = "user-modify-playback-state user-read-playback-state"

spotify = None              # global client
spotify_web_opened = False  # track if we've opened web player already

# ---------- REUSABLE GLASS CARD ----------
class GlassCard(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.padding = 20
        self.spacing = 10
        self.orientation = "vertical"

        with self.canvas.before:
            Color(0, 0.92, 1, 0.14)  # cyan-ish glass effect
            self._bg = RoundedRectangle(radius=[20, 20, 20, 20])

        self.bind(pos=self._update_bg, size=self._update_bg)

    def _update_bg(self, *args):
        self._bg.pos = self.pos
        self._bg.size = self.size


class IconButton(ButtonBehavior, Image):
    """Image jise button ki tarah click kar sakte hain."""
    pass






# ---------- LEFT: WEATHER CARD ----------
class WeatherCard(GlassCard):
    date_text = StringProperty("Tuesday, April 23")
    time_text = StringProperty("10:24")
    temp_text = StringProperty("27°C")
    extra_text = StringProperty("Partly cloudy • Your City")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.date_label = Label(
            text=self.date_text,
            font_size="24sp",
            halign="left",
            valign="top",
            size_hint_y=None,
            height=60,
        )
        self.date_label.bind(size=self._update_label_text_size)

        self.time_label = Label(
            text=self.time_text,
            font_size="40sp",
            halign="left",
            valign="center",
            size_hint_y=None,
            height=70,
        )
        self.time_label.bind(size=self._update_label_text_size)

        self.temp_label = Label(
            text=self.temp_text,
            font_size="48sp",
            halign="left",
            valign="center",
            size_hint_y=None,
            height=80,
        )
        self.temp_label.bind(size=self._update_label_text_size)

        self.extra_label = Label(
            text=self.extra_text,
            font_size="16sp",
            halign="left",
            valign="top",
            size_hint_y=None,
            height=40,
        )
        self.extra_label.bind(size=self._update_label_text_size)

        # Weather icon placeholder
        self.icon_label = Label(
            text="☁️", font_size="40sp", size_hint_y=None, height=60
        )

        self.add_widget(self.date_label)
        self.add_widget(self.icon_label)
        self.add_widget(self.time_label)
        self.add_widget(self.temp_label)
        self.add_widget(self.extra_label)

        # Update time every second
        Clock.schedule_interval(self.update_datetime, 1)

    def _update_label_text_size(self, label, size):
        label.text_size = size

    def update_datetime(self, dt):
        now = datetime.datetime.now()
        self.date_text = now.strftime("%A, %B %d")
        self.time_text = now.strftime("%I:%M %p")
        self.date_label.text = self.date_text
        self.time_label.text = self.time_text

    def set_weather(self, description: str, temp_c: float, city: str):
        """Baad me real weather API se call kar sakte ho."""
        self.temp_text = f"{int(round(temp_c))}°C"
        self.extra_text = f"{description} • {city}"
        self.temp_label.text = self.temp_text
        self.extra_label.text = self.extra_text


'''

# ---------- LEFT: NOW PLAYING CARD ----------
class NowPlayingCard(GlassCard):
    title_text = StringProperty("No song playing")
    artist_text = StringProperty("")
    status_on = BooleanProperty(False)
    cover_url = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # TOP: heading
        heading = Label(
            text="NOW PLAYING",
            font_size="18sp",
            halign="left",
            valign="center",
            size_hint_y=None,
            height=30,
        )
        heading.bind(size=self._update_label_text_size)

        # MIDDLE: row -> [ cover image | text info ]
        row = BoxLayout(orientation="horizontal", spacing=10)

        # Album cover (Spotify image)
        self.cover = AsyncImage(
            source="",
            allow_stretch=True,
            keep_ratio=True,
            size_hint_x=0.35,
        )

        # RIGHT side: title + artist + status
        info_col = BoxLayout(orientation="vertical", spacing=5)

        self.title_label = Label(
            text=self.title_text,
            font_size="18sp",
            halign="left",
            valign="top",
        )
        self.title_label.bind(size=self._update_label_text_size)

        self.artist_label = Label(
            text=self.artist_text,
            font_size="14sp",
            halign="left",
            valign="top",
        )
        self.artist_label.bind(size=self._update_label_text_size)

        self.status_label = Label(
            text="Status: OFF",
            font_size="14sp",
            halign="left",
            valign="bottom",
            size_hint_y=None,
            height=30,
        )
        self.status_label.bind(size=self._update_label_text_size)

        info_col.add_widget(self.title_label)
        info_col.add_widget(self.artist_label)
        info_col.add_widget(self.status_label)

        row.add_widget(self.cover)
        row.add_widget(info_col)

        # Add to card
        self.add_widget(heading)
        self.add_widget(row)

    def _update_label_text_size(self, label, size):
        # Wrap text nicely inside available space
        label.text_size = size

    def set_now_playing(self, title: str, artist: str, playing: bool, cover_url: str | None = None):
        self.title_text = title or "No song playing"
        self.artist_text = artist or ""
        self.status_on = playing

        self.title_label.text = self.title_text
        self.artist_label.text = self.artist_text
        self.status_label.text = "Status: ON" if playing else "Status: OFF"

        # Album art update
        if cover_url:
            self.cover_url = cover_url
            self.cover.source = cover_url
        else:
            self.cover_url = ""
            self.cover.source = ""  # no image when nothing is playing
'''



# ---------- LEFT: NOW PLAYING CARD ----------
class NowPlayingCard(GlassCard):
    title_text = StringProperty("No song playing")
    artist_text = StringProperty("")
    status_on = BooleanProperty(False)
    cover_url = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # TOP: heading
        heading = Label(
            text="NOW PLAYING",
            font_size="18sp",
            halign="left",
            valign="center",
            size_hint_y=None,
            height=30,
        )
        heading.bind(size=self._update_label_text_size)

        # MIDDLE: row -> [ cover | info ]
        row = BoxLayout(orientation="horizontal", spacing=10)

        # Album cover
        self.cover = AsyncImage(
            source="",
            allow_stretch=True,
            keep_ratio=True,
            size_hint_x=0.35,
        )

        # RIGHT: title + artist + status
        info_col = BoxLayout(orientation="vertical", spacing=5)

        self.title_label = Label(
            text=self.title_text,
            font_size="18sp",
            halign="left",
            valign="top",
        )
        self.title_label.bind(size=self._update_label_text_size)

        self.artist_label = Label(
            text=self.artist_text,
            font_size="14sp",
            halign="left",
            valign="top",
        )
        self.artist_label.bind(size=self._update_label_text_size)

        self.status_label = Label(
            text="Status: OFF",
            font_size="14sp",
            halign="left",
            valign="bottom",
            size_hint_y=None,
            height=26,
        )
        self.status_label.bind(size=self._update_label_text_size)

        info_col.add_widget(self.title_label)
        info_col.add_widget(self.artist_label)
        info_col.add_widget(self.status_label)

        row.add_widget(self.cover)
        row.add_widget(info_col)

        self.add_widget(heading)
        self.add_widget(row)

    def _update_label_text_size(self, label, size):
        label.text_size = size

    def set_now_playing(self, title: str, artist: str, playing: bool, cover_url: str | None = None):
        self.title_text = title or "No song playing"
        self.artist_text = artist or ""
        self.status_on = playing

        self.title_label.text = self.title_text
        self.artist_label.text = self.artist_text
        self.status_label.text = "Status: ON" if playing else "Status: OFF"

        if cover_url:
            self.cover_url = cover_url
            self.cover.source = cover_url
        else:
            self.cover_url = ""
            self.cover.source = ""



# ---------- BOTTOM: PLAYER BAR ----------
class PlayerBar(GlassCard):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.spacing = 8
        self.padding = [15, 10, 15, 10]

        self.duration_ms = 0


                # --- Controls row ---
        controls_row = BoxLayout(orientation="horizontal", spacing=20,
                                 size_hint_y=None, height=40)

        # Paths to icon files
        self.icon_prev = "icons/prev.png"
        self.icon_play = "icons/play.png"
        self.icon_pause = "icons/pause.png"
        self.icon_next = "icons/next.png"

        self.prev_btn = IconButton(
            source=self.icon_prev,
            size_hint_x=None, width=40,
            allow_stretch=True,
            keep_ratio=True,
        )
        self.play_btn = IconButton(
            source=self.icon_play,
            size_hint_x=None, width=50,
            allow_stretch=True,
            keep_ratio=True,
        )
        self.next_btn = IconButton(
            source=self.icon_next,
            size_hint_x=None, width=40,
            allow_stretch=True,
            keep_ratio=True,
        )

        # Center align them a bit
        controls_row.add_widget(Label(size_hint_x=0.3))
        controls_row.add_widget(self.prev_btn)
        controls_row.add_widget(self.play_btn)
        controls_row.add_widget(self.next_btn)
        controls_row.add_widget(Label(size_hint_x=0.3))


        # --- Progress row ---
        progress_row = BoxLayout(orientation="horizontal", spacing=10,
                                 size_hint_y=None, height=26)

        self.current_time_label = Label(
            text="0:00",
            font_size="12sp",
            size_hint_x=None, width=50,
            halign="right", valign="middle",
        )
        self.current_time_label.bind(size=self._update_label_text_size)

        self.slider = Slider(
            min=0.0, max=1.0, value=0.0,
            size_hint_x=1.0,
        )

        self.total_time_label = Label(
            text="0:00",
            font_size="12sp",
            size_hint_x=None, width=50,
            halign="left", valign="middle",
        )
        self.total_time_label.bind(size=self._update_label_text_size)

        progress_row.add_widget(self.current_time_label)
        progress_row.add_widget(self.slider)
        progress_row.add_widget(self.total_time_label)

        self.add_widget(controls_row)
        self.add_widget(progress_row)

        # Bind buttons
        # Bind buttons
        self.play_btn.bind(on_release=self._on_play_pressed)
        self.next_btn.bind(on_release=self._on_next_pressed)
        self.prev_btn.bind(on_release=self._on_prev_pressed)

        # Seeking on slider release
        self.slider.bind(on_touch_up=self._on_slider_touch_up)


    def _update_label_text_size(self, label, size):
        label.text_size = size

    def _fmt_time(self, ms: int) -> str:
        if ms <= 0:
            return "0:00"
        secs = ms // 1000
        m = secs // 60
        s = secs % 60
        return f"{m}:{s:02d}"

    def set_progress(self, position_ms: int, duration_ms: int, is_playing: bool):
        self.duration_ms = duration_ms or 0

        # Avoid division by zero
        if duration_ms > 0:
            self.slider.value = float(position_ms) / float(duration_ms)
        else:
            self.slider.value = 0.0

        self.current_time_label.text = self._fmt_time(position_ms)
        self.total_time_label.text = self._fmt_time(duration_ms)

        self.set_play_state(is_playing)

    def set_play_state(self, is_playing: bool):
        # Play / Pause icon toggle
        self.play_btn.source = self.icon_pause if is_playing else self.icon_play


    def _on_slider_touch_up(self, slider, touch):
        if slider.collide_point(*touch.pos) and self.duration_ms > 0:
            new_pos_ms = int(slider.value * self.duration_ms)
            threading.Thread(
                target=spotify_control_seek,
                args=(new_pos_ms,),
                daemon=True
            ).start()

    def _on_play_pressed(self, *args):
        threading.Thread(
            target=spotify_control_play_pause,
            daemon=True
        ).start()

    def _on_next_pressed(self, *args):
        threading.Thread(
            target=spotify_control_next,
            daemon=True
        ).start()

    def _on_prev_pressed(self, *args):
        threading.Thread(
            target=spotify_control_prev,
            daemon=True
        ).start()


# ===================== SPOTIFY PLAYER CONTROL ======================

def _get_sp():
    """Return authenticated spotify client or None"""
    try:
        return get_spotify_client()
    except:
        return None


def spotify_control_play_pause():
    sp = _get_sp()
    if not sp:
        return
    try:
        current = sp.current_playback()
        if current and current.get("is_playing"):
            sp.pause_playback()   # pause if already playing
        else:
            sp.start_playback()   # resume if paused
    except Exception as e:
        ui_log(f"Spotify error (play/pause): {e}")


def spotify_control_next():
    sp = get_spotify_client()
    if sp is None:
        return
    try:
        device_id = get_active_device_id(sp)
        if not device_id:
            speak("Spotify device not found.")
            return
        sp.next_track(device_id=device_id)
    except SpotifyException as e:
        ui_log(f"Spotify next error: {e}")
        speak("I couldn't skip to the next track.")


def spotify_control_prev():
    sp = get_spotify_client()
    if sp is None:
        return
    try:
        device_id = get_active_device_id(sp)
        if not device_id:
            speak("Spotify device not found.")
            return
        sp.previous_track(device_id=device_id)
    except SpotifyException as e:
        ui_log(f"Spotify previous error: {e}")
        speak("I couldn't go to the previous track.")


def ensure_shuffle_on(sp, device_id):
    try:
        sp.shuffle(state=True, device_id=device_id)
    except Exception as e:
        ui_log(f"Spotify shuffle error: {e}")


def spotify_control_seek(position_ms: int):
    sp = _get_sp()
    if not sp:
        return
    try:
        sp.seek_track(position_ms)
    except Exception as e:
        ui_log(f"Spotify error (seek): {e}")


# ---------- MIDDLE PANEL (EMPTY FOR NOW) ----------
class MiddlePanel(GlassCard):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Tumne bola tha: abhi chat nahi, to sirf heading rakha hai
        title = Label(
            text="VOICE CONSOLE",
            font_size="22sp",
            halign="center",
            valign="middle",
        )
        title.bind(size=self._update_label_text_size)
        self.add_widget(title)

    def _update_label_text_size(self, label, size):
        label.text_size = size


# ---------- RIGHT: AVATAR PANEL ----------
class AvatarPanel(GlassCard):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        avatar_path = "nivea_avatar.png"  # yahan apni avatar image rakh sakte ho
        if os.path.exists(avatar_path):
            img = Image(source=avatar_path, allow_stretch=True, keep_ratio=True)
            img.size_hint_y = 0.8
            self.add_widget(img)
        else:
            placeholder = Label(
                text="[ NIVEA AVATAR ]",
                font_size="18sp",
                halign="center",
                valign="middle",
            )
            placeholder.bind(size=self._update_label_text_size)
            self.add_widget(placeholder)

        name_label = Label(
            text="N I V E A",
            font_size="24sp",
            halign="center",
            valign="middle",
            size_hint_y=None,
            height=40,
        )
        name_label.bind(size=self._update_label_text_size)
        self.add_widget(name_label)

    def _update_label_text_size(self, label, size):
        label.text_size = size


# ---------- ROOT LAYOUT ----------
      
class NiveaRoot(BoxLayout):
    def __init__(self, **kwargs):
        # PURE screen ko 3 columns me rakhenge (left / middle / right)
        super().__init__(orientation="horizontal", **kwargs)
        self.spacing = 20
        self.padding = 20

        # ---------- LEFT COLUMN ----------
        left_col = BoxLayout(
            orientation="vertical",
            spacing=20,
            size_hint_x=0.25
        )

        # Weather top
        self.weather_card = WeatherCard(size_hint_y=0.40)

        # Now playing (cover + title + artist)
        self.now_playing_card = NowPlayingCard(size_hint_y=0.35)

        # Player bar: GAANA ke just niche
        self.player_bar = PlayerBar(size_hint_y=0.25)

        left_col.add_widget(self.weather_card)
        left_col.add_widget(self.now_playing_card)
        left_col.add_widget(self.player_bar)

        # ---------- MIDDLE COLUMN ----------
        self.middle_panel = MiddlePanel(size_hint_x=0.45)

        # ---------- RIGHT COLUMN ----------
        right_col = BoxLayout(
            orientation="vertical",
            size_hint_x=0.30
        )
        self.avatar_panel = AvatarPanel()
        right_col.add_widget(self.avatar_panel)

        # Add teen columns main root me
        self.add_widget(left_col)
        self.add_widget(self.middle_panel)
        self.add_widget(right_col)

    def append_log(self, line: str):
        # abhi use nahi kar rahe
        pass




'''
        # LEFT COLUMN
        left_col = BoxLayout(orientation="vertical", spacing=20, size_hint_x=0.25)
        self.weather_card = WeatherCard(size_hint_y=0.6)
        self.now_playing_card = NowPlayingCard(size_hint_y=0.4)
        left_col.add_widget(self.weather_card)
        left_col.add_widget(self.now_playing_card)

        # MIDDLE COLUMN
        self.middle_panel = MiddlePanel(size_hint_x=0.45)

        # RIGHT COLUMN
        right_col = BoxLayout(orientation="vertical", size_hint_x=0.30)
        self.avatar_panel = AvatarPanel()
        right_col.add_widget(self.avatar_panel)

        self.add_widget(left_col)
        self.add_widget(self.middle_panel)
        self.add_widget(right_col)

    # optional: agar future me UI me log show karna ho
    def append_log(self, line: str):
        # Abhi visually kahi use nahi kar rahe, but hook rakh diya
        pass

'''




# ---------- KIVY APP ----------
class NiveaApp(App):
    instance = None

    def build(self):
        NiveaApp.instance = self
        self.title = "Nivea Voice Assistant"
        self.root_widget = NiveaRoot()
        return self.root_widget

    # ui_log yahan call karega
    def append_log(self, text: str):
        # abhi UI me koi text area nahi, to ignore; console pe print ho hi raha hai
        pass

    # Spotify se now playing update
    def update_now_playing(self, title: str, artist: str, playing: bool = True, cover_url: str | None = None):
        self.root_widget.now_playing_card.set_now_playing(title, artist, playing, cover_url)

    def update_player_progress(self, position_ms: int, duration_ms: int, is_playing: bool):
        self.root_widget.player_bar.set_progress(position_ms, duration_ms, is_playing)

    def set_play_state(self, is_playing: bool):
        self.root_widget.player_bar.set_play_state(is_playing)






    # Weather update hook (jab API add karoge)
    def update_weather(self, description: str, temp_c: float, city: str):
        self.root_widget.weather_card.set_weather(description, temp_c, city)

    

    def on_start(self):
        # Voice assistant loop
        t1 = threading.Thread(target=voice_main_loop, daemon=True)
        t1.start()

        # Spotify now-playing poller
        t2 = threading.Thread(target=spotify_poll_loop, daemon=True)
        t2.start()



# ---------- UI LOG HELPER ----------
def ui_log(msg: str):
    print(msg)
    if NiveaApp.instance:
        NiveaApp.instance.append_log(msg)


# ------------- TEXT TO SPEECH -------------
voice_id = None
speech_rate = 178
speech_volume = 0.9

def init_tts_voice():
    global voice_id
    try:
        temp_engine = pyttsx3.init()
        voices = temp_engine.getProperty("voices")

        female_voice = None
        for v in voices:
            name_low = v.name.lower()
            if "female" in name_low or "zira" in name_low or "hema" in name_low:
                female_voice = v.id
                break

        if female_voice:
            voice_id = female_voice
        else:
            voice_id = voices[1].id if len(voices) > 1 else voices[0].id

        temp_engine.stop()
    except Exception as e:
        voice_id = None
        print("TTS init error:", e)

# app start pe ek baar call
init_tts_voice()


def speak(text):
    ui_log("Assistant: " + text)

    def _run_tts():
        try:
            engine = pyttsx3.init()
            if voice_id is not None:
                engine.setProperty("voice", voice_id)
            engine.setProperty("rate", speech_rate)
            engine.setProperty("volume", speech_volume)
            engine.say(text)
            engine.runAndWait()
            engine.stop()
        except Exception as e:
            ui_log(f"TTS error: {e}")

    t = threading.Thread(target=_run_tts, daemon=True)
    t.start()


# ------------- SPEECH TO TEXT -------------
recognizer = sr.Recognizer()
mic = sr.Microphone()

WAKE_WORD = "nivea"   # you can change to "alexa" or anything


def listen():
    """Listen from the microphone and return recognized text (lowercase)."""
    with mic as source:
        ui_log("\nListening...")
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        audio = recognizer.listen(source)

    try:
        text = recognizer.recognize_google(audio, language="en-IN")
        text = text.lower()
        ui_log("You: " + text)
        return text
    except sr.UnknownValueError:
        ui_log("Didn't catch that.")
        return ""
    except sr.RequestError as e:
        ui_log(f"Error with speech service: {e}")
        return ""


# ---------- SPOTIFY HELPERS ----------
def get_spotify_client():
    global spotify
    if spotify is not None:
        return spotify

    # Guard: agar id/secret nahi diye to Spotify disable
    if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
        speak("Spotify abhi configure nahi hai. Please client ID aur secret set karo.")
        return None

    try:
        spotify = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=SPOTIFY_CLIENT_ID,
            client_secret=SPOTIFY_CLIENT_SECRET,
            redirect_uri=SPOTIFY_REDIRECT_URI,
            scope=SPOTIFY_SCOPE,
            open_browser=True
        ))
        return spotify
    except SpotifyOauthError as e:
        ui_log(f"Spotify OAuth error (client): {e}")
        speak("Spotify ke client details me problem aa rahi hai. Please client ID aur secret check karo.")
        return None
    except Exception as e:
        ui_log(f"Spotify auth error: {e}")
        speak("Mujhe Spotify se connect karne me problem aa rahi hai.")
        return None



# --- Helpers used by the new get_active_device_id ---
def find_preferred_device(device_list):
    """Prefer a Web Player / Computer device, then non-phone, then any."""
    if not device_list:
        return None

    # 1) Try names that indicate Web Player
    for d in device_list:
        name = (d.get("name") or "").lower()
        if "web player" in name or "webplayer" in name or "open.spotify.com" in name or "web" in name:
            return d.get("id")

    # 2) Prefer type == Computer
    for d in device_list:
        if d.get("type") == "Computer":
            return d.get("id")

    # 3) Active non-phone first
    for d in device_list:
        if d.get("is_active") and d.get("type") != "Smartphone":
            return d.get("id")

    # 4) Any non-smartphone
    for d in device_list:
        if d.get("type") != "Smartphone":
            return d.get("id")

    # 5) fallback any
    return device_list[0].get("id")


def transfer_playback_to_device(sp, device_id, force_play=False):
    """Transfer playback to the device via Spotify Connect."""
    try:
        sp.transfer_playback(device_id=device_id, force_play=force_play)
        ui_log(f"Transferred playback to device {device_id}")
        return True
    except Exception as e:
        ui_log(f"transfer_playback error: {e}")
        return False


# --- Replacement get_active_device_id ---
def get_active_device_id(sp, poll_web_seconds=12):
    """
    Return a preferred device id.
    If no preferred device, open web player and poll up to poll_web_seconds for it to appear,
    then transfer playback to it.
    """
    global spotify_web_opened

    # Quick try some times to read devices (small loop to handle transient API errors)
    for attempt in range(3):
        try:
            devices = sp.devices().get("devices", [])
            break
        except Exception as e:
            ui_log(f"Spotify devices() read error (attempt {attempt+1}): {e}")
            time.sleep(1)
    else:
        speak("Mujhe Spotify devices read karne me problem aa rahi hai.")
        return None

    dev_id = find_preferred_device(devices)
    if dev_id:
        # Ensure shuffle on for the device (your existing behavior)
        try:
            ensure_shuffle_on(sp, dev_id)
        except Exception:
            pass
        return dev_id

    # No preferred device found: try opening web player and poll for it
    if not spotify_web_opened:
        speak("Opening Spotify Web Player in your browser to use as playback device.")
        webbrowser.open("https://open.spotify.com/")
        spotify_web_opened = True
    else:
        speak("Waiting for Spotify Web Player to become available...")

    # Poll for the web player / computer device
    end_time = time.time() + poll_web_seconds
    while time.time() < end_time:
        try:
            devices = sp.devices().get("devices", [])
        except Exception as e:
            ui_log(f"Spotify devices() polling error: {e}")
            time.sleep(1)
            continue

        dev_id = find_preferred_device(devices)
        if dev_id:
            # Transfer playback to this device and return it
            transferred = transfer_playback_to_device(sp, dev_id, force_play=True)
            try:
                ensure_shuffle_on(sp, dev_id)
            except Exception:
                pass
            return dev_id

        time.sleep(1)

    # nothing found after polling
    speak("Web player device nahi mila. Please open Spotify in your browser and press play once.")
    return None

# ---------- SPOTIFY POLLING LOOP ----------
def spotify_poll_loop():
    """Background me current playing song + progress check karta rahega."""
    while True:
        sp = get_spotify_client()
        if sp is None:
            time.sleep(10)
            continue

        try:
            playback = sp.current_playback()
        except Exception as e:
            ui_log(f"Spotify current_playback error: {e}")
            time.sleep(10)
            continue

        if playback and playback.get("item"):
            is_playing = playback.get("is_playing", False)
            track = playback["item"]
            track_name = track.get("name", "Unknown")
            artists = ", ".join(a["name"] for a in track.get("artists", []))
            images = track.get("album", {}).get("images", [])
            cover_url = images[0]["url"] if images else None
            position_ms = playback.get("progress_ms", 0)
            duration_ms = track.get("duration_ms", 0)

            if NiveaApp.instance:
                NiveaApp.instance.update_now_playing(track_name, artists, is_playing, cover_url)
                NiveaApp.instance.update_player_progress(position_ms, duration_ms, is_playing)
        else:
            if NiveaApp.instance:
                NiveaApp.instance.update_now_playing("No song playing", "", False, None)
                NiveaApp.instance.update_player_progress(0, 0, False)

        time.sleep(5)

# ------------- SPOTIFY SEARCH & PLAY -------------
def play_playlist_search(query):
    sp = get_spotify_client()
    if sp is None:
        return
    device_id = get_active_device_id(sp)
    if not device_id:
        speak("I could not find any active Spotify device. Please open Spotify on your computer or web player.")
        return

    results = sp.search(q=query, type="playlist", limit=1)
    playlists = results.get("playlists", {}).get("items", [])
    if not playlists:
        speak(f"I could not find a playlist for {query}.")
        return

    pl = playlists[0]
    playlist_uri = pl["uri"]
    playlist_name = pl["name"]
    images = pl.get("images", [])
    cover_url = images[0]["url"] if images else None

    speak(f"Playing playlist {playlist_name} on Spotify.")

    if NiveaApp.instance:
        NiveaApp.instance.update_now_playing(playlist_name, "", True, cover_url)


    try:
        sp.start_playback(device_id=device_id, context_uri=playlist_uri)
    except SpotifyException as e:
        ui_log(f"Spotify playback error (playlist): {e}")
        speak("I couldn't start the playlist on this device. Please play something once in Spotify and try again.")


def play_song_search(query):
    sp = get_spotify_client()
    if sp is None:
        return
    device_id = get_active_device_id(sp)
    if not device_id:
        speak("I could not find any active Spotify device. Please open Spotify on your computer or web player.")
        return

    results = sp.search(q=query, type="track", limit=1)
    tracks = results.get("tracks", {}).get("items", [])
    if not tracks:
        speak(f"I could not find the song {query}.")
        return

    track = tracks[0]
    track_uri = track["uri"]
    track_name = track["name"]
    artists = ", ".join(a["name"] for a in track["artists"])
    album = track.get("album", {})
    album_uri = album.get("uri")
    images = album.get("images", [])
    cover_url = images[0]["url"] if images else None

    speak(f"Playing {track_name} by {artists} on Spotify.")

    # UI update
    if NiveaApp.instance:
        NiveaApp.instance.update_now_playing(track_name, artists, True, cover_url)

    try:
        ensure_shuffle_on(sp, device_id)
        if album_uri:
            # 👉 Album context: next/prev will move within album
            sp.start_playback(
                device_id=device_id,
                context_uri=album_uri,
                offset={"uri": track_uri},
            )
        else:
            # Fallback: single track
            sp.start_playback(device_id=device_id, uris=[track_uri])
    except SpotifyException as e:
        ui_log(f"Spotify playback error (track): {e}")
        speak("I couldn't start the song on this device. Please play something once in Spotify and try again.")



# ------------- COMMAND HANDLER -------------

def time_based_greeting():
    """Return a short greeting based on local time."""
    now = datetime.datetime.now()
    hour = now.hour
    if 5 <= hour < 12:
        return "Good morning, sir."
    if 12 <= hour < 17:
        return "Good afternoon, sir."
    if 17 <= hour < 21:
        return "Good evening, sir."
    return "Hello, sir."


def handle_command(command: str):
    """Process the part after wake word."""
    if not command or command.strip() == "":
        greet = time_based_greeting()
        # You can tweak the Hindi phrasing if you want more/less formal
        speak(f"{greet} Sir, mai kya madad kar sakti hoon?")
        return

    # TIME & DATE
    if "time" in command:
        now = datetime.datetime.now().strftime("%I:%M %p")
        speak(f"The time is {now}.")

    elif "date" in command:
        today = datetime.datetime.now().strftime("%d %B %Y")
        speak(f"Today is {today}.")

    # BASIC OPEN
    elif "open youtube" in command and "play" not in command:
        speak("Opening YouTube.")
        webbrowser.open("https://www.youtube.com")

    elif "open google" in command:
        speak("Opening Google.")
        webbrowser.open("https://www.google.com")

    # GOOGLE SEARCH
    elif "search for" in command:
        query = command.split("search for", 1)[1].strip()
        if query:
            speak(f"Searching for {query}.")
            webbrowser.open(f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}")
        else:
            speak("What should I search for?")


    # OPEN INSTAGRAM (new)
    elif "open instagram" in command or "instagram" == command.strip():
        speak("Opening Instagram.")
        webbrowser.open("https://www.instagram.com")


    # YOUTUBE PLAY (voice)
    elif "youtube" in command and "play" in command:
        after_play = command.split("play", 1)[1]
        after_play = after_play.replace("on youtube", "").strip()
        if not after_play:
            speak("What should I play on YouTube?")
        else:
            speak(f"Playing {after_play} on YouTube.")
            url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(after_play)
            webbrowser.open(url)

    # SPOTIFY PLAY
    elif "play" in command:
        after_play = command.split("play", 1)[1].strip()

        if not after_play:
            speak("Which song should I play?")
            return

        # Mood / style commands
        if "sad" in after_play:
            play_playlist_search("sad songs")
        elif "happy" in after_play:
            play_playlist_search("happy songs")
        elif "english" in after_play and "song" in after_play:
            play_playlist_search("english songs")
        elif "party" in after_play:
            play_playlist_search("party hits")
        else:
            # Treat as song name directly
            play_song_search(after_play)

    # EXIT
    elif "exit" in command or "stop" in command or "quit" in command:
        speak("Okay, shutting down. Bye!")
        sys.exit(0)

    else:
        #speak(f"You said: {command}. I don't know that command yet.")
        # check if user explicitly asked an AI task using keywords
        if command.startswith("summarize"):
            # "summarize <text>" or "summarize the following: ..."
            text_to_summarize = command.split("summarize", 1)[1].strip()
            if not text_to_summarize:
                speak("What should I summarize?")
                return
            prompt = f"Please provide a short summary (2-4 lines) of the following text:\n\n{text_to_summarize}"
            run_gpt_and_reply(prompt)
            return

        if command.startswith("write an email") or "draft an email" in command:
            # try to parse target and purpose loosely
            prompt = f"You are an assistant that writes professional emails. Compose an email based on: {command}"
            run_gpt_and_reply(prompt)
            return

        if command.startswith("translate") or "translate to" in command:
            # e.g. "translate hello to hindi"
            prompt = f"Translate the following: {command}"
            run_gpt_and_reply(prompt)
            return

        if command.startswith("explain") or command.startswith("how") or "why" in command:
            # quick knowledge / explain request
            prompt = f"Answer concisely: {command}"
            run_gpt_and_reply(prompt)
            return

        # final fallback: send entire command as a question to GPT
        prompt = (
            "User asked: " + command + "\n\n"
            "Act as a helpful assistant and reply in a concise friendly tone. "
            "If it's a step-by-step instruction, give numbered steps."
        )
        run_gpt_and_reply(prompt)






# ------------- MAIN VOICE LOOP -------------
def voice_main_loop():
    speak(f"Hello, I am your voice assistant. Say '{WAKE_WORD}' to talk to me.")
    while True:
        text = listen()
        if not text:
            continue

        if WAKE_WORD in text:
            command = text.replace(WAKE_WORD, "").strip()
            handle_command(command)
        else:
            ui_log(f"(No wake word, ignoring: {text})")


if __name__ == "__main__":
    NiveaApp().run()
