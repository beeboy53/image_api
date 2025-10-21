import os
import uuid
from io import BytesIO
from fastapi import FastAPI, File, UploadFile, Response, HTTPException, Form
from rembg import remove
from PIL import Image

app = FastAPI()

# ✅ Create folders
os.makedirs("uploads", exist_ok=True)
os.makedirs("outputs", exist_ok=True)


@app.get("/")
def read_root():
    return {"message": "AI Background Remover + Replacer API is running 🚀"}


@app.post("/remove-bg")
async def remove_bg(
    file: UploadFile = File(...),
    background_color: str = Form(None),  # optional (e.g. "#ffffff" or "red")
    bg_image: UploadFile = File(None)  # optional replacement image
):
    # ✅ Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid main image type!")

    contents = await file.read()
    input_filename = f"{uuid.uuid4()}.png"
    input_path = os.path.join("uploads", input_filename)
    with open(input_path, "wb") as f:
        f.write(contents)

    # ✅ Remove background
    output = remove(contents)

    # ✅ Convert to Pillow Image for further editing
    image_no_bg = Image.open(BytesIO(output)).convert("RGBA")

    # ✅ Replace background (color or image)
    if bg_image:
        # Replace with another image
        bg_contents = await bg_image.read()
        bg = Image.open(BytesIO(bg_contents)).convert("RGBA")
        bg = bg.resize(image_no_bg.size)
        final_image = Image.alpha_composite(bg, image_no_bg)

    elif background_color:
        # Replace with color
        bg = Image.new("RGBA", image_no_bg.size, background_color)
        final_image = Image.alpha_composite(bg, image_no_bg)

    else:
        # No replacement — just transparent
        final_image = image_no_bg

    # ✅ Save output
    output_filename = f"{uuid.uuid4()}_final.png"
    output_path = os.path.join("outputs", output_filename)
    final_image.save(output_path)

    # ✅ Return image
    img_bytes = BytesIO()
    final_image.save(img_bytes, format="PNG")
    img_bytes.seek(0)

    return Response(content=img_bytes.read(), media_type="image/png")
from PIL import Image, ImageOps

@app.post("/optimize")
async def optimize_image(
    file: UploadFile = File(...),
    width: int = Form(None),
    height: int = Form(None),
    quality: int = Form(85),  # 1–100 (default 85)
    output_format: str = Form("webp")  # png, jpeg, webp
):
    allowed_types = ["image/jpeg", "image/png", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid image type!")

    # Read uploaded image
    contents = await file.read()
    img = Image.open(BytesIO(contents))

    # Resize if requested
    if width or height:
        new_width = width or img.width
        new_height = height or img.height
        img = ImageOps.contain(img, (new_width, new_height))

    # Convert mode for saving (to support JPEG/WebP)
    if output_format.lower() in ["jpeg", "jpg"] and img.mode == "RGBA":
        img = img.convert("RGB")

    # Save compressed image to memory
    output_bytes = BytesIO()
    img.save(output_bytes, format=output_format.upper(), optimize=True, quality=quality)
    output_bytes.seek(0)

    return Response(content=output_bytes.read(), media_type=f"image/{output_format.lower()}")
@app.post("/crop")
async def crop_image(
    file: UploadFile = File(...),
    x: int = Form(None),
    y: int = Form(None),
    width: int = Form(None),
    height: int = Form(None),
    aspect_ratio: str = Form(None),  # e.g. "1:1", "16:9"
    output_format: str = Form("png")
):
    allowed_types = ["image/jpeg", "image/png", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid image type!")

    contents = await file.read()
    img = Image.open(BytesIO(contents))
    img_width, img_height = img.size

    # Handle cropping by coordinates
    if all(v is not None for v in [x, y, width, height]):
        box = (x, y, x + width, y + height)
        img = img.crop(box)

    # Handle cropping by aspect ratio
    elif aspect_ratio:
        try:
            w_ratio, h_ratio = map(int, aspect_ratio.split(":"))
            target_ratio = w_ratio / h_ratio
            current_ratio = img_width / img_height

            if current_ratio > target_ratio:
                # Image is wider than target ratio → crop sides
                new_width = int(target_ratio * img_height)
                left = (img_width - new_width) // 2
                right = left + new_width
                img = img.crop((left, 0, right, img_height))
            else:
                # Image is taller than target ratio → crop top/bottom
                new_height = int(img_width / target_ratio)
                top = (img_height - new_height) // 2
                bottom = top + new_height
                img = img.crop((0, top, img_width, bottom))
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid aspect ratio format. Use like '1:1' or '16:9'.")

    else:
        raise HTTPException(status_code=400, detail="Provide either coordinates or aspect_ratio.")

    # Save cropped image
    output_bytes = BytesIO()
    img.save(output_bytes, format=output_format.upper())
    output_bytes.seek(0)

    return Response(content=output_bytes.read(), media_type=f"image/{output_format.lower()}")
from PIL import ImageEnhance, ImageFilter

@app.post("/enhance")
async def enhance_image(
    file: UploadFile = File(...),
    brightness: float = Form(1.0),   # 1.0 = original
    contrast: float = Form(1.0),     # >1.0 = more contrast
    sharpness: float = Form(1.0),    # >1.0 = sharper
    blur: float = Form(0.0),         # >0.0 = apply blur
    grayscale: bool = Form(False),   # True = black & white
    output_format: str = Form("png")
):
    allowed_types = ["image/jpeg", "image/png", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid image type!")

    contents = await file.read()
    img = Image.open(BytesIO(contents)).convert("RGB")

    # Apply brightness
    enhancer = ImageEnhance.Brightness(img)
    img = enhancer.enhance(brightness)

    # Apply contrast
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(contrast)

    # Apply sharpness
    enhancer = ImageEnhance.Sharpness(img)
    img = enhancer.enhance(sharpness)

    # Apply blur
    if blur > 0:
        img = img.filter(ImageFilter.GaussianBlur(blur))

    # Apply grayscale
    if grayscale:
        img = img.convert("L")

    # Save enhanced image
    output_bytes = BytesIO()
    img.save(output_bytes, format=output_format.upper())
    output_bytes.seek(0)

    return Response(content=output_bytes.read(), media_type=f"image/{output_format.lower()}")
@app.post("/convert")
async def convert_image(
    file: UploadFile = File(...),
    target_format: str = Form("png")  # can be "jpg", "png", "webp"
):
    allowed_types = ["image/jpeg", "image/png", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid image type!")

    contents = await file.read()
    img = Image.open(BytesIO(contents))

    # Handle JPG format conversion properly
    if target_format.lower() == "jpg":
        target_format = "JPEG"

    # Save converted image to memory
    output_bytes = BytesIO()
    img.convert("RGB").save(output_bytes, format=target_format.upper())
    output_bytes.seek(0)

    return Response(
        content=output_bytes.read(),
        media_type=f"image/{target_format.lower()}"
    )
from PIL import ImageDraw, ImageFont

@app.post("/watermark")
async def add_watermark(
    file: UploadFile = File(...),
    watermark_text: str = Form("Futurist Digital"),  # default watermark
    position: str = Form("bottom-right"),  # top-left, top-right, center, etc.
    opacity: float = Form(0.3),  # transparency level
    font_size: int = Form(32),
    output_format: str = Form("png")
):
    allowed_types = ["image/jpeg", "image/png", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid image type!")

    contents = await file.read()
    base_image = Image.open(BytesIO(contents)).convert("RGBA")

    # Create transparent overlay
    txt_layer = Image.new("RGBA", base_image.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(txt_layer)

    # Load a font (fallback to default if not available)
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        font = ImageFont.load_default()

    # Measure text size correctly for Pillow ≥ 10
    bbox = draw.textbbox((0, 0), watermark_text, font=font)
    text_width, text_height = bbox[2] - bbox[0], bbox[3] - bbox[1]

    # Choose position
    positions = {
        "top-left": (10, 10),
        "top-right": (base_image.width - text_width - 10, 10),
        "center": ((base_image.width - text_width) // 2, (base_image.height - text_height) // 2),
        "bottom-left": (10, base_image.height - text_height - 10),
        "bottom-right": (base_image.width - text_width - 10, base_image.height - text_height - 10),
    }
    pos = positions.get(position, positions["bottom-right"])

    # Draw watermark text with transparency
    text_color = (255, 255, 255, int(255 * opacity))
    draw.text(pos, watermark_text, font=font, fill=text_color)

    # Merge watermark layer
    watermarked = Image.alpha_composite(base_image, txt_layer)

    # Save to memory
    output_bytes = BytesIO()
    watermarked.save(output_bytes, format=output_format.upper())
    output_bytes.seek(0)

    return Response(content=output_bytes.read(), media_type=f"image/{output_format.lower()}")
@app.post("/filter")
async def apply_filter(
    file: UploadFile = File(...),
    filter_type: str = Form("grayscale"),  # grayscale, sepia, blur, sharpen, invert
    intensity: float = Form(1.0)
):
    allowed_types = ["image/jpeg", "image/png", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid image type!")

    contents = await file.read()
    img = Image.open(BytesIO(contents)).convert("RGB")

    # Apply filter logic
    if filter_type == "grayscale":
        img = ImageOps.grayscale(img)

    elif filter_type == "sepia":
        sepia_img = ImageOps.colorize(ImageOps.grayscale(img), "#704214", "#C0A080")
        img = sepia_img

    elif filter_type == "blur":
        img = img.filter(ImageFilter.GaussianBlur(radius=intensity * 2))

    elif filter_type == "sharpen":
        img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))

    elif filter_type == "invert":
        img = ImageOps.invert(img)

    else:
        raise HTTPException(status_code=400, detail="Unsupported filter type")

    output_bytes = BytesIO()
    img.save(output_bytes, format="JPEG")
    output_bytes.seek(0)

    return Response(content=output_bytes.read(), media_type="image/jpeg")
@app.post("/rotate")
async def rotate_image(
    file: UploadFile = File(...),
    angle: float = Form(...),  # e.g. 90, 180, 270
    expand: bool = Form(True),  # expand canvas to fit rotated image
    output_format: str = Form("png")
):
    allowed_types = ["image/jpeg", "image/png", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid image type!")

    contents = await file.read()
    img = Image.open(BytesIO(contents))

    rotated = img.rotate(-angle, expand=expand)  # negative angle = clockwise rotation

    output_bytes = BytesIO()
    rotated.save(output_bytes, format=output_format.upper())
    output_bytes.seek(0)

    return Response(content=output_bytes.read(), media_type=f"image/{output_format.lower()}")
@app.post("/flip")
async def flip_image(
    file: UploadFile = File(...),
    direction: str = Form(...),  # "horizontal" or "vertical"
    output_format: str = Form("png")
):
    allowed_types = ["image/jpeg", "image/png", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid image type!")

    contents = await file.read()
    img = Image.open(BytesIO(contents))

    if direction.lower() == "horizontal":
        flipped = img.transpose(Image.FLIP_LEFT_RIGHT)
    elif direction.lower() == "vertical":
        flipped = img.transpose(Image.FLIP_TOP_BOTTOM)
    else:
        raise HTTPException(status_code=400, detail="Invalid direction! Use 'horizontal' or 'vertical'.")

    output_bytes = BytesIO()
    flipped.save(output_bytes, format=output_format.upper())
    output_bytes.seek(0)

    return Response(content=output_bytes.read(), media_type=f"image/{output_format.lower()}")
@app.post("/compress")
async def compress_image(
    file: UploadFile = File(...),
    quality: int = Form(80),  # Between 1–100 (lower = more compression)
    output_format: str = Form("jpeg")
):
    allowed_types = ["image/jpeg", "image/png", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid image type!")

    contents = await file.read()
    img = Image.open(BytesIO(contents))

    # Convert RGBA → RGB for JPEG/WebP
    if output_format.lower() in ["jpeg", "jpg", "webp"] and img.mode == "RGBA":
        img = img.convert("RGB")

    output_bytes = BytesIO()
    img.save(output_bytes, format=output_format.upper(), optimize=True, quality=quality)
    output_bytes.seek(0)

    return Response(content=output_bytes.read(), media_type=f"image/{output_format.lower()}")
import zipfile

@app.post("/bulk-compress")
async def bulk_compress(
    files: list[UploadFile] = File(...),
    quality: int = Form(80),
    output_format: str = Form("jpeg")
):
    allowed_types = ["image/jpeg", "image/png", "image/webp"]
    zip_buffer = BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file in files:
            if file.content_type not in allowed_types:
                continue  # skip invalid files

            contents = await file.read()
            img = Image.open(BytesIO(contents))

            if output_format.lower() in ["jpeg", "jpg", "webp"] and img.mode == "RGBA":
                img = img.convert("RGB")

            output_bytes = BytesIO()
            img.save(output_bytes, format=output_format.upper(), optimize=True, quality=quality)
            output_bytes.seek(0)

            # Save into ZIP
            filename = f"{os.path.splitext(file.filename)[0]}_compressed.{output_format.lower()}"
            zipf.writestr(filename, output_bytes.read())

    zip_buffer.seek(0)

    return Response(
        content=zip_buffer.read(),
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=compressed_images.zip"}
    )
@app.post("/resize-bulk")
async def resize_bulk(
    files: list[UploadFile] = File(...),
    width: int = Form(...),
    height: int = Form(...),
    keep_aspect: bool = Form(True),
    output_format: str = Form("jpeg")
):
    allowed_types = ["image/jpeg", "image/png", "image/webp"]
    zip_buffer = BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file in files:
            if file.content_type not in allowed_types:
                continue  # Skip invalid files

            contents = await file.read()
            img = Image.open(BytesIO(contents))

            # Calculate new dimensions (if keeping aspect ratio)
            if keep_aspect:
                img.thumbnail((width, height))
            else:
                img = img.resize((width, height))

            # Convert RGBA → RGB if needed
            if output_format.lower() in ["jpeg", "jpg", "webp"] and img.mode == "RGBA":
                img = img.convert("RGB")

            output_bytes = BytesIO()
            img.save(output_bytes, format=output_format.upper(), optimize=True)
            output_bytes.seek(0)

            filename = f"{os.path.splitext(file.filename)[0]}_{width}x{height}.{output_format.lower()}"
            zipf.writestr(filename, output_bytes.read())

    zip_buffer.seek(0)
    return Response(
        content=zip_buffer.read(),
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=resized_images.zip"}
    )
from PIL import ImageStat, ImageOps, ImageFilter, ImageEnhance, ExifTags
import numpy as np
import glob

@app.post("/add-logo")
async def add_logo(
    file: UploadFile = File(...),
    logo: UploadFile = File(...),
    position: str = Form("bottom-right"),  # top-left, top-right, bottom-left, bottom-right, center
    opacity: float = Form(0.5)
):
    """Overlay a logo or watermark image onto another image."""
    allowed_types = ["image/jpeg", "image/png", "image/webp"]
    if file.content_type not in allowed_types or logo.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid image type!")

    # Read images
    main_img = Image.open(BytesIO(await file.read())).convert("RGBA")
    logo_img = Image.open(BytesIO(await logo.read())).convert("RGBA")

    # Resize logo (15% of main image width)
    logo_w = int(main_img.width * 0.15)
    logo_img = logo_img.resize((logo_w, int(logo_img.height * logo_w / logo_img.width)))

    # Apply opacity
    if opacity < 1:
        alpha = logo_img.split()[3]
        alpha = alpha.point(lambda p: int(p * opacity))
        logo_img.putalpha(alpha)

    # Calculate position
    margin = 20
    positions = {
        "bottom-right": (main_img.width - logo_img.width - margin, main_img.height - logo_img.height - margin),
        "bottom-left": (margin, main_img.height - logo_img.height - margin),
        "top-left": (margin, margin),
        "top-right": (main_img.width - logo_img.width - margin, margin),
        "center": ((main_img.width - logo_img.width)//2, (main_img.height - logo_img.height)//2),
    }
    pos = positions.get(position, positions["bottom-right"])

    # Merge
    main_img.paste(logo_img, pos, logo_img)

    output_bytes = BytesIO()
    main_img.save(output_bytes, format="PNG")
    output_bytes.seek(0)
    return Response(content=output_bytes.read(), media_type="image/png")


@app.post("/filter-bulk")
async def filter_bulk(
    files: list[UploadFile] = File(...),
    filter_type: str = Form("BLUR")  # BLUR, SHARPEN, CONTOUR, EDGE_ENHANCE, SMOOTH
):
    """Apply the same filter to multiple images."""
    allowed = ["image/jpeg", "image/png", "image/webp"]
    filter_map = {
        "BLUR": ImageFilter.BLUR,
        "SHARPEN": ImageFilter.SHARPEN,
        "CONTOUR": ImageFilter.CONTOUR,
        "EDGE_ENHANCE": ImageFilter.EDGE_ENHANCE,
        "SMOOTH": ImageFilter.SMOOTH,
    }

    if filter_type not in filter_map:
        raise HTTPException(status_code=400, detail="Invalid filter type")

    results = []
    for f in files:
        if f.content_type not in allowed:
            continue
        img = Image.open(BytesIO(await f.read()))
        img = img.filter(filter_map[filter_type])
        output_bytes = BytesIO()
        img.save(output_bytes, format="PNG")
        output_bytes.seek(0)
        out_path = f"outputs/{uuid.uuid4()}_filtered.png"
        with open(out_path, "wb") as out_file:
            out_file.write(output_bytes.read())
        results.append(out_path)

    return {"filtered_images": results}


@app.post("/metadata")
async def get_metadata(file: UploadFile = File(...)):
    """Extract metadata and image details."""
    allowed = ["image/jpeg", "image/png", "image/webp"]
    if file.content_type not in allowed:
        raise HTTPException(status_code=400, detail="Invalid image type!")

    img = Image.open(BytesIO(await file.read()))
    metadata = {
        "format": img.format,
        "mode": img.mode,
        "size": img.size,
        "width": img.width,
        "height": img.height,
        "info": img.info
    }

    # Extract EXIF if available
    exif_data = {}
    try:
        exif = img._getexif()
        if exif:
            for tag, value in exif.items():
                decoded = ExifTags.TAGS.get(tag, tag)
                exif_data[decoded] = value
    except Exception:
        pass

    metadata["exif"] = exif_data
    return metadata


@app.post("/auto-adjust")
async def auto_adjust(
    file: UploadFile = File(...),
    enhance_color: bool = Form(True),
    enhance_contrast: bool = Form(True),
    enhance_brightness: bool = Form(True)
):
    """Auto adjust brightness, color, and contrast."""
    allowed = ["image/jpeg", "image/png", "image/webp"]
    if file.content_type not in allowed:
        raise HTTPException(status_code=400, detail="Invalid image type!")

    img = Image.open(BytesIO(await file.read())).convert("RGB")

    if enhance_color:
        img = ImageEnhance.Color(img).enhance(1.2)

    if enhance_contrast:
        img = ImageEnhance.Contrast(img).enhance(1.1)

    if enhance_brightness:
        img = ImageEnhance.Brightness(img).enhance(1.1)

    # Auto equalize for lighting correction
    img = ImageOps.autocontrast(img)

    output_bytes = BytesIO()
    img.save(output_bytes, format="PNG")
    output_bytes.seek(0)
    return Response(content=output_bytes.read(), media_type="image/png")
