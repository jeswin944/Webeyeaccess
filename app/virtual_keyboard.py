import tkinter as tk
import pyautogui
import ctypes
import time


# ============================================================
# WINDOWS API
# ============================================================

user32 = ctypes.windll.user32

GWL_EXSTYLE = -20

WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOOLWINDOW = 0x00000080

SW_SHOWNOACTIVATE = 4


def get_foreground_window():
    return user32.GetForegroundWindow()


def get_window_title(hwnd):

    if not hwnd:
        return ""

    try:

        length = user32.GetWindowTextLengthW(hwnd)

        if length == 0:
            return ""

        buffer = ctypes.create_unicode_buffer(
            length + 1
        )

        user32.GetWindowTextW(
            hwnd,
            buffer,
            length + 1
        )

        return buffer.value

    except Exception:

        return ""


def activate_window(hwnd):

    if not hwnd:
        return

    try:

        user32.ShowWindow(
            hwnd,
            SW_SHOWNOACTIVATE
        )

        user32.SetForegroundWindow(
            hwnd
        )

    except Exception:

        pass


# ============================================================
# WEBEYE VIRTUAL KEYBOARD
# ============================================================

class WebEyeVirtualKeyboard:

    def __init__(self):

        # ----------------------------------------------------
        # Main window
        # ----------------------------------------------------

        self.root = tk.Tk()

        self.root.withdraw()

        self.root.overrideredirect(True)

        self.root.configure(
            bg="#15161c"
        )

        self.root.attributes(
            "-topmost",
            True
        )

        # ----------------------------------------------------
        # State
        # ----------------------------------------------------

        self.shift_on = False

        self.target_window = None

        self.keyboard_visible = False

        self.last_new_tab_state = False

        # ----------------------------------------------------
        # Screen
        # ----------------------------------------------------

        self.screen_width = (
            self.root.winfo_screenwidth()
        )

        self.screen_height = (
            self.root.winfo_screenheight()
        )

        # ----------------------------------------------------
        # Keyboard size
        # ----------------------------------------------------

        self.keyboard_width = min(
            900,
            self.screen_width - 40
        )

        self.keyboard_height = 360

        # ----------------------------------------------------
        # Build keyboard
        # ----------------------------------------------------

        self.create_keyboard()

        # ----------------------------------------------------
        # Configure Windows overlay
        # ----------------------------------------------------

        self.root.after(
            300,
            self.configure_overlay
        )

        # ----------------------------------------------------
        # Monitor Chrome
        # ----------------------------------------------------

        self.root.after(
            500,
            self.monitor_chrome
        )

    # ========================================================
    # Configure overlay window
    # ========================================================

    def configure_overlay(self):

        try:

            hwnd = self.root.winfo_id()

            style = user32.GetWindowLongW(
                hwnd,
                GWL_EXSTYLE
            )

            style |= (
                WS_EX_NOACTIVATE |
                WS_EX_TOOLWINDOW
            )

            user32.SetWindowLongW(
                hwnd,
                GWL_EXSTYLE,
                style
            )

        except Exception as error:

            print(
                "Overlay configuration error:",
                error
            )

    # ========================================================
    # Position keyboard
    # ========================================================

    def position_keyboard(self):

        # Put keyboard near bottom-center
        # of the screen.

        x = (
            self.screen_width -
            self.keyboard_width
        ) // 2

        y = (
            self.screen_height -
            self.keyboard_height -
            55
        )

        self.root.geometry(
            f"{self.keyboard_width}x"
            f"{self.keyboard_height}+"
            f"{x}+{y}"
        )

    # ========================================================
    # Monitor Chrome
    # ========================================================

    def monitor_chrome(self):

        try:

            hwnd = get_foreground_window()

            title = get_window_title(
                hwnd
            )

            title_lower = (
                title.lower()
            )

            chrome_detected = (
                "chrome" in title_lower
            )

            new_tab = (
                chrome_detected
                and
                (
                    "new tab" in title_lower
                    or
                    title_lower.startswith(
                        "new tab"
                    )
                )
            )

            # ------------------------------------------------
            # New Chrome tab detected
            # ------------------------------------------------

            if new_tab:

                if not self.last_new_tab_state:

                    self.target_window = hwnd

                    self.position_keyboard()

                    self.show_keyboard()

                    print(
                        "WebEye: Chrome New Tab detected"
                    )

                self.last_new_tab_state = True

            else:

                self.last_new_tab_state = False

        except Exception as error:

            print(
                "Chrome detection error:",
                error
            )

        self.root.after(
            400,
            self.monitor_chrome
        )

    # ========================================================
    # Show keyboard
    # ========================================================

    def show_keyboard(self):

        if self.keyboard_visible:

            return

        self.keyboard_visible = True

        self.position_keyboard()

        self.root.deiconify()

        self.status_label.config(
            text="Ready for typing"
        )

        # Keep it above Chrome
        self.root.attributes(
            "-topmost",
            True
        )

    # ========================================================
    # Hide keyboard
    # ========================================================

    def hide_keyboard(self):

        self.keyboard_visible = False

        self.root.withdraw()

    # ========================================================
    # Create keyboard
    # ========================================================

    def create_keyboard(self):

        main = tk.Frame(
            self.root,
            bg="#15161c"
        )

        main.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=8
        )

        # ----------------------------------------------------
        # Header
        # ----------------------------------------------------

        header = tk.Frame(
            main,
            bg="#15161c"
        )

        header.pack(
            fill="x"
        )

        title = tk.Label(
            header,
            text="WebEye Virtual Keyboard",
            font=(
                "Arial",
                14,
                "bold"
            ),
            fg="white",
            bg="#15161c"
        )

        title.pack(
            side="left"
        )

        close_button = tk.Button(
            header,
            text="×",
            font=(
                "Arial",
                16,
                "bold"
            ),
            fg="white",
            bg="#dc2626",
            activebackground="#b91c1c",
            activeforeground="white",
            borderwidth=0,
            width=3,
            height=1,
            command=self.hide_keyboard
        )

        close_button.pack(
            side="right"
        )

        # ----------------------------------------------------
        # Status
        # ----------------------------------------------------

        self.status_label = tk.Label(
            main,
            text="Waiting for Chrome...",
            font=(
                "Arial",
                9
            ),
            fg="#b8b8b8",
            bg="#15161c"
        )

        self.status_label.pack(
            anchor="w",
            pady=(1, 5)
        )

        # ----------------------------------------------------
        # Display
        # ----------------------------------------------------

        self.display_var = tk.StringVar()

        self.display_var.set(
            "Ready"
        )

        display = tk.Entry(
            main,
            textvariable=self.display_var,
            font=(
                "Arial",
                14
            ),
            fg="white",
            bg="#272932",
            insertbackground="white",
            relief="flat"
        )

        display.pack(
            fill="x",
            ipady=6,
            pady=(0, 7)
        )

        display.bind(
            "<Key>",
            lambda event: "break"
        )

        # ----------------------------------------------------
        # Keyboard
        # ----------------------------------------------------

        keyboard_frame = tk.Frame(
            main,
            bg="#15161c"
        )

        keyboard_frame.pack(
            fill="both",
            expand=True
        )

        rows = [

            [
                "1", "2", "3", "4", "5",
                "6", "7", "8", "9", "0"
            ],

            [
                "Q", "W", "E", "R", "T",
                "Y", "U", "I", "O", "P"
            ],

            [
                "A", "S", "D", "F", "G",
                "H", "J", "K", "L"
            ],

            [
                "SHIFT",
                "Z", "X", "C", "V",
                "B", "N", "M",
                "BACKSPACE"
            ],

            [
                ".",
                ",",
                "@",
                "SPACE",
                "CLEAR",
                "ENTER"
            ]

        ]

        for row in rows:

            row_frame = tk.Frame(
                keyboard_frame,
                bg="#15161c"
            )

            row_frame.pack(
                fill="x",
                pady=2
            )

            for key in row:

                self.create_key(
                    row_frame,
                    key
                )

    # ========================================================
    # Create key
    # ========================================================

    def create_key(
        self,
        parent,
        key
    ):

        if key == "SPACE":

            width = 18

        elif key == "BACKSPACE":

            width = 12

        elif key == "SHIFT":

            width = 10

        elif key == "ENTER":

            width = 12

        elif key == "CLEAR":

            width = 10

        else:

            width = 6

        background = "#30313b"

        active_background = "#4b4d5a"

        if key == "ENTER":

            background = "#166534"

            active_background = "#15803d"

        elif key == "CLEAR":

            background = "#991b1b"

            active_background = "#b91c1c"

        elif key in (
            "SHIFT",
            "BACKSPACE"
        ):

            background = "#454752"

            active_background = "#5b5e6b"

        button = tk.Button(
            parent,
            text=key,
            font=(
                "Arial",
                11,
                "bold"
            ),
            fg="white",
            bg=background,
            activebackground=active_background,
            activeforeground="white",
            borderwidth=0,
            relief="flat",
            width=width,
            height=1,
            cursor="hand2",
            command=lambda k=key:
                self.key_pressed(k)
        )

        button.pack(
            side="left",
            expand=True,
            fill="x",
            padx=2
        )

        if key == "SHIFT":

            self.shift_button = button

    # ========================================================
    # Key pressed
    # ========================================================

    def key_pressed(
        self,
        key
    ):

        if key == "SHIFT":

            self.toggle_shift()

            return

        if key == "BACKSPACE":

            self.send_key(
                "backspace"
            )

            return

        if key == "SPACE":

            self.send_key(
                "space"
            )

            return

        if key == "CLEAR":

            self.clear_text()

            return

        if key == "ENTER":

            self.send_key(
                "enter"
            )

            self.root.after(
                250,
                self.hide_keyboard
            )

            return

        # ---------------------------------------------------
        # Character
        # ---------------------------------------------------

        character = key

        if self.shift_on:

            character = (
                character.upper()
            )

        else:

            character = (
                character.lower()
            )

        self.send_text(
            character
        )

        # ----------------------------------------------------
        # Auto-release shift
        # ----------------------------------------------------

        if self.shift_on:

            self.shift_on = False

            self.shift_button.config(
                bg="#454752"
            )

    # ========================================================
    # Activate Chrome
    # ========================================================

    def activate_target(self):

        if not self.target_window:

            return False

        try:

            activate_window(
                self.target_window
            )

            time.sleep(
                0.05
            )

            return True

        except Exception:

            return False

    # ========================================================
    # Send text
    # ========================================================

    def send_text(
        self,
        text
    ):

        if not self.activate_target():

            return

        try:

            pyautogui.write(
                text,
                interval=0.02
            )

            self.status_label.config(
                text=f"Typed: {text}"
            )

            current = (
                self.display_var.get()
            )

            if current in (
                "Ready",
                "Waiting for input..."
            ):

                current = ""

            self.display_var.set(
                current + text
            )

        except Exception as error:

            print(
                "Typing error:",
                error
            )

    # ========================================================
    # Send special key
    # ========================================================

    def send_key(
        self,
        key
    ):

        if not self.activate_target():

            return

        try:

            pyautogui.press(
                key
            )

            self.status_label.config(
                text=f"Pressed: {key}"
            )

            current = (
                self.display_var.get()
            )

            if key == "space":

                if current == "Ready":

                    current = ""

                self.display_var.set(
                    current + " "
                )

            elif key == "backspace":

                if current != "Ready":

                    self.display_var.set(
                        current[:-1]
                    )

        except Exception as error:

            print(
                "Key error:",
                error
            )

    # ========================================================
    # Clear
    # ========================================================

    def clear_text(self):

        if not self.activate_target():

            return

        try:

            pyautogui.hotkey(
                "ctrl",
                "a"
            )

            time.sleep(
                0.05
            )

            pyautogui.press(
                "backspace"
            )

            self.display_var.set(
                ""
            )

            self.status_label.config(
                text="Text cleared"
            )

        except Exception as error:

            print(
                "Clear error:",
                error
            )

    # ========================================================
    # Shift
    # ========================================================

    def toggle_shift(self):

        self.shift_on = (
            not self.shift_on
        )

        if self.shift_on:

            self.shift_button.config(
                bg="#2563eb"
            )

            self.status_label.config(
                text="SHIFT ON"
            )

        else:

            self.shift_button.config(
                bg="#454752"
            )

            self.status_label.config(
                text="SHIFT OFF"
            )

    # ========================================================
    # Run
    # ========================================================

    def run(self):

        self.hide_keyboard()

        print(
            "=========================================="
        )

        print(
            "WebEye Virtual Keyboard"
        )

        print(
            "=========================================="
        )

        print(
            "Waiting for Chrome New Tab..."
        )

        print(
            "=========================================="
        )

        self.root.mainloop()


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    keyboard = WebEyeVirtualKeyboard()

    keyboard.run()


