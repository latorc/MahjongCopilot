""" image processing and visual analysis for Majsoul game screen"""
from enum import Enum, auto
import io
from typing import Iterable
from PIL import Image, ImageChops, ImageStat, ImageDraw
import common.utils as utils
from common.utils import Folder
from common.log_helper import LOGGER
from .browser import GameBrowser


def img_avg_diff(base_img:Image.Image, input_img:Image.Image, mask_img:Image.Image = None) -> float:
    """ Calculate the average difference between two images.
    given an optional mask file (black indicates ignored pixels).
    input image will be resized to mask size, or size of base_img if mask N/A
    Params:
        base_img (Image): base image PIL format .
        input_img (Image): image to compare to base, PIL format 
        mask_img (Image): mask image (optional), only non-black area are compared.
    Return:
        float: average pixel difference (only unmasked area)
    """
    # operate on copies because masking mutates alpha
    base_img = base_img.copy()
    input_img = input_img.copy()

    # resize input to mask or base img
    modified_mask = None
    if mask_img:
        img_size = mask_img.size
        base_img = base_img.resize(img_size, Image.Resampling.LANCZOS)
    else:
        img_size = base_img.size
    input_img = input_img.resize(img_size, Image.Resampling.LANCZOS)
    
    if mask_img:    # apply mask if there is
        # Set all non-black pixels to white
        modified_mask = mask_img.point(lambda p: 255 if p != 0 else 0)
    
        # Apply the modified mask
        base_img.putalpha(modified_mask)
        input_img.putalpha(modified_mask)
        base_img = Image.composite(base_img, Image.new('RGB', base_img.size, 'white'), modified_mask)
        input_img = Image.composite(input_img, Image.new('RGB', input_img.size, 'white'), modified_mask)
    
    # Compare the images (after applying the mask)
    diff = ImageChops.difference(base_img, input_img)
    stat = ImageStat.Stat(diff, mask=modified_mask)  # Use modified mask to ignore black pixels
    
    # Calculate the average difference only for non-ignored pixels
    non_ignored_pixels = sum(modified_mask.point(lambda p: p > 0 and 255).convert("L").point(bool).getdata())
    # Correct calculation of average difference
    if non_ignored_pixels:
        avg_diff = sum(stat.mean) / len(stat.mean)
    else:
        avg_diff = 0    
    return avg_diff


class ImgTemp(Enum):
    """ game image templates"""
    MAIN_MENU = auto()
    DISCONNECT_RETRYING = auto()
    DISCONNECT_TIMEOUT = auto()
    DISCONNECT_MAIN = auto()
    

class GameVisual:
    """ image analysis for game screen"""
    NORMALIZED_TEMPLATE_SIZE = (1280, 720)
    
    def __init__(self, browser:GameBrowser) -> None:
        self.browser = browser
        if not browser:
            raise ValueError("Browser is None")
        
        self.temp_dict = {}
        """ image template dict {ImgTemp: [(image_file, mask_file, threshold), ...], ...}"""
        self._load_imgs()

    @staticmethod
    def _scale_box(box:tuple[int, int, int, int], size:tuple[int, int]) -> tuple[int, int, int, int]:
        """Scale a 1280x720 reference box to the current template size."""
        width, height = size
        sx = width / 1280
        sy = height / 720
        x1, y1, x2, y2 = box
        return (
            int(round(x1 * sx)),
            int(round(y1 * sy)),
            int(round(x2 * sx)),
            int(round(y2 * sy)),
        )

    def _draw_rect(self, draw:ImageDraw.ImageDraw, size:tuple[int, int], box:tuple[int, int, int, int]) -> None:
        draw.rectangle(self._scale_box(box, size), fill=255)

    def _draw_border(
        self,
        draw:ImageDraw.ImageDraw,
        size:tuple[int, int],
        box:tuple[int, int, int, int],
        border_px:int,
    ) -> None:
        x1, y1, x2, y2 = self._scale_box(box, size)
        scale = min(size[0] / 1280, size[1] / 720)
        border = max(1, int(round(border_px * scale)))
        draw.rectangle((x1, y1, x2, min(y2, y1 + border)), fill=255)
        draw.rectangle((x1, max(y1, y2 - border), x2, y2), fill=255)
        draw.rectangle((x1, y1, min(x2, x1 + border), y2), fill=255)
        draw.rectangle((max(x1, x2 - border), y1, x2, y2), fill=255)

    def _draw_ring(
        self,
        draw:ImageDraw.ImageDraw,
        size:tuple[int, int],
        box:tuple[int, int, int, int],
        width_px:int,
    ) -> None:
        scaled_box = self._scale_box(box, size)
        scale = min(size[0] / 1280, size[1] / 720)
        width = max(1, int(round(width_px * scale)))
        draw.ellipse(scaled_box, outline=255, width=width)

    def _normalize_template(self, img:Image.Image) -> Image.Image:
        """Crop slight aspect-ratio drift and resize a screenshot template to 1280x720."""
        src_w, src_h = img.size
        target_w, target_h = self.NORMALIZED_TEMPLATE_SIZE
        target_ratio = target_w / target_h
        src_ratio = src_w / src_h

        if abs(src_ratio - target_ratio) > 1e-4:
            if src_ratio > target_ratio:
                new_w = int(round(src_h * target_ratio))
                left = max(0, (src_w - new_w) // 2)
                img = img.crop((left, 0, left + new_w, src_h))
            else:
                new_h = int(round(src_w / target_ratio))
                top = max(0, (src_h - new_h) // 2)
                img = img.crop((0, top, src_w, top + new_h))

        return img.resize(self.NORMALIZED_TEMPLATE_SIZE, Image.Resampling.LANCZOS)

    def _load_rgb_template(self, img_file:str, normalize:bool=False) -> Image.Image:
        """Load a template image from resources."""
        img_path = utils.sub_file(Folder.RES, img_file)
        img = Image.open(img_path).convert('RGB')
        if normalize:
            img = self._normalize_template(img)
        return img

    def _build_generic_main_menu_mask(self, size:tuple[int, int]) -> Image.Image:
        """Build a language-agnostic main menu mask using only shared UI chrome.

        The CN and JP lobbies differ mainly in text/avatar art. Their outer menu boards,
        top currency ornaments and right-side circular buttons share the same layout.
        """
        mask = Image.new('L', size, 0)
        draw = ImageDraw.Draw(mask)

        # Three large lobby boards: compare only their borders, not the localized text.
        board_boxes = [
            (725, 166, 1178, 303),
            (756, 320, 1188, 469),
            (780, 479, 1193, 631),
        ]
        for box in board_boxes:
            self._draw_border(draw, size, box, 16)

        # Top resource ornaments.
        for box in [
            (560, 43, 619, 103),
            (771, 43, 830, 103),
        ]:
            self._draw_ring(draw, size, box, 8)

        for box in [
            (684, 31, 745, 107),
            (896, 31, 957, 107),
        ]:
            self._draw_border(draw, size, box, 8)

        # Top-right gear and vertical tool buttons: compare only the circular frames.
        for box in [
            (1216, 8, 1276, 68),
            (1217, 132, 1274, 189),
            (1217, 225, 1274, 282),
            (1217, 317, 1274, 374),
            (1217, 409, 1274, 466),
            (1217, 501, 1274, 558),
        ]:
            self._draw_ring(draw, size, box, 8)

        # Small board ornaments around the main menu columns.
        for box in [
            (716, 155, 760, 207),
            (1138, 142, 1187, 191),
            (759, 314, 798, 357),
            (1144, 305, 1189, 351),
            (781, 477, 821, 522),
            (1148, 470, 1195, 517),
        ]:
            self._draw_rect(draw, size, box)

        return mask

    def _build_disconnect_mask(self, size:tuple[int, int]) -> Image.Image:
        """Compare only the central disconnect modal and restart button."""
        mask = Image.new('L', size, 0)
        draw = ImageDraw.Draw(mask)
        self._draw_rect(draw, size, (278, 195, 913, 541))
        return mask
        
    def _load_imgs(self) -> None:
        """ load all template images"""
        img_mainmenu = self._load_rgb_template('mainmenu.png')
        mask_mainmenu = Image.open(utils.sub_file(Folder.RES, 'mainmenu_mask.png')).convert('L')
        generic_mask = self._build_generic_main_menu_mask(img_mainmenu.size)
        self.temp_dict[ImgTemp.MAIN_MENU] = [
            (img_mainmenu, mask_mainmenu, 30.0),
            (img_mainmenu, generic_mask, 28.0),
        ]

        disconnect_mask = self._build_disconnect_mask(self.NORMALIZED_TEMPLATE_SIZE)
        for tmp, img_file in [
            (ImgTemp.DISCONNECT_RETRYING, 'disconnect1.png'),
            (ImgTemp.DISCONNECT_TIMEOUT, 'disconnect2.png'),
            (ImgTemp.DISCONNECT_MAIN, 'disconnect3.png'),
        ]:
            img_disconnect = self._load_rgb_template(img_file, normalize=True)
            self.temp_dict[tmp] = [
                (img_disconnect, disconnect_mask, 12.0),
            ]

    def _comp_temp_on_img(
        self,
        img_input:Image.Image,
        tmp:ImgTemp,
        thres:float|None=None,
    ) -> tuple[bool, float]:
        """Compare a prepared screenshot against one template entry."""
        template_variants:list[tuple[Image.Image, Image.Image, float]] = self.temp_dict[tmp]
        best_diff = None
        for base_img, mask, variant_thres in template_variants:
            diff = img_avg_diff(base_img, img_input, mask)
            if best_diff is None or diff < best_diff:
                best_diff = diff
            threshold = thres if thres is not None else variant_thres
            if diff < threshold:
                return True, diff
        return False, best_diff if best_diff is not None else -1

    def _capture_screen_img(self) -> Image.Image | None:
        """Capture the current browser viewport as a PIL image."""
        img_bytes = self.browser.screen_shot()
        if img_bytes is None:
            return None
        img_io = io.BytesIO(img_bytes)
        return Image.open(img_io).convert('RGB')

    def comp_temp(self, tmp:ImgTemp, thres:float|None=None) -> tuple[bool, float]:
        """ compare current screen to template
        params:
            tmp (ImgTemp): template img to compare to
            thres (float): threshold, diff lower than which is considered a match.
                If None, use the threshold defined by the template variant.
        return:
            bool: True if the current screen matches the template
            float: average difference between current screen and loc template"""
        img_input = self._capture_screen_img()
        if img_input is None:
            return False, -1
        try:
            return self._comp_temp_on_img(img_input, tmp, thres)
        except Exception as e:
            LOGGER.error("Error in testing template %s: %s", tmp.name, e, exc_info=True)
            return False, -1

    def comp_temps(self, tmps:Iterable[ImgTemp], thres:float|None=None) -> tuple[ImgTemp | None, float]:
        """Compare the current screen against multiple templates using a single screenshot."""
        img_input = self._capture_screen_img()
        if img_input is None:
            return None, -1
        best_diff = None
        best_match = None
        best_match_diff = None
        try:
            for tmp in tmps:
                matched, diff = self._comp_temp_on_img(img_input, tmp, thres)
                if best_diff is None or (diff >= 0 and diff < best_diff):
                    best_diff = diff
                if matched and (best_match_diff is None or diff < best_match_diff):
                    best_match = tmp
                    best_match_diff = diff
            if best_match is not None:
                return best_match, best_match_diff
            return None, best_diff if best_diff is not None else -1
        except Exception as e:
            LOGGER.error("Error in testing template group: %s", e, exc_info=True)
            return None, -1
