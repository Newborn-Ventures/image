from django.conf import settings
import Image as pil
from cStringIO import StringIO
import os
import sha

IMAGE_DEFAULT_FORMAT = getattr(settings, 'IMAGE_DEFAULT_FORMAT', 'JPEG')
IMAGE_DEFAULT_QUALITY = getattr(settings, 'IMAGE_DEFAULT_QUALITY', 85)


def image_create_token(parameters):
    return "image_token_%s" % sha.new(parameters).hexdigest()


def do_overlay(img, overlay_path, overlay_source=None, overlay_tint=None):
    if overlay_path is None:
        return img

    overlay_path = os.path.normpath(overlay_path)

    if overlay_source is 'media':
        overlay = pil.open(settings.MEDIA_ROOT + "/" + overlay_path)
    else:
        overlay = pil.open(settings.STATIC_ROOT + "/" + overlay_path)

    # We want the overlay to fit in the image
    iw, ih = img.size
    ow, oh = overlay.size
    overlay_ratio = float(ow) / float(oh)
    have_to_scale = False
    if ow > iw:
        ow = iw
        oh = int(float(iw) / overlay_ratio)
        have_to_scale = True
    if oh > ih:
        ow = int(float(ih) * overlay_ratio)
        oh = ih
        have_to_scale = True

    if have_to_scale:
        overlay = overlay.resize((ow, oh), pil.ANTIALIAS)
        ow, oh = overlay.size

    if overlay_tint:
        
        if overlay.mode != "RGBA":
            overlay = img.convert("RGBA")
        
        tint_color = (
            float(int("0x%s" % overlay_tint[0:2], 16)) / 255.0,
            float(int("0x%s" % overlay_tint[2:4], 16)) / 255.0,
            float(int("0x%s" % overlay_tint[4:6], 16)) / 255.0,
            float(int("0x%s" % overlay_tint[6:8], 16)) / 255.0,
        )
        try:
            intensity = float(int("0x%s" % overlay_tint[8:10], 16))
        except ValueError:
            intensity = 255.0
        
        img_data = overlay.getdata()
        new_data = []
        if intensity == 255.0:
            for data in img_data:
                data = (
                    int(float(data[0]) * tint_color[0]),
                    int(float(data[1]) * tint_color[1]),
                    int(float(data[2]) * tint_color[2]),
                    int(float(data[3]) * tint_color[3]),
                )
                new_data.append(data)
        else:
            intensity = intensity / 255.0
            intensity_inv = 1 - intensity
            tint_color = (
                tint_color[0] * intensity,
                tint_color[1] * intensity,
                tint_color[2] * intensity,
                tint_color[3] * intensity,
            )
            for data in img_data:
                data = (
                    int(float(data[0]) * intensity_inv + float(data[0]) * tint_color[0]),
                    int(float(data[1]) * intensity_inv + float(data[1]) * tint_color[1]),
                    int(float(data[2]) * intensity_inv + float(data[2]) * tint_color[2]),
                    int(float(data[3]) * intensity_inv + float(data[3]) * tint_color[3]),
                )
                new_data.append(data)
            
        overlay.putdata(tuple(new_data))

    img.paste(overlay, (int((iw - ow) / 2), int((ih - oh) / 2)), overlay)

    return img


def do_overlays(img, overlays, overlay_tints, overlay_sources):
    overlay_index = 0
    
    for overlay in overlays:
        
        try:
            overlay_tint = overlay_tints[overlay_index]
        except IndexError:
            overlay_tint = None
        
        if overlay_tint == "None":
            overlay_tint = None
            
        try:
            overlay_source = overlay_sources[overlay_index]
        except IndexError:
            overlay_source = 'static'
            
        do_overlay(img, overlay, overlay_source, overlay_tint)
        overlay_index += 1


def do_mask(img, maskPath):
    if maskPath is None:
        return img

    maskPath = os.path.normpath(maskPath)

    mask = pil.open(settings.STATIC_ROOT + "/" + maskPath).convert("RGBA")

    # We want the mask to have the same size than the image
    iw, ih = img.size
    mw, mh = mask.size
    if mw != iw or mh != ih:
        mask = mask.resize((iw, ih), pil.ANTIALIAS)

    r, g, b, a = mask.split()
    img.putalpha(a)


def do_fill(img, fill, width, height):
    if fill is None:
        return img

    overlay = img
    
    fill_color = (
        int("0x%s" % fill[0:2], 16),
        int("0x%s" % fill[2:4], 16),
        int("0x%s" % fill[4:6], 16),
        int("0x%s" % fill[6:8], 16),
    )
    img = pil.new("RGBA", (width,height), fill_color)

    iw, ih = img.size
    ow, oh = overlay.size

    img.paste(overlay, (int((iw - ow) / 2), int((ih - oh) / 2)), overlay)

    return img


def do_background(img, background):
    if background is None:
        return img

    overlay = img
    
    fill_color = (
        int("0x%s" % background[0:2], 16),
        int("0x%s" % background[2:4], 16),
        int("0x%s" % background[4:6], 16),
        int("0x%s" % background[6:8], 16),
    )
    img = pil.new("RGBA", overlay.size, fill_color)

    iw, ih = img.size
    ow, oh = overlay.size

    img.paste(overlay, (int((iw - ow) / 2), int((ih - oh) / 2)), overlay)

    return img




def scaleAndCrop(data, width, height, force=True, overlays=(), overlay_sources=(), overlay_tints=(), mask=None, center=".5,.5", format=IMAGE_DEFAULT_FORMAT, quality=IMAGE_DEFAULT_QUALITY, fill=None, background=None):
    """Rescale the given image, optionally cropping it to make sure the result image has the specified width and height."""

    max_width = width
    max_height = height

    input_file = StringIO(data)
    img = pil.open(input_file)
    if img.mode != "RGBA":
        img = img.convert("RGBA")

    if not force:
        img.thumbnail((max_width, max_height), pil.ANTIALIAS)
    else:
        src_width, src_height = img.size
        src_ratio = float(src_width) / float(src_height)
        dst_width, dst_height = max_width, max_height
        dst_ratio = float(dst_width) / float(dst_height)

        if dst_ratio < src_ratio:
            crop_height = src_height
            crop_width = crop_height * dst_ratio
            x_offset = float(src_width - crop_width) / 2
            y_offset = 0
        else:
            crop_width = src_width
            crop_height = crop_width / dst_ratio
            x_offset = 0
            y_offset = float(src_height - crop_height) / 2

        center_x, center_y = center.split(',')
        center_x = float(center_x)
        center_y = float(center_y)

        x_offset = min(
            max(0, center_x * src_width - crop_width / 2),
            src_width - crop_width
        )
        y_offset = min(
            max(0, center_y * src_height - crop_height / 2),
            src_height - crop_height
        )

        img = img.crop((int(x_offset), int(y_offset), int(x_offset) + int(crop_width), int(y_offset) + int(crop_height)))
        img = img.resize((int(dst_width), int(dst_height)), pil.ANTIALIAS)

    tmp = StringIO()
    img = do_fill(img, fill, width, height)
    img = do_background(img, background)
    do_mask(img, mask)
    do_overlays(img, overlays, overlay_tints, overlay_sources)
    
    img.save(tmp, format, quality=quality)
    tmp.seek(0)
    output_data = tmp.getvalue()
    input_file.close()
    tmp.close()

    return output_data


def scale(data, width, height, overlays=(), overlay_sources=(), overlay_tints=(), mask=None, format=IMAGE_DEFAULT_FORMAT, quality=IMAGE_DEFAULT_QUALITY, fill=None, background=None):
    """Rescale the given image, optionally cropping it to make sure the result image has the specified width and height."""

    max_width = width
    max_height = height

    input_file = StringIO(data)
    img = pil.open(input_file)

    if img.mode != "RGBA":
        img = img.convert("RGBA")

    src_width, src_height = img.size
    src_ratio = float(src_width) / float(src_height)
    dst_width = max_width
    dst_height = dst_width / src_ratio

    if dst_height > max_height:
        dst_height = max_height
        dst_width = dst_height * src_ratio

    img = img.resize((int(dst_width), int(dst_height)), pil.ANTIALIAS)

    tmp = StringIO()
    img = do_fill(img, fill, width, height)
    img = do_background(img, background)
    do_mask(img, mask)
    do_overlays(img, overlays, overlay_tints, overlay_sources)

    img.save(tmp, format, quality=quality)
    tmp.seek(0)
    output_data = tmp.getvalue()
    input_file.close()
    tmp.close()

    return output_data
