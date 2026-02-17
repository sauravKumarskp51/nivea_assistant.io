import pyautogui
import json
import time
import keyboard  # pip install keyboard
import os


# SAFETY FIRST
pyautogui.FAILSAFE = True  # Move mouse to corner to abort
pyautogui.PAUSE = 0.1

positions = {}

def wait_and_capture(name, instructions=""):
    """Capture position with exact instructions"""
    print(f"\n{'='*60}")
    print(f"🎯 CAPTURE: {name.upper()}")
    print(f"{'='*60}")
    if instructions:
        print(instructions)
    print("\n👉 Move mouse EXACTLY to target")
    print("✅ Press F8 to capture")
    print("❌ ESC to skip / restart")
    print("📍 Current position will show below")
    
    while True:
        print(f"\n📍 Mouse at: {pyautogui.position()}")
        event = keyboard.read_event()
        
        if event.event_type == keyboard.KEY_DOWN:
            if event.name == "f8":
                x, y = pyautogui.position()
                positions[name] = {"x": x, "y": y}
                print(f"✅ {name} SAVED at x={x}, y={y}")
                time.sleep(1)
                break
            elif event.name == "esc":
                print("❌ Skipped")
                return False
        time.sleep(0.1)

def verify_positions():
    """Verify all positions are reasonable"""
    print("\n🔍 VERIFYING POSITIONS...")
    for name, pos in positions.items():
        print(f"  {name}: ({pos['x']}, {pos['y']})")
    
    print("\n✅ All positions look good? (y/n)")
    return input().lower() == 'y'

print("\n🛠️  EXACT ALARM CALIBRATION TOOL")
print("📋 Follow EVERY step precisely")
print("🖱️  Move mouse SLOWLY to exact center of target")
print("-" * 60)

# STEP 0: Safety check
print("\n🔒 SAFETY: Move mouse to top-left corner if anything goes wrong")
input("Press ENTER to start...")

# STEP 1: Open Clock App
print("\n🚀 STEP 1: OPEN CLOCK APP")
pyautogui.hotkey("win", "r")
time.sleep(0.5)
pyautogui.write("ms-clock:")
pyautogui.press("enter")
print("⏳ Waiting 4 seconds for Clock to load...")
time.sleep(4)

# STEP 2: Alarm Tab (left sidebar)
wait_and_capture(
    "alarm_tab",
    """📍 HOVER EXACTLY over the ALARM tab icon in LEFT sidebar
    🎯 Should be 2nd/3rd icon from top (clock bell icon)
    📏 Usually around x=50-100, y=150-250"""
)

# STEP 3: Add Alarm Button (+)
print("\n➕ STEP 3: CLICK '+' BUTTON MANUALLY")
print("👆 Click the large BLUE '+' button at top-right")
input("Press ENTER after 'Add new alarm' popup appears...")

# STEP 4: Hour Field
wait_and_capture(
    "hour_field",
    """📍 HOVER EXACTLY in CENTER of HOUR number field
    🎯 Left number box in popup (should highlight when hovered)
    📏 Usually x=400-500, y=200-300"""
)

# STEP 5: Minute Field  
wait_and_capture(
    "minute_field",
    """📍 HOVER EXACTLY in CENTER of MINUTE number field
    🎯 Right number box next to hour (should highlight)
    📏 Usually x=500-600, y=200-300"""
)

# STEP 6: AM/PM Toggle (OPTIONAL but recommended)
print("\n🕐 STEP 6: AM/PM TOGGLE (Optional)")
use_ampm = input("Do you want AM/PM toggle? (y/n): ").lower() == 'y'
if use_ampm:
    print("👆 Click AM/PM toggle button first, then hover exactly over it")
    input("Press ENTER after clicking toggle...")
    wait_and_capture(
        "am_pm_toggle",
        """📍 HOVER EXACTLY over AM/PM toggle button center
        🎯 Should show current AM/PM state when hovered"""
    )

# STEP 7: Save Button
wait_and_capture(
    "save_button",
    """📍 HOVER EXACTLY in CENTER of blue SAVE button
    🎯 Bottom-right of popup (says 'Save')
    📏 Usually x=500-600, y=350-450"""
)

# Add these to your calibration script AFTER save_button:
print("\n🔢 STEP 8: ALARM BOXES (Click each existing alarm)")
for i in range(1, 5):
    wait_and_capture(
        f"alarm_box_{i}",
        f"""📍 Click EXISTING ALARM BOX #{i}
        🎯 {i}th alarm slot from top (7:00, 8:01, etc.)
        📏 Usually x=300-500, y=200+ per box"""
    )

# FINAL VERIFICATION
if verify_positions():
    # Save with backup
    backup_file = "alarm_positions_backup.json"
    if os.path.exists(backup_file):
        os.remove(backup_file)
    
    with open("alarm_positions.json", "w") as f:
        json.dump(positions, f, indent=2)
    
    with open(backup_file, "w") as f:
        json.dump(positions, f, indent=2)
    
    print(f"\n🎉 SUCCESS! Saved to alarm_positions.json + {backup_file}")
    print("\n📱 Test your assistant: 'nivea set alarm'")
else:
    print("\n⚠️  Verification failed. Restart calibration.")
