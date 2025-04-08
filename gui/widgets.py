# -*- coding: utf-8 -*-
"""Custom widgets for GUI (CustomTkinter Version) using CTkImage"""
from pathlib import Path
from typing import (
    Callable,
    Dict,
    Tuple,
    Union,
    Optional,
)  # Added Optional, Dict, Tuple, Union
import tkinter as tk
import customtkinter as ctk
from customtkinter import CTkImage  # Import CTkImage
from PIL import Image  # Keep PIL.Image for opening files
import time

# import os # os was imported but not used directly

from common.log_helper import LOGGER

# Ensure Folder and sub_file are defined/imported if used elsewhere
from common.utils import (
    sub_file,
    Folder,
)  # Removed unused sub_file unless needed elsewhere

# ==========================================
# Refactored Widgets with CTkImage
# ==========================================


class ToggleSwitch(ctk.CTkFrame):
    """
    Toggle button widget (CustomTkinter Version) using CTkImage.
    NOTE: customtkinter provides ctk.CTkSwitch, which is generally preferred.
    """

    def __init__(
        self,
        master,
        text: str,
        height: int,
        font_size: int = 12,
        command: Callable = None,
    ):
        super().__init__(
            master, height=height, width=height * 2, fg_color="transparent"
        )
        self._command = command
        self._is_on = False
        # Cache now stores CTkImage objects
        self._image_cache: Dict[str, Optional[CTkImage]] = {"on": None, "off": None}
        img_ht = int(height * 0.6)
        icon_size = (img_ht, img_ht)

        res_path = Path(Folder.RES) if hasattr(Folder, "RES") and Folder.RES else None
        if res_path:
            self._load_image(res_path / "switch_on.png", "on", icon_size)
            self._load_image(res_path / "switch_off.png", "off", icon_size)
        else:
            LOGGER.error("Folder.RES not defined for ToggleSwitch.")

        self.img_label = ctk.CTkLabel(self, text="", image=self._image_cache.get("off"))
        self.img_label.pack(side="top", pady=(0, 5))
        font = ctk.CTkFont(size=font_size)
        self.text_label = ctk.CTkLabel(self, text=text, font=font)
        self.text_label.pack(side="top")
        self.img_label.bind("<Button-1>", self._on_click)
        self.img_label.bind(
            "<Enter>", lambda e: self.img_label.configure(cursor="hand2")
        )
        self.img_label.bind("<Leave>", lambda e: self.img_label.configure(cursor=""))

    def _load_image(
        self, image_path: Union[Path, str], key: str, size: Tuple[int, int]
    ):
        """Loads an image from a given Path or string path into a CTkImage."""
        try:
            img_p = Path(image_path) if isinstance(image_path, str) else image_path

            if not img_p.is_file():
                LOGGER.warning(f"ToggleSwitch image not found: {img_p}")
                self._image_cache[key] = None  # Ensure cache reflects missing image
                return

            # Open with PIL
            img = Image.open(img_p)
            # Create CTkImage (handles resizing internally)
            # Use the same image for light and dark mode for consistency with original code
            ctk_img = CTkImage(light_image=img, dark_image=img, size=size)
            self._image_cache[key] = ctk_img

        except Exception as e:
            LOGGER.error(
                f"Failed to load ToggleSwitch image '{image_path}' as CTkImage: {e}"
            )
            self._image_cache[key] = None  # Ensure cache reflects error

    def switch_on(self):
        if not self._is_on:
            self._is_on = True
            on_img = self._image_cache.get("on")
            if on_img and self.img_label.winfo_exists():
                self.img_label.configure(image=on_img)

    def switch_off(self):
        if self._is_on:
            self._is_on = False
            off_img = self._image_cache.get("off")
            if off_img and self.img_label.winfo_exists():
                self.img_label.configure(image=off_img)

    def set_state(self, is_on: bool):
        (self.switch_on() if is_on else self.switch_off())

    def _on_click(self, _event=None):
        # Toggle the state visually first
        self.set_state(not self._is_on)
        # Then call the command if it exists
        if self._command:
            try:
                self._command()  # Command should ideally query the *new* state if needed
            except Exception as e:
                LOGGER.error(
                    f"Error executing ToggleSwitch command: {e}", exc_info=True
                )


# ==========================================


class Timer(ctk.CTkFrame):
    """A timer widget (CustomTkinter Version) with improved input validation"""

    START = "⏱️"  # Start symbol
    STOP = "⏹️"  # Stop symbol

    def __init__(
        self,
        master: ctk.CTkFrame,
        label_text: str,
        height: int = 40,
        default_font_size: int = 12,
    ):
        super().__init__(master, height=height, fg_color="transparent")
        # Store label_text if needed, otherwise remove if unused
        # self.label_text = label_text
        self.font_size = default_font_size
        self.entry_font = ctk.CTkFont(size=self.font_size)
        self.button_font = ctk.CTkFont(family="Segoe UI Emoji", size=self.font_size + 2)
        self._callback: Optional[Callable] = None
        self._timer_running: bool = False
        self._timer_id: Optional[str] = None  # Tkinter after IDs are strings
        self._stop_time: Optional[float] = None
        self._validating = False  # Flag to prevent trace/validation recursion

        # StringVars initialized empty for placeholder text
        self.hour_var = tk.StringVar(value="")
        self.minute_var = tk.StringVar(value="")
        self.second_var = tk.StringVar(value="")

        # Layout configuration
        self.grid_columnconfigure(0, weight=1)  # Entries frame expands
        self.grid_columnconfigure(1, weight=0)  # Button fixed size
        self.grid_rowconfigure(0, weight=1)

        # Frame for entries and separators
        self.frame_entries = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_entries.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        self.pack_args = {
            "side": tk.LEFT,
            "padx": (1, 1),
            "pady": (1, 1),
        }  # Common packing args

        self.entries: list[ctk.CTkEntry] = []  # To hold entry widgets

        # Setup hour, minute, second entries
        self._setup_entry(self.frame_entries, self.hour_var, 23)  # Max hours = 23
        ctk.CTkLabel(self.frame_entries, text=":", font=self.entry_font, width=5).pack(
            **self.pack_args
        )
        self._setup_entry(self.frame_entries, self.minute_var, 59)  # Max minutes = 59
        ctk.CTkLabel(self.frame_entries, text=":", font=self.entry_font, width=5).pack(
            **self.pack_args
        )
        self._setup_entry(self.frame_entries, self.second_var, 59)  # Max seconds = 59

        # Start/Stop button
        self.the_btn = ctk.CTkButton(
            self,
            text=Timer.START,
            font=self.button_font,
            command=self._toggle_timer,
            width=40,
        )
        self.the_btn.grid(row=0, column=1, sticky="nsew", padx=(5, 0))

    def set_callback(self, callback: Callable):
        """Sets the function to call when the timer finishes."""
        self._callback = callback

    def _setup_entry(self, parent, var: tk.StringVar, max_val: int):
        """Creates and configures an entry widget with validation."""
        entry = ctk.CTkEntry(
            parent,
            textvariable=var,
            font=self.entry_font,
            width=30,
            justify=tk.CENTER,
            placeholder_text="00",  # Display '00' when empty
        )
        # --- Input Validation Strategy ---
        # Use lambda with default argument capture for sv
        var.trace_add("write", lambda name, index, mode, sv=var: self._filter_input(sv))
        # Use lambda with default argument capture for sv and mv
        entry.bind(
            "<FocusOut>",
            lambda event, sv=var, mv=max_val: self._validate_and_format_final(sv, mv),
            add="+",
        )
        entry.bind(
            "<Return>",
            lambda event, sv=var, mv=max_val: self._validate_and_format_final(sv, mv),
            add="+",
        )

        entry.pack(**self.pack_args)
        self.entries.append(entry)

    def _filter_input(self, var: tk.StringVar):
        """Trace callback: Filters input during typing (allows only digits, max 2 chars)."""
        if self._validating:
            return
        self._validating = True
        try:
            current_value = var.get()
            # Keep only digits, limit to 2 characters
            new_value = "".join(filter(str.isdigit, current_value))[:2]
            if new_value != current_value:
                var.set(new_value)
        finally:
            # Ensure validation flag is reset even if error occurs (though unlikely here)
            self._validating = False

    def _validate_and_format_final(self, var: tk.StringVar, max_val: int):
        """Event callback (<FocusOut>, <Return>): Validates range, formats with leading zero."""
        if self._validating:
            return
        self._validating = True
        try:
            current_value = var.get()
            final_value = ""  # Default to empty if invalid or cleared
            if current_value.isdigit():  # Process only if it contains digits
                val = int(current_value)
                clamped_val = min(
                    max(0, val), max_val
                )  # Clamp value between 0 and max_val
                final_value = f"{clamped_val:02}"  # Format with leading zero
            elif current_value:  # Log if non-empty and non-digit
                LOGGER.debug(
                    f"Invalid non-digit value '{current_value}' during final validation. Clearing."
                )
            # else: it's already empty, do nothing

            # Only set if the value needs changing (prevents potential trace loops)
            if var.get() != final_value:
                var.set(final_value)
        except ValueError:
            # This case should be less frequent due to isdigit() check, but handle just in case
            LOGGER.warning(
                f"Invalid non-integer value '{current_value}' during final validation. Clearing."
            )
            if var.get() != "":
                var.set("")
        except Exception as e:
            LOGGER.error(
                f"Unexpected error during final validation for '{current_value}': {e}"
            )
            if var.get() != "":
                var.set("")  # Attempt to clear on unexpected errors
        finally:
            self._validating = False

    def _toggle_timer(self):
        """Starts or stops the timer based on its current state."""
        if self._timer_running:
            self._stop_timer()
        else:
            # Explicitly validate all fields before starting
            self._validate_and_format_final(self.hour_var, 23)
            self._validate_and_format_final(self.minute_var, 59)
            self._validate_and_format_final(self.second_var, 59)
            # Now start the timer
            self._start_timer()

    def _start_timer(self):
        """Starts the countdown after validation."""
        # Validation now happens in _toggle_timer before this is called
        try:
            # Use '0' if the field is empty after validation
            hours_str = self.hour_var.get() or "0"
            minutes_str = self.minute_var.get() or "0"
            seconds_str = self.second_var.get() or "0"

            hours = int(hours_str)
            minutes = int(minutes_str)
            seconds = int(seconds_str)

            total_seconds = hours * 3600 + minutes * 60 + seconds
            if total_seconds <= 0:
                LOGGER.info("Timer duration is zero or negative. Not starting.")
                # Optional: Clear fields if duration is zero?
                # self._clear_time()
                return

            self._timer_running = True
            if self.the_btn.winfo_exists():
                self.the_btn.configure(text=Timer.STOP)
            LOGGER.info(f"Timer started for {hours:02d}:{minutes:02d}:{seconds:02d}")
            self._stop_time = time.time() + total_seconds
            for e in self.entries:
                if e.winfo_exists():
                    e.configure(state="disabled")
            self._run_timer()  # Start the timer loop

        except ValueError:
            # This should ideally not happen if validation worked, but log just in case
            LOGGER.error(
                "Invalid time input format encountered when starting timer (should have been caught by validation)."
            )
        except Exception as e:
            LOGGER.error(f"Unexpected error starting timer: {e}", exc_info=True)

    def _run_timer(self):
        """Internal method called periodically to update the timer display."""
        if not self._timer_running or self._stop_time is None:
            return

        try:
            # Calculate remaining time, ensure it's not negative for display
            remaining_time_float = self._stop_time - time.time()
            remaining_time_int = max(0, int(round(remaining_time_float)))

            if remaining_time_int > 0:
                hours = remaining_time_int // 3600
                minutes = (remaining_time_int % 3600) // 60
                seconds = remaining_time_int % 60

                # Update StringVars only if the value has changed
                if (
                    not self._validating
                ):  # Check validation flag to prevent interference
                    if self.hour_var.get() != f"{hours:02}":
                        self.hour_var.set(f"{hours:02}")
                    if self.minute_var.get() != f"{minutes:02}":
                        self.minute_var.set(f"{minutes:02}")
                    if self.second_var.get() != f"{seconds:02}":
                        self.second_var.set(f"{seconds:02}")

                # Schedule the next update
                # Use a slightly shorter delay to account for processing time, aiming for ~5 updates/sec
                self._timer_id = self.after(200, self._run_timer)
            else:
                # Timer finished
                LOGGER.info("Timer finished.")
                # Ensure display shows 00:00:00 before stopping
                if not self._validating:
                    if self.hour_var.get() != "00":
                        self.hour_var.set("00")
                    if self.minute_var.get() != "00":
                        self.minute_var.set("00")
                    if self.second_var.get() != "00":
                        self.second_var.set("00")

                # Stop the timer mechanism and reset state
                self._stop_timer(finished=True)

                # Execute callback *after* stopping and resetting state
                if self._callback:
                    try:
                        self._callback()
                    except Exception as e:
                        LOGGER.error(
                            f"Error executing timer callback: {e}", exc_info=True
                        )

        except Exception as e:
            LOGGER.error(f"Error during timer run loop: {e}", exc_info=True)
            # Attempt to stop cleanly even if an error occurred
            self._stop_timer(finished=False)  # Indicate it didn't finish normally

    def _clear_time(self):
        """Clears entry fields to empty strings, allowing placeholders to show."""
        if self._validating:
            return
        self._validating = True
        try:
            # Setting to empty string allows placeholder text to appear
            if self.hour_var.get() != "":
                self.hour_var.set("")
            if self.minute_var.get() != "":
                self.minute_var.set("")
            if self.second_var.get() != "":
                self.second_var.set("")
        finally:
            self._validating = False

    def _stop_timer(self, finished=False):
        """Stops the timer, cancels pending updates, and resets state."""
        # Cancel any pending 'after' calls
        if self._timer_id is not None:
            self.after_cancel(self._timer_id)
            self._timer_id = None

        self._timer_running = False
        self._stop_time = None

        # Update button text
        if self.the_btn.winfo_exists():
            self.the_btn.configure(text=Timer.START)

        # Re-enable entry fields
        for e in self.entries:
            if e.winfo_exists():
                e.configure(state="normal")

        # Log if stopped manually and clear fields
        if not finished:
            LOGGER.info("Timer stopped.")
            # Clear the time only if stopped manually or due to error
            self._clear_time()
        # If finished=True, the fields should already show 00:00:00 or be cleared by run_timer


# ==========================================


class ToolBar(ctk.CTkFrame):
    """Tool bar for buttons (CustomTkinter Version) using CTkImage"""

    def __init__(self, master, height: int = 40, **kwargs):
        super().__init__(master, height=height, fg_color="transparent", **kwargs)
        self.height = height
        # Cache format: { (filename_or_path, size_tuple): CTkImage }
        self._image_cache: Dict[Tuple[str, Tuple[int, int]], Optional[CTkImage]] = {}
        self._button_refs: Dict[str, ctk.CTkButton] = {}  # Store references if needed

    def _calculate_icon_size(self) -> Tuple[int, int]:
        """Calculates the desired icon size based on toolbar height."""
        scale_factor = 0.8  # Adjusted slightly, can be tuned
        icon_dimension = max(1, int(self.height * scale_factor))
        return (icon_dimension, icon_dimension)

    def _load_image(
        self, img_file_or_path: Optional[str], size: Tuple[int, int]
    ) -> Optional[CTkImage]:
        """Loads, caches, and returns a CTkImage from a filename or full path."""
        if not img_file_or_path:
            return None

        cache_key = (img_file_or_path, size)
        if cache_key in self._image_cache:
            # Return cached CTkImage object (could be None if loading failed previously)
            return self._image_cache[cache_key]

        try:
            # --- Determine the final path to load ---
            file_path_to_load: Optional[Path] = None
            potential_path = Path(img_file_or_path)

            if potential_path.is_file():
                file_path_to_load = potential_path
            else:
                if hasattr(Folder, "RES") and Folder.RES:
                    base_path = Path(Folder.RES)
                    # Check relative to RES root
                    path_in_res = base_path / potential_path
                    if path_in_res.is_file():
                        file_path_to_load = path_in_res
                    else:
                        # Fallback: Check relative to RES/images
                        path_in_images = base_path / "images" / potential_path
                        if path_in_images.is_file():
                            file_path_to_load = path_in_images
                # If still not found and RES wasn't defined or didn't contain the file
                if file_path_to_load is None:
                    LOGGER.error(
                        f"Folder.RES not defined or image '{img_file_or_path}' not found relative to it."
                    )
                    self._image_cache[cache_key] = None  # Cache the failure
                    return None

            # If no valid path was found after all checks
            if file_path_to_load is None:
                LOGGER.warning(
                    f"Toolbar image not found: '{img_file_or_path}' (checked as-is and relative to RES/images if applicable)"
                )
                self._image_cache[cache_key] = None  # Cache the failure
                return None
            # --- End path determination ---

            # Load using PIL
            pil_image = Image.open(file_path_to_load)

            # Create CTkImage - use same image for light/dark
            ctk_image = CTkImage(light_image=pil_image, dark_image=pil_image, size=size)

            # Store in cache before returning
            self._image_cache[cache_key] = ctk_image
            return ctk_image

        except Exception as e:
            LOGGER.error(
                f"Failed to load or process toolbar image '{img_file_or_path}' as CTkImage: {e}",
                exc_info=True,
            )
            self._image_cache[cache_key] = None  # Cache the failure
            return None

    def add_button(
        self, text: str, img_file_or_path: Optional[str], command: Callable
    ) -> ctk.CTkButton:
        """Adds a button with an optional icon (as CTkImage) to the toolbar."""
        icon_size = self._calculate_icon_size()
        # Call the modified _load_image which returns CTkImage or None
        ctk_image = self._load_image(img_file_or_path, icon_size)

        # Determine button dimensions (square for icons)
        button_width = self.height
        button_height = self.height
        # Display button text only if there's no icon loaded successfully
        display_text = "" if ctk_image else text

        btn = ctk.CTkButton(
            self,
            image=ctk_image,  # Pass the CTkImage object (or None)
            text=display_text,
            width=button_width,
            height=button_height,
            command=command,
            fg_color="transparent",
            hover_color=("gray75", "gray25"),  # Standard CTk hover colors
            # Compound doesn't make sense if text is empty when image exists
            # Let CTk handle default placement based on image/text presence
            # compound="left" if ctk_image and display_text else "center",
            corner_radius=4,
        )
        # Store original path/filename and size for potential updates
        # These attributes help in reloading/updating later if needed
        setattr(btn, "_image_identifier", img_file_or_path)
        setattr(btn, "_image_size", icon_size)  # Store the target size

        self._button_refs[text] = (
            btn  # Use text as key (ensure uniqueness or use a different key)
        )
        btn.pack(side=tk.LEFT, padx=1, pady=2)
        return btn

    def set_img(self, btn: ctk.CTkButton, img_file_or_path: Optional[str]):
        """Updates the image (CTkImage) on an existing button."""
        if not isinstance(btn, ctk.CTkButton):
            LOGGER.error("set_img called with non-CTkButton widget")
            return
        if not btn.winfo_exists():
            LOGGER.warning("set_img called on destroyed button")
            return

        # Retrieve stored info
        current_identifier = getattr(btn, "_image_identifier", None)
        icon_size = getattr(
            btn, "_image_size", self._calculate_icon_size()
        )  # Fallback size

        # Avoid reloading if the identifier (path/filename) hasn't changed
        if current_identifier == img_file_or_path:
            # LOGGER.debug(f"set_img: Identifier '{img_file_or_path}' hasn't changed. Skipping reload.")
            return

        # Call the modified _load_image to get the new CTkImage
        new_ctk_image = self._load_image(img_file_or_path, icon_size)

        try:
            # Update the button's image
            btn.configure(image=new_ctk_image)
            # Update the stored identifier
            setattr(btn, "_image_identifier", img_file_or_path)

            # Optional: Adjust text based on whether an image was successfully loaded
            # Retrieve the original text if possible (this might require storing it differently)
            # For now, we assume the button's text should be empty if an image is present
            original_text = btn.cget(
                "text"
            )  # Might be empty if image was previously set
            display_text = (
                "" if new_ctk_image else original_text
            )  # Or fetch original intended text
            if btn.cget("text") != display_text:
                btn.configure(text=display_text)

        except tk.TclError as e:
            # This can happen if the widget is destroyed between check and configure
            LOGGER.warning(
                f"TclError configuring button image in set_img (widget might be destroyed): {e}"
            )
        except Exception as e:
            LOGGER.error(
                f"Unexpected error configuring button image in set_img: {e}",
                exc_info=True,
            )

    def add_sep(self):
        """Adds a vertical separator line to the toolbar."""
        sep_height = max(
            10, self.height - 8
        )  # Make separator slightly shorter than toolbar
        # Calculate vertical padding to center the separator
        pady_sep = (self.height - sep_height) // 2
        sep = ctk.CTkFrame(
            self, width=2, height=sep_height, fg_color="gray50", corner_radius=1
        )
        # Use fill='y' but also explicit pady for centering
        sep.pack(side=tk.LEFT, padx=5, pady=pady_sep, fill="y")


# ==========================================


class StatusBar(ctk.CTkFrame):
    """Status bar with multiple configurable columns (CustomTkinter Version) using CTkImage"""

    def __init__(self, master, num_columns: int, height: int = 24):
        super().__init__(
            master, fg_color=("gray85", "gray18"), height=height, corner_radius=0
        )
        if num_columns <= 0:
            raise ValueError("StatusBar requires at least one column")
        self.num_columns = num_columns
        self._labels: list[ctk.CTkLabel] = []
        # Cache now stores: (CTkImage | None, icon_path_or_name | None)
        self._icons: list[Tuple[Optional[CTkImage], Optional[str]]] = [
            (None, None)
        ] * num_columns
        self._font = ctk.CTkFont(size=11)

        # Configure grid columns
        for i in range(num_columns):
            # Last column gets weight 1 to expand, others get 0
            weight = 1 if i == num_columns - 1 else 0
            # 'uniform' makes columns share space based on weight if multiple have weight > 0
            # Here, it ensures non-expanding columns have a consistent minimum size.
            self.grid_columnconfigure(i, weight=weight, uniform="sb_cols")
        self.grid_rowconfigure(0, weight=1)  # Row expands vertically

        # Create label widgets for each column
        for i in range(num_columns):
            self._create_column(i)

    def _create_column(self, index: int):
        """Creates a label widget for a specific column index."""
        label = ctk.CTkLabel(
            self, text="", font=self._font, compound="left", anchor="w", padx=5
        )
        # Padding between columns, slightly less for the last one on the right
        padx_right = (
            2 if index < self.num_columns - 1 else 5
        )  # More padding at the very end
        label.grid(row=0, column=index, sticky="nsew", padx=(5, padx_right), pady=1)
        self._labels.append(label)

    def _load_status_icon(self, icon_file_or_path: Optional[str]) -> Optional[CTkImage]:
        """Loads, resizes, and returns an icon as CTkImage suitable for the status bar."""
        if not icon_file_or_path:
            return None

        # Determine icon size based on font height for status bar consistency
        # Add a small buffer (e.g., +2 pixels)
        icon_height = self._font.cget("size") + 2
        icon_size = (icon_height, icon_height)

        # Status bar icons might change frequently; caching might be less critical
        # than for toolbar icons, but we can still use a simple approach.
        # Let's rely on the main self._icons cache in update_column for now.

        try:
            # --- Determine the final path to load (Similar logic to ToolBar) ---
            file_path_to_load: Optional[Path] = None
            potential_path = Path(icon_file_or_path)

            if potential_path.is_file():
                file_path_to_load = potential_path
            else:
                if hasattr(Folder, "RES") and Folder.RES:
                    base_path = Path(Folder.RES)
                    path_in_res = base_path / potential_path
                    if path_in_res.is_file():
                        file_path_to_load = path_in_res
                    else:
                        path_in_images = base_path / "images" / potential_path
                        if path_in_images.is_file():
                            file_path_to_load = path_in_images
                if file_path_to_load is None:
                    LOGGER.error(
                        f"Folder.RES not defined or status icon '{icon_file_or_path}' not found relative to it."
                    )
                    return None  # Cannot proceed

            if file_path_to_load is None:
                LOGGER.warning(f"StatusBar icon not found: '{icon_file_or_path}'")
                return None
            # --- End path determination ---

            # Load with PIL
            img = Image.open(file_path_to_load)
            # Create CTkImage
            ctk_image = CTkImage(light_image=img, dark_image=img, size=icon_size)
            return ctk_image

        except Exception as e:
            LOGGER.error(
                f"Failed to load status bar icon '{icon_file_or_path}' as CTkImage: {e}",
                exc_info=True,
            )
            return None

    def update_column(
        self, index: int, text: str, icon_file_or_path: Optional[str] = None
    ):
        """Updates a specific column's text and icon (using CTkImage)."""
        if not 0 <= index < len(self._labels):
            LOGGER.error(f"StatusBar update_column: Invalid index {index}")
            return
        label = self._labels[index]
        if not label.winfo_exists():
            # LOGGER.debug(f"StatusBar update_column: Label {index} destroyed.")
            return  # Don't try to update a destroyed widget

        # Get current state from the label and our cache
        current_text = label.cget("text")
        current_icon_tuple = self._icons[index]  # (CTkImage | None, path | None)
        current_icon_object = current_icon_tuple[0]
        current_icon_identifier = current_icon_tuple[1]

        # Determine if updates are needed
        text_changed = current_text != text
        # Compare the *identifier* (path/filename) provided now vs the one cached
        icon_identifier_changed = icon_file_or_path != current_icon_identifier

        new_icon_image: Optional[CTkImage] = (
            current_icon_object  # Assume no change initially
        )

        # If the identifier changed, we need to load the new icon
        if icon_identifier_changed:
            # Use the loading function which returns CTkImage or None
            new_icon_image = (
                self._load_status_icon(icon_file_or_path) if icon_file_or_path else None
            )
            # Update our internal cache with the new image object and its identifier
            self._icons[index] = (new_icon_image, icon_file_or_path)
            # LOGGER.debug(f"StatusBar col {index}: Icon changed to '{icon_file_or_path}', loaded: {new_icon_image is not None}")

        # Configure the label only if text or the actual image object has changed
        # (Checking new_icon_image != current_icon_object handles cases where loading fails/succeeds)
        if text_changed or (new_icon_image is not current_icon_object):
            try:
                # Pass the potentially new CTkImage object (or None)
                label.configure(text=text, image=new_icon_image)
                # LOGGER.debug(f"StatusBar col {index}: Configured text='{text}', image={new_icon_image is not None}")
            except tk.TclError as e:
                # Catch errors if the widget is destroyed between winfo_exists and configure
                LOGGER.warning(
                    f"TclError configuring status bar label {index} (widget might be destroyed): {e}"
                )
            except Exception as e:
                LOGGER.error(
                    f"Unexpected error configuring status bar label {index}: {e}",
                    exc_info=True,
                )


# Example Usage (if you want to run this file directly for testing)
if __name__ == "__main__":
    # Assume Folder.RES is set correctly relative to this script for testing
    # You might need to create dummy 'res/images' folders and placeholder images
    # (e.g., switch_on.png, switch_off.png, some_icon.png)
    try:
        # Create a dummy Folder class for testing if common.utils isn't fully set up
        class DummyFolder:
            # Point RES to a directory relative to this script
            # Create this directory and put dummy images inside
            RES = Path(__file__).parent / "test_res"

        Folder = DummyFolder  # Override imported Folder for testing
        # Ensure the test_res directory exists
        Folder.RES.mkdir(exist_ok=True)
        (Folder.RES / "images").mkdir(exist_ok=True)
        # Create dummy image files if they don't exist (simple 1x1 pixel images)
        dummy_files = [
            "switch_on.png",
            "switch_off.png",
            "images/icon1.png",
            "images/icon2.png",
            "images/accept.png",
        ]
        for fname in dummy_files:
            fpath = Folder.RES / fname
            if not fpath.exists():
                try:
                    print(f"Creating dummy image: {fpath}")
                    Image.new("RGB", (10, 10), color="red").save(fpath)
                except Exception as e:
                    print(f"Error creating dummy image {fpath}: {e}")

    except NameError:
        print(
            "Skipping dummy Folder creation - assuming common.utils.Folder is available."
        )
        # Make sure Folder.RES points to a valid path with necessary images externally

    app = ctk.CTk()
    app.title("CTkImage Widget Test")
    app.geometry("600x400")

    main_frame = ctk.CTkFrame(app)
    main_frame.pack(pady=20, padx=20, fill="both", expand=True)

    # --- ToggleSwitch Test ---
    def toggle_action():
        state = (
            "ON" if toggle.is_on() else "OFF"
        )  # Assuming ToggleSwitch gets an is_on() method or use internal state
        print(f"Toggle Switch state: {state}")
        # Update status bar based on toggle
        status.update_column(
            0,
            f"Toggle: {state}",
            "images/icon1.png" if toggle._is_on else "images/icon2.png",
        )

    # Add is_on() method to ToggleSwitch for external query if needed:
    def is_on(self):
        return self._is_on

    ToggleSwitch.is_on = is_on  # Monkey-patch for the example

    toggle_frame = ctk.CTkFrame(main_frame)
    toggle_frame.pack(pady=10)
    ctk.CTkLabel(toggle_frame, text="Test Toggle:").pack(side="left", padx=5)
    toggle = ToggleSwitch(toggle_frame, text="Enable", height=30, command=toggle_action)
    toggle.pack(side="left")

    # --- Timer Test ---
    def timer_finished():
        print("Timer Finished!")
        status.update_column(1, "Timer Done!", "images/accept.png")

    timer_frame = ctk.CTkFrame(main_frame)
    timer_frame.pack(pady=10)
    ctk.CTkLabel(timer_frame, text="Test Timer:").pack(side="left", padx=5)
    timer = Timer(
        timer_frame, label_text="Countdown", height=35
    )  # label_text is currently unused internally
    timer.set_callback(timer_finished)
    timer.pack(side="left")

    # --- ToolBar Test ---
    toolbar = ToolBar(main_frame, height=35)
    toolbar.pack(pady=10, fill="x")

    def tb_action1():
        print("Toolbar Button 1 Clicked")
        status.update_column(2, "Action 1", "images/icon1.png")
        # Example: Change button 2's icon
        if hasattr(app, "btn2"):  # Check if btn2 exists
            toolbar.set_img(app.btn2, "images/icon1.png")

    def tb_action2():
        print("Toolbar Button 2 Clicked")
        status.update_column(2, "Action 2", "images/icon2.png")
        # Example: Change button 2's icon back
        if hasattr(app, "btn2"):
            toolbar.set_img(app.btn2, "images/accept.png")  # Change to a third icon

    toolbar.add_button("Action 1", "images/icon1.png", tb_action1)
    app.btn2 = toolbar.add_button(
        "Action 2", "images/icon2.png", tb_action2
    )  # Store ref
    toolbar.add_sep()
    toolbar.add_button("No Icon", None, lambda: print("Text Button Clicked"))

    # --- StatusBar Test ---
    status = StatusBar(app, num_columns=3, height=26)  # Status bar at bottom
    status.pack(side="bottom", fill="x")

    status.update_column(0, "Ready", None)
    status.update_column(1, "Timer Idle", "images/icon2.png")
    status.update_column(2, "No Action", None)

    app.mainloop()
