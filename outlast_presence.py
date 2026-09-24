"""
I wanted to make a outlast trials DRP that didnt send all
your data to some weird asswebsite so here it is

i grabbed the trial names from the file with the languages
my brain so fucking fried bru but here yea have fun
"""

import logging
import os
import re
import sys
import threading
import time
import traceback
import winreg

import psutil
import pystray
from PIL import Image, ImageDraw



APPLICATION_ID = "1551054274543231167"
APP_NAME = "OutlastPresence"
POLL_INTERVAL = 3
LARGE_IMAGE = "outlast_logo"
LARGE_TEXT = "The Outlast Trials"
OUTLAST_EXE = "totclient-win64-shipping.exe"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"

LOG_PATH = os.path.join(
    os.environ.get("LOCALAPPDATA", ""),
    r"OPP\Saved\Logs\OPP.log",
)

FROZEN = getattr(sys, "frozen", False)
BASE_DIR = os.path.dirname(sys.executable if FROZEN else os.path.abspath(__file__))
LOG_FILE = os.path.join(BASE_DIR, "outlast_presence.log")

TRIAL_NAMES = {
    "PS_Trial":             "Kill The Snitch",
    "PS_Trial_Tutorial":    "Kill The Snitch",
    "PSA_MT01":             "Teach the Police Officer",
    "PSB_MT01":             "Cancel the Autopsy",
    "PSB_MT02":             "Sabotage the Lockdown",
    "PSB_MT03":             "Eliminate the Past",
    "PSO_MT01":             "Release the Prisoners",
    "PSO_MT02":             "Seize the Narcotics",
    "PS_Trial2":            "Exam: Kill The Snitch",
    "PS_Trial3":            "Final Exam: Kill The Snitch",

    "OR_Trial":             "Cleanse the Orphans",
    "OR_Trial2":            "Exam: Cleanse the Orphans",
    "ORS_MT01":             "Feed the Children",
    "ORS_MT02":             "Foster the Orphans",
    "ORS_MT03":             "Reunite the Family",
    "ORI_MT01":             "Gather the Children of God",

    "CH_Trial":             "Vindicate the Guilty",
    "CH_Trial2":            "Exam: Vindicate the Guilty",
    "CH_Trial3":            "Final Exam: Vindicate the Guilty",
    "CHA_MT01":             "Escape the Courthouse",
    "CHA_MT02":             "Destroy the Evidence",
    "CHA_MT03":             "Fuel the Release",
    "CHJ_MT01":             "Tilt The Scales of Justice",
    "CHJ_MT02":             "Sentence the Prosecuted",
    "CHJ_MT03":             "Bribe the Judges",

    "PF_Trial":             "Locksock the Warden",
    "PF_Trial_Tutorial":    "Locksock the Warden",

    "TF_Trial":             "Pervert the Futterman",
    "TF_Trial2":            "EXAM: Pervert the Futterman",
    "TFS_MT01":             "Crush the Sex Toys",
    "TFS_MT02":             "Incinerate the Sex Toys",
    "TFS_MT03":             "Fumigate the Factory",
    "TFW_MT01":             "Shutdown the Factory",
    "TFW_MT02":             "Flatten the Foreman",

    "FP_Trial":             "Grind the Bad Apples",
    "FP_Trial2":            "Exam: Grind the Bad Apples",
    "FPB_MT01":             "Punish the Miscreants",
    "FPB_MT02":             "Open the Gates",
    "FPB_MT03":             "Deface the Futtermans",
    "FPC_MT01":             "Drill the Futterman",
    "FPC_MT02":             "Redeem Your Freedom",
    "FPI_MT01":             "Beguile the Children",
    "FPI_MT02":             "Win the Truth",

    "SM_Trial":             "Kill the Politician",
    "SMC_MT01":             "Investigate the Minotaur",
    "SMC_MT02":             "Fabricate the Scandal",
    "SMC_MT03":             "Fund the Campaign",

    "SR_Trial":             "Liquidate the Union",
    "SRR_MT01":             "Get Out the Vote",
    "SRR_MT02":             "Disrupt the Neighborhood",
    "SRR_MT03":             "Eliminate the Legacy",

    "TS_Trial":             "Silence the Idol",
    "TSR_MT01":             "Cancel the Broadcast",
    "TSR_MT02":             "Change the Program",

    "DT_Trial":             "Pleasure the Prosecutor",
    "DTS_MT01":             "Kidnap the Mistress",
    "DTS_MT02":             "Spread the Disease",
    "DTS_MT03":             "Traffick the Product",

    "MH_Trial":             "Poison the Medicine",
    "MHS_MT01":             "Empty the Vault",
    "MHS_MT02":             "Poison the Cattle",
    "MHS_MT03":             "Stash the Contraband",
    "MHS_MT04":             "Cook the Informant",

    "RE_Trial":             "Despoil the Auction",
    "RES_MT01":             "Solve The Murder",
    "RES_MT02":             "Incinerate the Relic",

    "AE_Trial":             "ESCAPE",
    "AET_MT01":             "Escape the Lies",

    "TrialMansion":         "WELCOME",
}

DIFFICULTY_MAP = {
    "easy":      "Introductory",
    "normal":    "Standard",
    "hard":      "Intensive",
    "nightmare": "Psychosurgery",
}

RE_MAIN_MENU = re.compile(r'LoadMap\s*\(\s*/Game/Maps/Global/MainMenu', re.IGNORECASE)
RE_LOBBY = re.compile(r'LoadMap\s*\(\s*/Game/Maps/Lobby/Lobby_Persistent', re.IGNORECASE)
RE_MATCHMAKING = re.compile(r'"type"\s*:\s*"searching"', re.IGNORECASE)
RE_GAME_STAGE = re.compile(
    r'GameStageInfo changed\.'
    r'.*?Trial ID:\s*(?P<trial_id>\S+?),'
    r'.*?Program difficulty:\s*(?P<difficulty>\w+),'
    r'.*?EffectiveNumberOfPlayers:\s*(?P<players>\d+)',
    re.IGNORECASE,
)
RE_STAGE_READY = re.compile(
    r'StageReady\.\s*Trial ID:\s*(?P<trial_id>\S+?),'
    r'.*?Mission:\s*(?P<mission>\S+?),'
    r'.*?ENbPlayer:\s*(?P<players>\d+)',
    re.IGNORECASE,
)
RE_INVASION = re.compile(r'"invasionState"\s*:\s*"([^"]+)"')
RE_ESCALATION = re.compile(r'"trialChain"\s*:\s*([\d.]+)')
RE_RETURNING = re.compile(r'"presenceState"\s*:\s*"returningtolobby"', re.IGNORECASE)

INVASION_OFF_VALUES = ("-", "Disabled", "disabled", "none", "None")


class GameState:
    def __init__(self):
        self.reset()

    def reset(self):
        self.screen = "menu"
        self.trial_name = ""
        self.difficulty = ""
        self.player_count = 0
        self.escalation_step = 0
        self.invasion = False
        self._invasion_buf = 0
        self._escalation_buf = 0

    def to_discord(self):
        if self.screen == "menu":
            return "Main Menu", None
        if self.screen == "matchmaking":
            return "Awaiting...", None
        if self.screen == "lobby":
            players = f"{self.player_count}/4 players" if self.player_count else None
            return "In the Sleep Room", players

        name = self.trial_name or "In a Trial"
        parts = []

        if self.screen == "tram":
            if self.difficulty:
                parts.append(self.difficulty)
            if self.player_count:
                parts.append(f"{self.player_count}/4 players")
            return f"Shuttle | {name}", " · ".join(parts) or None

        if self.escalation_step:
            parts.append(f"Escalation — Step {self.escalation_step}")
        elif self.difficulty:
            parts.append(self.difficulty)
        if self.invasion:
            parts.append("Invasion")
        if self.player_count:
            parts.append(f"{self.player_count}/4 players")
        return name, " · ".join(parts) or None

    def status_text(self):
        details, state_str = self.to_discord()
        return f"{details} — {state_str}" if state_str else details

def check_for_updates():
    """Silently check GitHub for a newer release and auto-update if found."""
    try:
        import urllib.request
        import json
        import subprocess

        url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
        req = urllib.request.Request(url, headers={"User-Agent": "OutlastPresence"})
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read())

        latest = data["tag_name"].lstrip("v")
        if latest <= VERSION:
            return  # already up to date

        logging.info(f"Update available: v{latest} (current: v{VERSION})")

        # Find the exe asset
        exe_url = None
        for asset in data.get("assets", []):
            if asset["name"].endswith(".exe"):
                exe_url = asset["browser_download_url"]
                break

        if not exe_url:
            return

        # Download new exe next to current one
        current_exe = sys.executable if getattr(sys, "frozen", False) else None
        if not current_exe:
            return  # only auto-update when running as exe

        new_exe = current_exe + ".new"
        urllib.request.urlretrieve(exe_url, new_exe)

        # Write a small batch file that swaps the exe and restarts
        bat = current_exe + "_update.bat"
        with open(bat, "w") as f:
            f.write(f"""@echo off
timeout /t 2 /nobreak >nul
move /y "{new_exe}" "{current_exe}"
start "" "{current_exe}"
del "%~f0"
""")

        logging.info("Update downloaded — applying on restart.")
        subprocess.Popen(bat, shell=True)
        sys.exit(0)  # exit so the batch file can replace the exe

    except Exception as e:
        logging.warning(f"Update check failed: {e}")

def resolve_trial(mission_id):
    if mission_id in TRIAL_NAMES:
        return TRIAL_NAMES[mission_id]

    base = mission_id.replace("_Tutorial", "")
    if base in TRIAL_NAMES:
        return TRIAL_NAMES[base]

    for key, name in TRIAL_NAMES.items():
        if mission_id.upper().startswith(key.upper()):
            return name
    return mission_id


def update_invasion(line, state):
    match = RE_INVASION.search(line)
    if not match:
        return False

    if match.group(1) in INVASION_OFF_VALUES:
        state._invasion_buf = 0
        if state.invasion:
            state.invasion = False
            return True
        return False

    state._invasion_buf += 1
    if state._invasion_buf >= 2 and not state.invasion:
        state.invasion = True
        return True
    return False


def update_escalation(line, state):
    match = RE_ESCALATION.search(line)
    if not match:
        return False

    step = int(float(match.group(1)))
    if step <= 0:
        state._escalation_buf = 0
        if state.escalation_step != 0:
            state.escalation_step = 0
            return True
        return False

    state._escalation_buf += 1
    if state._escalation_buf >= 2 and state.escalation_step != step:
        state.escalation_step = step
        return True
    return False


def process_line(line, state):
    if RE_MAIN_MENU.search(line):
        if state.screen != "menu":
            state.reset()
            return True
        return False

    if RE_LOBBY.search(line):
        if state.screen != "lobby":
            state.screen = "lobby"
            state.trial_name = ""
            return True
        return False

    if RE_MATCHMAKING.search(line) and state.screen in ("menu", "lobby"):
        if state.screen != "matchmaking":
            state.screen = "matchmaking"
            return True
        return False

    match = RE_GAME_STAGE.search(line)
    if match:
        difficulty = match.group("difficulty")
        state.screen = "tram"
        state.trial_name = resolve_trial(match.group("trial_id"))
        state.difficulty = DIFFICULTY_MAP.get(difficulty.lower(), difficulty.title())
        state.player_count = int(match.group("players"))
        return True

    match = RE_STAGE_READY.search(line)
    if match:
        state.screen = "trial"
        state.trial_name = resolve_trial(match.group("mission"))
        state.player_count = int(match.group("players"))
        return True

    if RE_RETURNING.search(line) and state.screen not in ("lobby", "menu"):
        state.screen = "lobby"
        state.trial_name = ""
        return True

    if "invasionState" in line or "trialChain" in line:
        invasion_changed = update_invasion(line, state)
        escalation_changed = update_escalation(line, state)
        return invasion_changed or escalation_changed

    return False


def get_launch_command():
    if FROZEN:
        return f'"{sys.executable}"'
    pythonw = sys.executable.replace("python.exe", "pythonw.exe")
    python = pythonw if os.path.exists(pythonw) else sys.executable
    return f'"{python}" "{os.path.abspath(__file__)}"'


def is_registered():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ) as key:
            winreg.QueryValueEx(key, APP_NAME)
        return True
    except Exception:
        return False


def register_startup():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, get_launch_command())
        logging.info("Registered for startup.")
    except Exception as e:
        logging.warning(f"Could not register for startup: {e}")


def unregister_startup():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, APP_NAME)
        logging.info("Removed from startup.")
    except FileNotFoundError:
        pass
    except Exception as e:
        logging.warning(f"Could not remove from startup: {e}")


def make_tray_icon():
    ico_path = os.path.join(BASE_DIR, "outlast.ico")
    if os.path.exists(ico_path):
        return Image.open(ico_path).convert("RGBA")

    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([2, 2, 62, 62], fill=(30, 10, 10, 255))
    draw.line([16, 16, 48, 48], fill=(200, 30, 30, 255), width=7)
    draw.line([48, 16, 16, 48], fill=(200, 30, 30, 255), width=7)
    return img


def build_tray(state_ref, stop_event):
    def on_status(icon, item):
        icon.notify(state_ref["state"].status_text(), "Outlast Presence")

    def on_uninstall(icon, item):
        unregister_startup()
        icon.notify("Removed from startup. Close this to stop.", "Outlast Presence")

    def on_exit(icon, item):
        unregister_startup()
        stop_event.set()
        icon.stop()

    menu = pystray.Menu(
        pystray.MenuItem("Outlast Trials Presence", None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Current Status", on_status),
        pystray.MenuItem("Uninstall from Startup", on_uninstall),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Exit", on_exit),
    )
    return pystray.Icon(APP_NAME, make_tray_icon(), "Outlast Presence", menu)


def connect_discord():
    from pypresence import Presence
    rpc = Presence(APPLICATION_ID)
    rpc.connect()
    return rpc


def push_to_discord(rpc, state, start_time):
    details, state_str = state.to_discord()
    kwargs = dict(
        details=details,
        start=int(start_time),
        large_image=LARGE_IMAGE,
        large_text=LARGE_TEXT,
    )
    if state_str:
        kwargs["state"] = state_str
    rpc.update(**kwargs)
    logging.info(f"Status: {details}{' — ' + state_str if state_str else ''}")


def is_outlast_running():
    for proc in psutil.process_iter(["name"]):
        try:
            if proc.info["name"] and OUTLAST_EXE in proc.info["name"].lower():
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return False


def catch_up_on_log(state):
    if not os.path.exists(LOG_PATH):
        logging.warning("Log not found. Add -log to Steam launch options.")
        return 0

    try:
        # Find when the game process actually started
        game_start_time = None
        for proc in psutil.process_iter(["name", "create_time"]):
            try:
                if proc.info["name"] and OUTLAST_EXE in proc.info["name"].lower():
                    game_start_time = proc.info["create_time"]
                    break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        log_mtime = os.path.getmtime(LOG_PATH)

        if game_start_time and log_mtime < game_start_time:
            # Log is from a previous session / skip to end
            with open(LOG_PATH, "r", encoding="utf-8", errors="replace") as f:
                f.seek(0, 2)
                pos = f.tell()
            logging.info("Old log detected — waiting for fresh entries.")
            return pos
        else:
            # Log is current / read from start to catch current state
            with open(LOG_PATH, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    process_line(line, state)
                pos = f.tell()
            logging.info(f"Log caught up — state: {state.screen}")
            return pos

    except Exception as e:
        logging.warning(f"Log catch-up error: {e}")
        return 0


def read_new_lines(log_pos):
    with open(LOG_PATH, "r", encoding="utf-8", errors="replace") as f:
        f.seek(log_pos)
        lines = f.readlines()
        return lines, f.tell()


def run_loop(state_ref, stop_event):
    logging.info("Outlast Presence running. Waiting for game...")

    state = GameState()
    state_ref["state"] = state
    rpc = None
    in_game = False
    start_time = None
    log_pos = 0

    while not stop_event.is_set():
        try:
            game_running = is_outlast_running()

            if game_running and not in_game:
                logging.info("The Outlast Trials detected!")
                in_game = True
                start_time = time.time()
                state.reset()
                log_pos = catch_up_on_log(state)

                try:
                    rpc = connect_discord()
                    push_to_discord(rpc, state, start_time)
                except Exception as e:
                    logging.warning(f"Discord connect failed: {e}")

            if game_running and in_game and os.path.exists(LOG_PATH):
                try:
                    new_lines, log_pos = read_new_lines(log_pos)

                    if any(process_line(line, state) for line in new_lines) and rpc:
                        try:
                            push_to_discord(rpc, state, start_time)
                        except Exception as e:
                            logging.warning(f"Discord push failed: {e} — reconnecting...")
                            try:
                                rpc = connect_discord()
                                push_to_discord(rpc, state, start_time)
                            except Exception:
                                pass
                except Exception as e:
                    logging.warning(f"Log read error: {e}")

            elif not game_running and in_game:
                logging.info("The Outlast Trials closed.")
                if rpc:
                    try:
                        rpc.clear()
                        rpc.close()
                    except Exception:
                        pass
                    rpc = None
                in_game = False
                state.reset()
                log_pos = 0

        except Exception as e:
            logging.error(f"Unexpected error: {e}")

        time.sleep(POLL_INTERVAL)


def main():
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    if not is_registered():
        register_startup()

    stop_event = threading.Event()
    state_ref = {"state": GameState()}

    threading.Thread(
        target=run_loop,
        args=(state_ref, stop_event),
        daemon=True,
    ).start()

    build_tray(state_ref, stop_event).run()
    check_for_updates()

if __name__ == "__main__":
    try:
        main()
    except Exception:
        with open(os.path.join(BASE_DIR, "crash.log"), "w") as f:
            f.write(traceback.format_exc())
