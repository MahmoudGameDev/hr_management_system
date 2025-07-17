# c:\Users\mahmo\OneDrive\Documents\GitHub\hr_management_system\utils\image_utils.py
import os
from PIL import Image, ImageTk, ImageDraw, UnidentifiedImageError
import qrcode
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

ICON_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "icons")

def resize_image(image: Image.Image, max_width: int, max_height: int) -> Image.Image:
    """
    Resizes an image to fit within max_width and max_height, maintaining aspect ratio.
    """
    original_width, original_height = image.size
    ratio = min(max_width / original_width, max_height / original_height)
    new_width = int(original_width * ratio)
    new_height = int(original_height * ratio)
    return image.resize((new_width, new_height), Image.Resampling.LANCZOS)

def load_and_resize_photo(image_path: str, max_width: int, max_height: int) -> Optional[ImageTk.PhotoImage]:
    """
    Loads an image from a file path, resizes it, and returns an ImageTk.PhotoImage.
    Returns None if the image cannot be loaded or processed.
    """
    if not image_path or not os.path.exists(image_path):
        return None
    try:
        img = Image.open(image_path)
        img = resize_image(img, max_width, max_height)
        return ImageTk.PhotoImage(img)
    except UnidentifiedImageError:
        logger.warning(f"Cannot identify image file: {image_path}")
        return None
    except Exception as e:
        logger.error(f"Error loading or resizing photo {image_path}: {e}")
        return None

def get_icon_path(icon_name: str) -> str:
    """
    Returns the full path to an icon file.
    Assumes icons are in assets/icons directory relative to the project root.
    """
    return os.path.join(ICON_DIR, icon_name)

def get_icon(icon_name: str, size: Optional[Tuple[int, int]] = None) -> Optional[ImageTk.PhotoImage]:
    """
    Loads an icon, optionally resizes it, and returns an ImageTk.PhotoImage.
    """
    icon_filepath = get_icon_path(icon_name)
    if not os.path.exists(icon_filepath):
        logger.warning(f"Icon not found: {icon_filepath}")
        return None
    try:
        img = Image.open(icon_filepath)
        if size:
            img = img.resize(size, Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(img)
    except Exception as e:
        logger.error(f"Error loading icon {icon_name}: {e}")
        return None

def create_qr_code_image(data: str, box_size: int = 10, border: int = 4) -> Optional[Image.Image]:
    """
    Generates a QR code image from the given data.
    Returns a PIL Image object.
    """
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=box_size,
            border=border,
        )
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        return img
    except Exception as e:
        logger.error(f"Error generating QR code for data '{data}': {e}")
        return None

def capture_signature_from_canvas(canvas_widget) -> Optional[bytes]:
    """
    Captures the content of a Tkinter Canvas as PNG image data (bytes).
    This is a simplified version and might need adjustments based on your Tkinter setup.
    Requires Pillow's ImageGrab.
    """
    try:
        # Ensure the window is updated before grabbing
        canvas_widget.update_idletasks()
        x = canvas_widget.winfo_rootx()
        y = canvas_widget.winfo_rooty()
        x1 = x + canvas_widget.winfo_width()
        y1 = y + canvas_widget.winfo_height()
        
        from PIL import ImageGrab # Local import to avoid error if Pillow not fully installed
        img = ImageGrab.grab(bbox=(x, y, x1, y1))
        
        from io import BytesIO
        byte_arr = BytesIO()
        img.save(byte_arr, format='PNG')
        return byte_arr.getvalue()
    except Exception as e:
        logger.error(f"Error capturing signature from canvas: {e}")
        return None