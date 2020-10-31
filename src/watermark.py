from PIL import Image
import requests

def watermark_with_transparency(input_image_path,
                                output_image_path,
                                watermark_image_path,
                                position):
    response = requests.get(input_image_path, stream=True)
    response.raw.decode_content = True
    base_image = Image.open(response.raw)
    watermark = Image.open(watermark_image_path)
    width, height = base_image.size
    width2, height2 = watermark.size
    if (width/width2)*height2 < height:
        watermark = watermark.resize((width, int((width/width2)*height2)))
    else:
        watermark = watermark.resize((int((height/height2)*width2), height))
    transparent = Image.new('RGBA', (width, height), (0,0,0,0))
    transparent.paste(base_image, (0,0))
    if position == "1":
        width3, height3 = watermark.size
        watermark = watermark.resize((int(width3/2), int(height3/2)))
        transparent.paste(watermark, (0,0), mask=watermark)
    elif position == "2":
        transparent.paste(watermark, (int((width-width2)/2),int((height-height2)/2)), mask=watermark)
    transparent.save(output_image_path)
