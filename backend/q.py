import os
import time
import speech_recognition as sr
import pyttsx3
from speech_recognition import WaitTimeoutError

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
    with mic as source:
        print("Listening...")
        recognizer.adjust_for_ambient_noise(source, duration=0.8)
        try:
            audio = recognizer.listen(source, timeout=7, phrase_time_limit=7)
        except WaitTimeoutError:
            print("Listening timed out, no speech.")
            return ""

    try:
        text = recognizer.recognize_google(audio, language="en-IN").lower()
        print("You:", text)
        return text
    except Exception as e:
        print("Recognition error:", e)
        return ""


def handle_command(cmd: str):
    if "open files" in cmd:
        speak("Opening files")
        time.sleep(0.3)
        os.startfile("explorer")

    elif "open settings" in cmd:
        speak("Opening settings")
        time.sleep(0.3)
        os.system("start ms-settings:")

    elif cmd.strip() == "":
        speak("Yes, I am listening.")
    else:
        speak("I did not understand")


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


if __name__ == "__main__":
    voice_loop()










'''

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
    pyautogui.hotkey("win", "up")
    time.sleep(0.8)
    
    # Go to Alarm tab
    try:
        click("alarm_tab", delay=1.0)
        speak("Alarm section ready")
    except:
        speak("Opening alarm section")
        pyautogui.click(80, 200)  # fallback alarm tab position
        time.sleep(0.8)

def set_alarm_ui(hour, minute):
    """Set exact time using calibrated positions"""
    speak(f"Setting {hour}:{minute:02d}")
    
    # Hour field
    click("hour_field")
    pyautogui.hotkey("ctrl", "a")  # select all
    pyautogui.write(str(hour))
    time.sleep(0.2)
    
    # Minute field  
    click("minute_field")
    pyautogui.hotkey("ctrl", "a")
    pyautogui.write(f"{minute:02d}")
    time.sleep(0.2)
    
    # Save
    click("save_button", delay=0.3)

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

'''