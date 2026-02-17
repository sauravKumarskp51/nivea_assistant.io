import os
import threading
import time
import datetime
import speech_recognition as sr
import webbrowser
import sys
import urllib.parse
import json
import pyperclip
import pyautogui
import pyttsx3
import re
import threading
from datetime import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from spotipy.exceptions import SpotifyException
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import urllib.parse
from speech_recognition import WaitTimeoutError, UnknownValueError
from selenium.common.exceptions import InvalidSessionIdException, WebDriverException
import queue
import pygetwindow as gw
import json, random, os
from datetime import date
from flask import Flask, jsonify

chatgpt_context = []        # conversation memory
last_chatgpt_response = "" # latest response text
tts_stop_flag = threading.Event()

google_driver = None
youtube_driver = None
chatgpt_driver = None

EDGE_PATH =r"C:\Program Files\BraveSoftware\Brave-Browser\Application\msedgedriver.exe"

if not os.path.exists(EDGE_PATH):
    EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

webbrowser.register(
    "edge",
    None,
    webbrowser.BackgroundBrowser(EDGE_PATH)
)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
ALL_GITA = os.path.join(DATA_DIR, "gita_all.json")
TODAY_GITA = os.path.join(DATA_DIR, "gita_today.json")


WAKE_WORD = "nivea"


def speak(text: str):
    print("Assistant:", text)
    engine = pyttsx3.init("sapi5")
    engine.setProperty("rate", 175)
    engine.setProperty("volume", 1.0)
    voices = engine.getProperty("voices")
    voice_index = 1 if len(voices) > 1 else 0
    engine.setProperty("voice", voices[voice_index].id)
    engine.say(text)
    engine.runAndWait()
    engine.stop()
    del engine


recognizer = sr.Recognizer()
mic = sr.Microphone()


def listen() -> str:
    try:
        recognizer.energy_threshold = 300  # lower = more sensitive
        recognizer.dynamic_energy_threshold = True  # auto-adjusts
        
        with mic as source:
            print("Listening...")
            recognizer.adjust_for_ambient_noise(source, duration=0.3)
            audio = recognizer.listen(source, timeout=4, phrase_time_limit=4)
        
        text = recognizer.recognize_google(audio, language="en-IN").lower()
        print("You:", text)
        return text
        
    except WaitTimeoutError:
        print("Listening timed out.")
        return ""
    except Exception as e:
        print("Recognition error:", e)
        return ""




# ================== CONFIG ==================
SPOTIFY_CLIENT_ID = "42a64a2a568148319ea6f376056e3bbc"
SPOTIFY_CLIENT_SECRET = "151ccf8055bb4aaf9c6277664468a499"
SPOTIFY_REDIRECT_URI = "http://127.0.0.1:8888/callback"
SPOTIFY_SCOPE = "user-modify-playback-state user-read-playback-state"

WAKE_WORD = "nivea"

# ============================================

app = Flask(__name__)
CORS(app)

spotify = None
spotify_web_opened = False

# ================== SPOTIFY ==================

def ensure_spotify_device(sp, wait_seconds=20):
    """
    Ensures a Spotify device exists.
    Opens Spotify Web Player ONLY if no device is found.
    """
    global spotify_web_opened

    # 1️⃣ Check if device already exists
    try:
        devices = sp.devices().get("devices", [])
        if devices:
            # Prefer active device
            for d in devices:
                if d.get("is_active"):
                    return d["id"]

            # Otherwise return first device
            return devices[0]["id"]
    except Exception:
        pass

    # 2️⃣ No device found → open Spotify Web (ONCE)
    if not spotify_web_opened:
        speak("Opening Spotify")
        webbrowser.open("https://open.spotify.com")
        spotify_web_opened = True

    # 3️⃣ Wait for device to appear
    end_time = time.time() + wait_seconds
    while time.time() < end_time:
        try:
            devices = sp.devices().get("devices", [])
            if devices:
                return devices[0]["id"]
        except Exception:
            pass

        time.sleep(1)

    return None

def ensure_spotify_open():
    global spotify_web_opened
    if not spotify_web_opened:
        speak("Opening Spotify")
        webbrowser.open("https://open.spotify.com")
        spotify_web_opened = True
        time.sleep(5)  # give browser time to load

def ensure_shuffle_on(sp, device_id):
    try:
        sp.shuffle(state=True, device_id=device_id)
    except Exception as e:
        print("Shuffle error:", e)

def get_active_device_id(sp, wait_seconds=12):
    end_time = time.time() + wait_seconds

    while time.time() < end_time:
        devices = sp.devices().get("devices", [])

        if devices:
            for d in devices:
                if d.get("is_active"):
                    return d["id"]

            # fallback to any device
            return devices[0]["id"]

        time.sleep(1)

    return None

def get_spotify_client():
    global spotify
    if spotify:
        return spotify

    spotify = spotipy.Spotify(
        auth_manager=SpotifyOAuth(
            client_id=SPOTIFY_CLIENT_ID,
            client_secret=SPOTIFY_CLIENT_SECRET,
            redirect_uri=SPOTIFY_REDIRECT_URI,
            scope=SPOTIFY_SCOPE,
            open_browser=True
        )
    )
    return spotify

def play_music():
    sp = get_spotify_client()
    device_id = ensure_spotify_device(sp)

    if not device_id:
        speak("Spotify is opening. Try again.")
        return

    try:
        sp.transfer_playback(device_id=device_id, force_play=True)
        time.sleep(0.3)
        sp.start_playback(device_id=device_id)
        speak("Playing music")
    except SpotifyException as e:
        print("Spotify play error:", e)
        speak("Spotify not ready yet.")

def pause_music():
    sp = get_spotify_client()
    device_id = ensure_spotify_device(sp)

    if not device_id:
        speak("Spotify not ready.")
        return

    try:
        sp.transfer_playback(device_id=device_id, force_play=False)
        time.sleep(0.3)
        sp.pause_playback(device_id=device_id)
        speak("Music paused")
    except SpotifyException as e:
        print("Spotify pause error:", e)
        speak("Nothing is playing right now.")

def next_track():
    sp = get_spotify_client()
    device_id = ensure_spotify_device(sp)
    if device_id:
        sp.next_track(device_id=device_id)
        speak("Next song")

def prev_track():
    sp = get_spotify_client()
    device_id = ensure_spotify_device(sp)
    if device_id:
        sp.previous_track(device_id=device_id)
        speak("Previous song")

def play_song_search(query):
    sp = get_spotify_client()
    if sp is None:
        return

    # 1️⃣ Ensure device exists (auto-opens Spotify web)
    device_id = ensure_spotify_device(sp)
    if not device_id:
        speak("Spotify is opening. Please try again in a moment.")
        return

    # 2️⃣ Search song
    results = sp.search(q=query, type="track", limit=1)
    tracks = results.get("tracks", {}).get("items", [])

    if not tracks:
        speak(f"I could not find {query}")
        return

    track = tracks[0]
    track_uri = track["uri"]
    track_name = track["name"]
    artists = ", ".join(a["name"] for a in track["artists"])
    album_uri = track["album"]["uri"]

    speak(f"Playing {track_name} by {artists}")

    try:
        # 3️⃣ Start playback with CONTEXT (important for autoplay)
        sp.start_playback(
            device_id=device_id,
            context_uri=album_uri,
            offset={"uri": track_uri}
        )

        # 4️⃣ Enable shuffle so next songs auto-play
        sp.shuffle(True, device_id=device_id)

    except SpotifyException as e:
        print("Spotify playback error:", e)
        speak("Spotify is opening. Please try again.")

# ================== GITA ==================

def get_random_gita_shlok():
    with open(ALL_GITA, "r", encoding="utf-8") as f:
        shloks = json.load(f)

    return random.choice(shloks)

def safe_load_json(path, default):
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print("⚠️ JSON load failed:", e)
    return default



# ================== CORE SYSTEM ACTIONS ==================

def action_open_browser():
    speak("Opening browser")
    os.startfile("msedge")

def action_open_files():
    speak("Opening files")
    os.startfile("explorer")


def action_open_settings():
    speak("Opening settings")
    os.system("start ms-settings:")


def action_open_calendar():
    speak("Opening calendar")
    webbrowser.open("https://calendar.google.com")




# ================== ALARM ==================

with open("alarm_positions.json") as f:
    POS = json.load(f)

def click(name, delay=0.5):
    p = POS[name]
    pyautogui.click(p["x"], p["y"])
    time.sleep(delay)

def parse_time_from_voice(text):
    text = text.lower().replace(".", "").strip()

    # Matches: 8, 8 30, 8:30, 8:30 pm, 20:15
    match = re.search(
        r'(\d{1,2})(?:[:\s](\d{2}))?\s*(am|pm)?',
        text
    )

    if not match:
        return None

    hour = int(match.group(1))
    minute = int(match.group(2)) if match.group(2) else 0
    meridiem = match.group(3)

    if meridiem:
        if meridiem == "pm" and hour < 12:
            hour += 12
        if meridiem == "am" and hour == 12:
            hour = 0

    if hour > 23 or minute > 59:
        return None

    return hour, minute

def focus_and_maximize_clock():
    """Bring Clock to front and keep it maximized."""
    for w in gw.getAllWindows():
        if "clock" in w.title.lower():
            try:
                w.restore()
                w.activate()
                time.sleep(0.3)
                w.maximize()          # hard maximize
                time.sleep(0.5)
            except:
                pass
            break

def ensure_alarm_ready():
    """Open Clock → Maximize → Go to Alarm tab"""
    speak("Opening alarm app")
    
    # Open Clock
    pyautogui.hotkey("win", "r")
    time.sleep(0.3)
    pyautogui.write("ms-clock:")
    pyautogui.press("enter")
    time.sleep(2.5)
    
    # Maximize & focus
    #pyautogui.hotkey("win", "up")
    #time.sleep(0.8)
    focus_and_maximize_clock()

    # Go to Alarm tab
    try:
        click("alarm_tab", delay=1.0)
        speak("Alarm section ready")
    except:
        speak("Opening alarm section")
        pyautogui.click(80, 200)  # fallback alarm tab position
        time.sleep(0.8)

def set_alarm_ui(hour, minute):
    """Set exact time and CLICK Save button"""
    speak(f"Setting {hour}:{minute:02d}")
    
    # 1) Hour field
    click("hour_field", delay=0.3)
    pyautogui.hotkey("ctrl", "a")
    pyautogui.write(str(hour))
    time.sleep(0.2)
    
    # 2) Minute field
    click("minute_field", delay=0.3)
    pyautogui.hotkey("ctrl", "a")
    pyautogui.write(f"{minute:02d}")
    time.sleep(0.2)
    
    # 3) Click Save BUTTON explicitly
    click("save_button", delay=0.5)   # <- uses alarm_positions.json
    
    # 4) Small wait so popup can close
    time.sleep(0.8)

def find_and_click_alarm_box():
    """Find first available/modifiable alarm box and click it"""
    speak("Finding alarm slot")
    
    # Try all 4 boxes in order
    for i in range(1, 5):
        try:
            click(f"alarm_box_{i}", delay=0.3)
            time.sleep(0.5)
            speak(f"Using slot {i}")
            return True
        except:
            continue  # box doesn't exist or can't click
    
    speak("No slots available")
    return False

def set_alarm_smart():
    """Complete flow: find box → set time"""
    if not find_and_click_alarm_box():
        speak("All alarm slots full. Delete one first.")
        return
    
    # Edit popup appears → set time
    time.sleep(0.8)
    ask_and_set_alarm()

def ask_and_set_alarm():
    """Ask for time and set alarm - assumes Alarm tab is ready"""
    speak("What time? Say eight thirty or nine am")
    time.sleep(0.5)
    
    while True:
        time_text = listen()
        if not time_text:
            speak("Please repeat the time")
            continue
            
        parsed = parse_time_from_voice(time_text)
        if parsed:
            hour, minute = parsed
            set_alarm_ui(hour, minute)
            speak("Alarm set successfully!")
            break
        else:
            speak("Sorry, say clearly like seven forty five")


# ================== VOICE COMMAND HANDLER ==================

def handle_command(cmd):
    if "play song" in cmd:
        play_music()
    elif "stop song" in cmd:
        pause_music()
    elif "play next" in cmd:
        next_track()
    elif "play previous" in cmd:
        prev_track()

    elif "exit" in cmd:
        speak("Goodbye")
        sys.exit(0)
    

    elif cmd.startswith("play"):
        play_song_search(cmd.replace("play", "").strip())

    elif "set alarm" in cmd:
        ensure_alarm_ready()
        time.sleep(1.5)
        set_alarm_smart()

    elif "open browser" in cmd or "open google" in cmd:
        action_open_browser()

    elif "open files" in cmd or "open file" in cmd:
        action_open_files()

    elif "open settings" in cmd or "system settings" in cmd:
        action_open_settings()

    elif "open calendar" in cmd or "set reminder" in cmd:
        action_open_calendar()

    
    
    else:
        speak("I didn't understand")



def voice_loop():
    speak("Nivea assistant is ready")

    while True:
        text = listen()
        if not text:
            continue

        if WAKE_WORD in text:
            command = text.replace(WAKE_WORD, "").strip()
            handle_command(command)
            time.sleep(0.5)



# ================== FLASK API ==================

@app.route("/api/spotify/status")
def spotify_status():
    try:
        sp = get_spotify_client()
        pb = sp.current_playback()

        if not pb or not pb.get("item"):
            return jsonify({
                "connected": True,
                "playing": False,
                "progress_ms": 0,
                "duration_ms": 0
            })

        item = pb["item"]
        device = pb.get("device", {})

        return jsonify({
            "connected": True,
            "playing": pb.get("is_playing", False),
            "song": item.get("name", ""),
            "artist": ", ".join(a["name"] for a in item.get("artists", [])),
            "album_art": item.get("album", {}).get("images", [{}])[0].get("url", ""),
            "device": device.get("name", "Unknown"),
            "progress_ms": pb.get("progress_ms", 0),
            "duration_ms": item.get("duration_ms", 0)
        })

    except Exception as e:
        print("Spotify status error:", e)
        return jsonify({"connected": False})

@app.route("/api/spotify/seek", methods=["POST"])
def spotify_seek():
    try:
        position_ms = request.json.get("position_ms")
        sp = get_spotify_client()
        sp.seek_track(position_ms)
        return jsonify({"ok": True})
    except Exception as e:
        print("Seek error:", e)
        return jsonify({"ok": False})

@app.route("/api/spotify/control", methods=["POST"])
def spotify_control():
    action = request.json["action"]
    if action == "playpause":
        play_music()
    elif action == "next":
        next_track()
    elif action == "prev":
        prev_track()
    return jsonify({"ok": True})

@app.route("/api/gita/random")
def gita_random():
    today = date.today().isoformat()

    # Load all shloks
    all_shloks = safe_load_json(ALL_GITA, [])

    # Load today file safely (supports old formats)
    today_data = safe_load_json(TODAY_GITA, {})

    # 🔁 Normalize structure (AUTO-FIX OLD FILES)
    if today_data.get("date") != today:
        today_data = {
            "date": today,
            "used_indexes": [],
            "shloks": []
        }

    if "used_indexes" not in today_data:
        today_data["used_indexes"] = []

    if "shloks" not in today_data:
        today_data["shloks"] = []

    used = set(today_data["used_indexes"])

    # Remaining shloks (by index, no ID needed)
    available = [
        (i, s) for i, s in enumerate(all_shloks)
        if i not in used
    ]

    if not available:
        return jsonify({"error": "No more shloks left for today"}), 404

    idx, shlok = random.choice(available)

    today_data["used_indexes"].append(idx)
    today_data["shloks"].append(shlok)

    # Save healed + updated file
    with open(TODAY_GITA, "w", encoding="utf-8") as f:
        json.dump(today_data, f, ensure_ascii=False, indent=2)

    return jsonify(shlok)

@app.route("/api/gita/today")
def gita_today():
    today = date.today().isoformat()

    data = safe_load_json(TODAY_GITA, {})

    if data.get("date") != today:
        return jsonify([])

    return jsonify(data.get("shloks", []))


# ================== SYSTEM ROUTES ==================

@app.route("/api/system/open-browser")
def api_open_browser():
    action_open_browser()
    return jsonify(ok=True)

@app.route("/api/system/open-files")
def open_files():
    speak("Opening files")

    # Use real Windows shortcut (MOST RELIABLE)
    pyautogui.hotkey("win", "e")

    time.sleep(0.5)

    # Safety: force focus if still behind
    for w in gw.getAllWindows():
        if "file explorer" in w.title.lower() or "this pc" in w.title.lower():
            try:
                w.restore()
                w.activate()
            except:
                pass

    return jsonify(ok=True)

@app.route("/api/system/open-settings")
def open_settings():
    speak("Opening settings")
    pyautogui.hotkey("win", "i")
    return jsonify(ok=True)

@app.route("/api/system/open-alarm")
def open_alarm():
    speak("Opening alarm")
    pyautogui.hotkey("win", "r")
    time.sleep(0.3)
    pyautogui.write("ms-clock:")
    pyautogui.press("enter")
    return jsonify(ok=True)

@app.route("/api/system/open-calendar")
def api_open_calendar():
    action_open_calendar()
    return jsonify(ok=True)



# ================== START EVERYTHING ==================



def start_flask():
    """Start Flask API server in background thread"""
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)

if __name__ == "__main__":
    # Start Flask API thread
    flask_thread = threading.Thread(target=start_flask, daemon=True)
    flask_thread.start()
    print("🚀 Flask API started on http://127.0.0.1:5000")
    
    # Start voice assistant
    time.sleep(2)  # Give Flask time to start
    voice_loop()




