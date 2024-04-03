from PIL import Image, ImageChops, ImageStat
import utils
from utils import TEMP_FOLDER

def img_avg_diff(base_img:str, image:str, mask_path:str = None):
    """ Calculate the average difference between two images. given an optional mask file (black indicates ignored pixels)."""
    img_base = Image.open(base_img).convert('RGB')
    img_input = Image.open(image).convert('RGB')
    if mask_path:
        mask = Image.open(mask_path).convert('L')  # Ensure mask is in grayscale
        img_size = mask.size
        img_base = img_base.resize(img_size, Image.Resampling.LANCZOS)
    else:
        img_size = img_base.size
    img_input = img_input.resize(img_size, Image.Resampling.LANCZOS)
    
    if mask_path:
        # Modify mask: Set all non-black pixels to white
        modified_mask = mask.point(lambda p: 255 if p != 0 else 0)
    
        # Apply the modified mask
        img_base.putalpha(modified_mask)
        img_input.putalpha(modified_mask)
        img_base = Image.composite(img_base, Image.new('RGB', img_base.size, 'white'), modified_mask)
        img_input = Image.composite(img_input, Image.new('RGB', img_input.size, 'white'), modified_mask)
    
    # Compare the images (after applying the mask)
    diff = ImageChops.difference(img_base, img_input)
    stat = ImageStat.Stat(diff, mask=modified_mask)  # Use modified mask to ignore black pixels
    
    # Calculate the average difference only for non-ignored pixels
    non_ignored_pixels = sum(modified_mask.point(lambda p: p > 0 and 255).convert("L").point(bool).getdata())
    # Correct calculation of average difference
    if non_ignored_pixels:
        avg_diff = sum(stat.mean) / len(stat.mean)
    else:
        avg_diff = 0
    
    return avg_diff, img_size


if __name__ == "__main__":
    imgs_to_compare = [
        "shot1.png",
        "shot2.png",
        "colored.png",
        "room.png",
        "akagi.png",
        "points.png",
        "results.png"
    ]
    base = utils.sub_file(TEMP_FOLDER, 'main_menu.png')
    mask = utils.sub_file(TEMP_FOLDER, 'mask.png')
    print("comparing images to base:")
    for i in imgs_to_compare:
        img = utils.sub_file(TEMP_FOLDER, i)
        diff, img_size = img_avg_diff(base, img, mask)
        print(f"{i} diff={diff:.1f} (size={img_size})")
