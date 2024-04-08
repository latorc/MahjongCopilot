""" image processing and visual analysis for Majsoul game screen"""
from enum import Enum, auto
import io
from PIL import Image, ImageChops, ImageStat
import common.utils as utils
from common.utils import RES_FOLDER
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
    # input_img = Image.open(input_file).convert('RGB')
    # resize input to mask or base img
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
    

class GameVisual:
    """ image analysis for game screen"""
    
    def __init__(self, browser:GameBrowser) -> None:
        self.browser = browser
        if not browser:
            raise ValueError("Browser is None")
        
        self.temp_dict = {}
        """ image template dict {ImgTemp: (image_file, mask_file), ...}"""
        self._load_imgs()
        
    def _load_imgs(self) -> None:
        """ load all template images"""
        files = [
            (ImgTemp.MAIN_MENU, 'mainmenu.png', 'mainmenu_mask.png')
        ]
        for loc, img_file, mask_file in files:
            img_file = utils.sub_file(RES_FOLDER, img_file)
            mask_file = utils.sub_file(RES_FOLDER, mask_file)
            img_mainmenu = Image.open(img_file).convert('RGB')
            mask_mainmenu = Image.open(mask_file).convert('L')
            self.temp_dict[loc] = (img_mainmenu, mask_mainmenu)


    def comp_temp(self, tmp:ImgTemp, thres:float=30) -> tuple[bool, float]:
        """ compare current screen to template
        params:
            tmp (ImgTemp): template img to compare to
            thres (float): threshold, diff lower than which is considered a match
        return:
            bool: True if the current screen matches the template
            float: average difference between current screen and loc template"""
        img_bytes = self.browser.screen_shot()
        if img_bytes is None:
            return False, -1
        img_io = io.BytesIO(img_bytes)
        img_input = Image.open(img_io).convert('RGB')
        # if not img_file:
        #     return False, -1
        base_img, mask = self.temp_dict[tmp]
        try:
            diff = img_avg_diff(base_img, img_input, mask)
            return diff < thres, diff
        except Exception as e:
            LOGGER.error("Error in testing template %s: %s", tmp.name, e, exc_info=True)
            return False, -1