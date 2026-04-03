"""
Alert and notification dialogs for fnwispr
Handles user-facing error messages and confirmations
Falls back to logging when Tcl/Tk is unavailable
"""

import sys
import logging

logger = logging.getLogger(__name__)


class AlertManager:
    """Manages user-facing alerts and notifications"""

    # Try to import Tkinter, but don't fail if unavailable
    _has_tkinter = False
    try:
        import tkinter as tk
        from tkinter import messagebox
        _has_tkinter = True
    except Exception:
        pass

    @staticmethod
    def _print_to_console(title: str, message: str):
        """Print alert to stderr for when Tkinter is unavailable"""
        print(f"\n{'='*60}", file=sys.stderr)
        print(f"[{title}]", file=sys.stderr)
        print(f"{'='*60}", file=sys.stderr)
        print(message, file=sys.stderr)
        print(f"{'='*60}\n", file=sys.stderr)

    @staticmethod
    def show_mic_error(device_name: str, error_details: str, is_startup: bool = False):
        """
        Show microphone initialization error alert

        Args:
            device_name: Name of the microphone device
            error_details: Technical error message
            is_startup: Whether this is a startup error (vs config change)
        """
        if is_startup:
            # On startup, just log — don't block with a popup.
            # The tray tooltip shows the error state and the user can fix via tray menu.
            logger.warning(
                f"Cannot initialize microphone '{device_name}': {error_details}. "
                f"Select a different device from the tray menu or Settings."
            )
            return

        title = "Microphone Configuration Error"
        message = (
            f"Cannot initialize microphone '{device_name}'.\n\n"
            f"Reverting to previous device.\n"
            f"Please check your audio settings.\n\n"
            f"Technical details: {error_details}"
        )

        try:
            if AlertManager._has_tkinter:
                root = AlertManager.tk.Tk()
                root.withdraw()  # Hide the root window
                AlertManager.messagebox.showerror(title, message)
                root.destroy()
            else:
                AlertManager._print_to_console(title, message)
            logger.error(f"Microphone error: {device_name} - {error_details}")
        except Exception as e:
            logger.error(f"Failed to show microphone error alert: {e}")
            # Fallback to stderr
            AlertManager._print_to_console(title, message)

    @staticmethod
    def show_warning(title: str, message: str):
        """
        Show generic warning dialog

        Args:
            title: Dialog title
            message: Warning message
        """
        try:
            if AlertManager._has_tkinter:
                root = AlertManager.tk.Tk()
                root.withdraw()
                AlertManager.messagebox.showwarning(title, message)
                root.destroy()
            else:
                AlertManager._print_to_console(title, message)
            logger.warning(f"Warning: {title}")
        except Exception as e:
            logger.error(f"Failed to show warning alert: {e}")
            # Fallback to stderr
            AlertManager._print_to_console(title, message)

    @staticmethod
    def show_info(title: str, message: str):
        """
        Show generic info dialog

        Args:
            title: Dialog title
            message: Info message
        """
        try:
            if AlertManager._has_tkinter:
                root = AlertManager.tk.Tk()
                root.withdraw()
                AlertManager.messagebox.showinfo(title, message)
                root.destroy()
            else:
                AlertManager._print_to_console(title, message)
            logger.info(f"Info: {title}")
        except Exception as e:
            logger.error(f"Failed to show info alert: {e}")
            # Fallback to stderr
            AlertManager._print_to_console(title, message)

    @staticmethod
    def ask_quit_or_minimize(remember_callback=None):
        """
        Ask user whether to quit or minimize to tray

        Args:
            remember_callback: Callback function(choice) if user checks "Remember my choice"

        Returns:
            "quit" or "minimize"
        """
        try:
            if AlertManager._has_tkinter:
                root = AlertManager.tk.Tk()
                root.withdraw()

                result = AlertManager.messagebox.askyesnocancel(
                    "Close fnwispr",
                    "Do you want to quit fnwispr or minimize to system tray?\n\n"
                    "Yes = Quit\n"
                    "No = Minimize to tray",
                )

                root.destroy()

                if result is True:
                    return "quit"
                elif result is False:
                    return "minimize"
                else:
                    return None
            else:
                # No Tkinter available - default to minimize
                logger.info("No Tkinter available for quit/minimize dialog, defaulting to minimize")
                return "minimize"

        except Exception as e:
            logger.error(f"Failed to show quit/minimize dialog: {e}")
            return "minimize"
