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
import ctypes
import pyautogui
import pyttsx3
import re
import glob
import subprocess
import os
import requests
from sympy import sympify, SympifyError
import pywhatkit as pwk 
from pathlib import Path
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
whatsapp_active = False
voice_state = "idle"  # idle | listening | thinking | speaking
current_insight = "It’s quiet right now. I’m here if you need me."
last_heartbeat = time.time()
opened_apps = set()



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
    global voice_state, current_insight

    voice_state = "speaking"
    current_insight = "Speaking."

    print("Assistant:", text)

    try:
        engine = pyttsx3.init("sapi5")
        engine.setProperty("rate", 175)
        engine.setProperty("volume", 1.0)

        voices = engine.getProperty("voices")
        voice_index = 1 if len(voices) > 1 else 0
        engine.setProperty("voice", voices[voice_index].id)

        engine.say(text)
        engine.runAndWait()
        engine.stop()

    except Exception as e:
        print("TTS error:", e)

    finally:
        voice_state = "idle"
        current_insight = "Waiting."

recognizer = sr.Recognizer()
mic = sr.Microphone()

def listen() -> str:
    global voice_state, current_insight

    try:
        # 🎧 LISTENING
        voice_state = "listening"
        current_insight = "I’m listening."

        recognizer.energy_threshold = 300
        recognizer.dynamic_energy_threshold = True

        with mic as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.3)
            audio = recognizer.listen(
                source,
                timeout=4,
                phrase_time_limit=4
            )

        # 🧠 THINKING
        voice_state = "thinking"
        current_insight = "Thinking…"

        text = recognizer.recognize_google(
            audio,
            language="en-IN"
        ).lower()

        print("You:", text)
        return text

    except WaitTimeoutError:
        voice_state = "idle"
        current_insight = "It’s quiet right now. I’m here."
        return ""

    except Exception as e:
        print("Recognition error:", e)
        voice_state = "idle"
        current_insight = "I couldn’t hear clearly. Waiting."
        return ""

# ================== CONFIG ==================
SPOTIFY_CLIENT_ID = ""
SPOTIFY_CLIENT_SECRET = ""
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
    opened_apps.add("msedge")

def action_open_files():
    speak("Opening files")
    os.startfile("explorer")
    opened_apps.add("explorer")

def action_open_settings():
    speak("Opening settings")
    os.system("start ms-settings:")

def action_open_calendar():
    speak("Opening calendar")
    webbrowser.open("https://calendar.google.com")

# ================== FILE HANDLING ==================
def smart_file_search(query):
    """Open ANY file using Windows Search (100% reliable)"""
    try:
        # Win+S → Type filename → Enter (exactly like manual)
        pyautogui.hotkey("win", "s")
        time.sleep(0.3)
        pyautogui.write(query)
        time.sleep(0.8)  # Wait for file results
        pyautogui.press("enter")
        return True
    except:
        return False

def handle_file_open(cmd):
    """Handle file open via Windows Search"""
    query = cmd.replace("open", "").replace("file", "").strip()
    speak(f"Searching for {query}")
    
    if smart_file_search(query):
        speak(f"Opening {query}")
    else:
        speak(f"Could not find {query}")

# ================== APP LAUNCHER ==================

def smart_open(query): 
    #speak(f"Opening {query}") 
    try: 
        pyautogui.hotkey("win", "s") 
        time.sleep(0.3) 
        pyautogui.write(query) 
        time.sleep(0.8) 
        pyautogui.press("enter") 
        return True 
    except: 
        return False

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

# ================== VOLUME CONTROL ==================
def handle_volume(cmd):
    if "volume up" in cmd or "volume higher" in cmd:
        for _ in range(2):
            pyautogui.press("volumeup")
        speak("Volume up")
    elif "volume down" in cmd or "volume lower" in cmd:
        for _ in range(2):
            pyautogui.press("volumedown")
        speak("Volume down")
    elif "mute" in cmd or "volume off" in cmd:
        pyautogui.press("volumemute")
        speak("Volume muted")
    elif "unmute" in cmd:
        pyautogui.press("volumemute")
        speak("Volume unmuted")

# ================== WEATHER ==================
def handle_weather(cmd):
    """Open Weather app via Windows Search"""
    speak("Opening weather")
    
    # Win+S → "weather" → Enter (opens your Weather app)
    pyautogui.hotkey("win", "s")
    time.sleep(0.3)
    pyautogui.write("weather")
    time.sleep(0.8)  # Wait for Weather app result
    pyautogui.press("enter")
    
    # Optional: say city for context
    city = re.search(r"(?:in\s+)?([a-zA-Z\s]+?)(?:\s|$)", cmd)
    if city:
        speak(f"Weather for {city.group(1)}")

# ================== SHOPPING ==================
def handle_shopping(cmd):
    query = cmd.replace("buy", "").replace("price", "").strip()
    speak(f"Searching {query} prices")
    pwk.search(f"buy {query} amazon flipkart")

# ================== GIT CONTROLLER ==================


class GitVoice:
    def __init__(self):
        self.repo_path = Path.home() / "Desktop" / "face_recognition_flask-main"  # Default repo
        
    def run_git(self, *args):
        """Run git command and return output"""
        try:
            result = subprocess.run(
                ["git", *args], 
                cwd=self.repo_path,
                capture_output=True, 
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            print(f"Git error: {e.stderr}")
            return None
    
    def status(self):
        status = self.run_git("status", "--short")
        speak(f"Git status: {status or 'clean'}")
    
    def add_all(self):
        self.run_git("add", ".")
        speak("All changes staged")
    
    def commit(self, message):
        self.run_git("commit", "-m", message)
        speak(f"Committed: {message}")
    
    def push(self):
        self.run_git("push")
        speak("Pushed to remote")
    
    def pull(self):
        self.run_git("pull")
        speak("Pulled latest changes")
    
    def new_branch(self, branch_name):
        self.run_git("checkout", "-b", branch_name)
        speak(f"Created branch {branch_name}")
    
    def switch_branch(self, branch_name):
        self.run_git("checkout", branch_name)
        speak(f"Switched to {branch_name}")

git = GitVoice()

def handle_git(cmd):
    cmd_lower = cmd.lower()
    
    # Check for Git variants FIRST
    git_variants = ["git", "geet", "g i t", "commit", "branch", "push", "pull", "status"]
    if any(variant in cmd_lower for variant in git_variants):
        
        # Clean pronunciation
        clean_cmd = re.sub(r'(geet|g i t)', 'git', cmd_lower)
        print(f"✅ Git detected: {clean_cmd}")  # Debug
        
        # Execute Git command
        if "status" in clean_cmd:
            git.status()
        elif "add all" in clean_cmd or "stage all" in clean_cmd:
            git.add_all()
        elif "commit" in clean_cmd:
            msg = cmd.replace("commit", "").replace("git", "").replace("geet", "").strip() or "Voice commit"
            git.commit(msg)
        elif "push" in clean_cmd:
            git.push()
        elif "pull" in clean_cmd:
            git.pull()
        elif "new branch" in clean_cmd:
            branch = cmd.replace("new branch", "").strip() or "feature"
            git.new_branch(branch)
        elif "switch branch" in clean_cmd:
            branch = cmd.replace("switch branch", "").strip()
            git.switch_branch(branch)
        else:
            git.status()  # Default: show status
        
        return True  # ✅ STOP here - Git handled!
    
    return False  # Not a Git command

# ================== WHATSAPP HANDLER ==================
def open_whatsapp():
    global whatsapp_active

    if whatsapp_active:
        return  # 🔥 already open, do nothing

    speak("Opening WhatsApp")
    smart_open("whatsapp")
    whatsapp_active = True
    opened_apps.add("whatsapp")

def whatsapp_search_contact(name):
    speak(f"Searching contact {name}")

    # Open search
    pyautogui.hotkey("ctrl", "f")
    time.sleep(0.4)

    # 🔥 CLEAR OLD SEARCH TEXT (CRITICAL FIX)
    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.1)
    pyautogui.press("backspace")
    time.sleep(0.2)

    # Type new contact name
    pyautogui.write(name, interval=0.05)
    time.sleep(1)

    # Open chat
    pyautogui.press("enter")
    time.sleep(1)

def whatsapp_type_message(message):
    pyautogui.write(message, interval=0.03)
    time.sleep(0.5)

def whatsapp_send_message():
    pyautogui.press("enter")

def listen_for_message(max_retries=3):
    for attempt in range(max_retries):
        message = listen()
        if message:
            return message
        speak("I did not catch that. Please repeat the message.")
    return None

def handle_whatsapp_message_flow(contact_name):
    open_whatsapp()
    whatsapp_search_contact(contact_name)

    speak("What message should I send?")

    message = listen_for_message()

    if not message:
        speak("Still no message heard. Cancelling.")
        return

    whatsapp_type_message(message)
    whatsapp_send_message()
    speak("Message sent successfully")


# ================== THEME + BRIGHTNESS ==================
def set_windows_theme(mode):
    # 0 = dark, 1 = light
    value = "0" if mode == "dark" else "1"

    subprocess.run([
        "reg", "add",
        "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize",
        "/v", "AppsUseLightTheme",
        "/t", "REG_DWORD",
        "/d", value,
        "/f"
    ], shell=True)

    subprocess.run([
        "reg", "add",
        "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize",
        "/v", "SystemUsesLightTheme",
        "/t", "REG_DWORD",
        "/d", value,
        "/f"
    ], shell=True)

    # 🔥 FORCE WINDOWS TO REFRESH THEME
    ctypes.windll.user32.SendMessageTimeoutW(
        0xFFFF, 0x1A, 0, "ImmersiveColorSet",
        0x2, 100, None
    )

    # Restart explorer for guaranteed apply
    subprocess.run("taskkill /f /im explorer.exe", shell=True)
    subprocess.run("start explorer", shell=True)

def set_brightness(percent):
    percent = max(0, min(100, int(percent)))
    c = wmi.WMI(namespace='wmi')
    methods = c.WmiMonitorBrightnessMethods()

    if methods:
        methods[0].WmiSetBrightness(percent, 0)

# ================== CLOSING APPS ==================
def close_app(name=None):
    if name:
        speak(f"Closing {name}")
        try:
            os.system(f"taskkill /IM {name}.exe /F")
        except:
            speak(f"Could not close {name}")
    else:
        speak("Closing current app")
        pyautogui.hotkey("alt", "f4")

def handle_close_command(cmd):
    cmd = cmd.lower()

    app_map = {
        "browser": "msedge",
        "edge": "msedge",
        "chrome": "chrome",
        "files": "explorer",
        "file explorer": "explorer",
        "spotify": "spotify",
        "whatsapp": "whatsapp",
        "settings": "SystemSettings"
    }

    # 🔥 Close everything (explicit only)
    if "close everything" in cmd or "close all" in cmd:
        speak("Closing all opened applications")
        for app in list(opened_apps):
            os.system(f"taskkill /IM {app}.exe /F")
        opened_apps.clear()
        return True

    # 🔍 Close specific app
    for key, exe in app_map.items():
        if f"close {key}" in cmd:
            close_app(exe)
            opened_apps.discard(exe)
            return True

    # 🪟 Close current window
    if "close" in cmd:
        close_app()
        return True

    return False

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

    # OPEN INSTAGRAM (new)
    elif "open instagram" in cmd or "instagram" == cmd.strip():
        speak("Opening Instagram.")
        webbrowser.open("https://www.instagram.com")    
    
    elif "open gemini" in cmd:
        speak("Opening Gemini.")
        webbrowser.get("edge").open("https://gemini.google.com/")

    # Volume
    elif any(word in cmd for word in ["volume", "mute", "unmute"]):
        handle_volume(cmd)
        return

    # Shopping
    elif "buy" in cmd or "price" in cmd:
        handle_shopping(cmd)
        return

    # Weather
    elif "weather" in cmd:
        handle_weather(cmd)
        return

    # Git commands
    elif "geet" in cmd or "branch" in cmd or "commit" in cmd:
        handle_git(cmd)
        return

    elif "open whatsapp" in cmd:
        open_whatsapp()

    elif "send message to" in cmd:
        name = cmd.replace("send message to", "").strip()
        if name:
            handle_whatsapp_message_flow(name)
        else:
            speak("Whom should I message?")


    elif "close whatsapp" in cmd:
        global whatsapp_active
        speak("Closing WhatsApp")
        pyautogui.hotkey("alt", "f4")
        whatsapp_active = False

    # CLOSE COMMANDS
    if "close" in cmd:
        if handle_close_command(cmd):
            return


    elif "dark mod" in cmd:
        set_windows_theme("dark")
        speak("Dark mode enabled")

    elif "light mod" in cmd or "bright mode" in cmd:
        set_windows_theme("light")
        speak("Light mode enabled")

    elif "brightness" in cmd and "set" in cmd:
        match = re.search(r'(\d{1,3})', cmd)
        if match:
            level = int(match.group(1))
            set_brightness(level)
            speak(f"Brightness set to {level} percent")
        else:
            speak("Please say a brightness value")


    elif "weather" in cmd:
        pyautogui.hotkey("win", "s")
        time.sleep(0.4)
        pyautogui.write("weather")
        time.sleep(0.8)
        pyautogui.press("enter")










    elif "open google" in cmd:
        speak("Opening Google on Edge.")
        webbrowser.get("edge").open("https://www.google.com")

    elif "search for" in cmd:
        query = cmd.split("search for", 1)[1].strip()
        if query:
            speak(f"Searching for {query} on Google.")
            webbrowser.get("edge").open(
                f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}"
            )
        else:
            speak("What should I search for?")

    # ALL "open" commands
    elif cmd.startswith("open "):
        query = cmd.replace("open", "").strip()
        if smart_open(query):
            speak(f"Opening {query}")
        else:
            speak(f"Could not find {query}")
        return

    else:
        speak("I didn't understand")

# ================== VOICE LOOP ==================

def voice_loop():
    global last_heartbeat
    speak("Nivea assistant is ready")

    while True:
        last_heartbeat = time.time()   # ❤️ heartbeat tick

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

@app.route("/api/voice/state")
def get_voice_state():
    return jsonify({
        "state": voice_state
    })

@app.route("/api/heart")
def heart_status():
    alive = (time.time() - last_heartbeat) < 3  # 3 sec tolerance
    return jsonify({
        "alive": alive,
        "voice_state": voice_state
    })

@app.route("/api/system/open-weather")
def open_weather():
    speak("Opening weather")

    pyautogui.hotkey("win", "s")
    time.sleep(0.4)
    pyautogui.write("weather")
    time.sleep(0.8)
    pyautogui.press("enter")

    return jsonify(ok=True)


@app.route("/api/system/brightness", methods=["POST"])
def api_brightness():
    data = request.json or {}
    action = data.get("action")
    value = data.get("value")

    if action == "up":
        pyautogui.press("brightnessup")
        speak("Brightness increased")

    elif action == "down":
        pyautogui.press("brightnessdown")
        speak("Brightness decreased")

    elif action == "set" and value is not None:
        for _ in range(100):
            pyautogui.press("brightnessdown")
        for _ in range(int(value)):
            pyautogui.press("brightnessup")
        speak(f"Brightness set to {value} percent")

    return jsonify(ok=True)

@app.route("/api/system/theme", methods=["POST"])
def system_theme():
    theme = request.json.get("theme")

    if theme in ("dark", "light"):
        set_windows_theme(theme)
        speak(f"{theme.capitalize()} mode enabled")

    return jsonify(ok=True)



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





