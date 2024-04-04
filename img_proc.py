""" image processing and visual analysis for Majsoul game screen"""
from enum import Enum, auto
from PIL import Image, ImageChops, ImageStat
import utils
from utils import RES_FOLDER
from browser import GameBrowser
from log_helper import LOGGER
def img_avg_diff(base_img:Image.Image, input_file:str, mask_img:Image.Image = None) -> float:
    """ Calculate the average difference between two images.
    given an optional mask file (black indicates ignored pixels).
    input image will be resized to mask size, or size of base_img if mask N/A
    Params:
        base_img (str): path to the base image.
        input_img (str): path to the image to compare to base
        mask_path (str): path to the mask image (optional), only white (value=0) area are compared.
    Return:
        float: average pixel difference (only unmasked area)
    """
    input_img = Image.open(input_file).convert('RGB')
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
    """ game UI templates"""
    main_menu = auto()
    

class GameVisual:
    """ image analysis for Majsoul game screen"""
    
    def __init__(self, browser:GameBrowser) -> None:
        self.browser = browser
        if not browser:
            raise ValueError("Browser is None")
        
        self.loc_dict = {}
        """ location dict {loc: (image, mask), ...}"""
        self.load_imgs()
        
    def load_imgs(self) -> None:
        """ load all images for analysis"""
        files = [
            (ImgTemp.main_menu, 'mainmenu.png', 'mainmenu_mask.png')
        ]
        for loc, img_file, mask_file in files:
            img_file = utils.sub_file(RES_FOLDER, img_file)
            mask_file = utils.sub_file(RES_FOLDER, mask_file)
            img_mainmenu = Image.open(img_file).convert('RGB')
            mask_mainmenu = Image.open(mask_file).convert('L')
            self.loc_dict[loc] = (img_mainmenu, mask_mainmenu)


    def comp_temp(self, tmp:ImgTemp, thres:float=30) -> tuple[bool, float]:
        """ compare current screen to template
        params:
            tmp (Location): template to compare to
            thres (float): threshold, lower than which is considered a match
        return:
            bool: True if the screen is loc
            float: average difference between current screen and loc template"""
        img_file = self.browser.screen_shot()
        if not img_file:
            return False, -1
        base_img, mask = self.loc_dict[tmp]
        try:
            diff = img_avg_diff(base_img, img_file, mask)
            return diff < thres, diff
        except Exception as e:
            LOGGER.error("Error in testing location: %s", e, exc_info=True)
            return False, -1



if __name__ == "__main__":
    pass
