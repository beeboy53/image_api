ADMIN_SECRET = "admin_92hfjW5sP@2025"
import os
import uuid
import json
from io import BytesIO
from datetime import date, datetime, timedelta
from fastapi import FastAPI, File, UploadFile, Response, HTTPException, Form, Header, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from rembg import remove
from PIL import Image, ImageOps, ImageEnhance, ImageFilter, ImageDraw, ImageFont, ExifTags
import zipfile
from fastapi import Form, Header

# auth_utils is expected to exist alongside this file (users.json management)
# If you haven't created it yet, use the earlier provided auth_utils.py implementation.
from auth_utils import load_users, save_users, validate_key, increment_usage, register_key, get_usage_info

app = FastAPI(title="Image Processing API (Full) - with Auth & Usage")

# Ensure directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(OUTPUTS_DIR, exist_ok=True)

# Serve outputs as static files so URLs can be returned
app.mount("/outputs", StaticFiles(directory=OUTPUTS_DIR), name="outputs")

ALLOWED_TYPES = ["image/jpeg", "image/png", "image/webp"]

def save_image_bytes_and_get_url(img_bytes: bytes, request: Request, prefix: str = "processed", ext: str = "png"):
    fname = f"{prefix}_{uuid.uuid4().hex}.{ext}"
    out_path = os.path.join(OUTPUTS_DIR, fname)
    with open(out_path, "wb") as f:
        f.write(img_bytes)
    # Build absolute URL using the incoming request base URL (auto-detect)
    base = str(request.base_url).rstrip("/")
    url = f"{base}/outputs/{fname}"
    return out_path, url

def make_success(message: str, image_url: str = None, user=None):
    usage = None
    if user:
        usage = {
            "plan": user.get("plan"),
            "used": user.get("usage", 0),
            "limit": user.get("limit", 0),
            "remaining": max(0, user.get("limit", 0) - user.get("usage", 0))
        }
    return {"status": "success", "message": message, "image_url": image_url, "usage": usage}

def ensure_allowed(file: UploadFile):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Invalid image type! Allowed: jpeg, png, webp")

# -------------------- Admin: Register Key --------------------


@app.post("/register-key")
def register_new_key(
    email: str = Form(...),
    plan: str = Form("free"),
    x_admin_key: str = Header(None)
):
    """
    Secure admin endpoint — registers a new API key.
    Requires header: x-admin-key
    Example curl:
    curl -X POST http://127.0.0.1:8000/register-key \
      -H "x-admin-key: YOUR_ADMIN_SECRET_KEY" \
      -F "email=awwalmalik4@gmail.com" \
      -F "plan=free"
    """
    if x_admin_key != ADMIN_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized — Invalid admin key")

    try:
        api_key = register_key(plan)
        return {
            "status": "success",
            "email": email,
            "plan": plan,
            "api_key": api_key
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error registering key: {str(e)}")

# -------------------- Usage info --------------------
@app.get("/usage")
def usage_info(request: Request, x_api_key: str = Header(None)):
    """
    Get usage and plan details for the current API key.
    Example return:
    {
        "plan": "free",
        "limit": 10,
        "usage": 3,
        "remaining": 7,
        "expiry": "2025-11-21T12:00:00",
        "server": "http://127.0.0.1:8000"
    }
    """
    user = validate_key(x_api_key)
    usage = get_usage_info(x_api_key)

    server_url = str(request.base_url).rstrip("/")
    return {
        "plan": usage["plan"],
        "limit": usage["limit"],
        "usage": usage["usage"],
        "remaining": usage["remaining"],
        "expiry": usage["expiry"],
        "server": server_url
    }
 
# -------------------- Remove BG --------------------
@app.post("/remove-bg")
async def remove_bg(request: Request,
                    api_key: str = Header(..., alias="x-api-key"),
                    file: UploadFile = File(...),
                    background_color: str = Form(None),
                    bg_image: UploadFile = File(None)):
    user = validate_key(api_key)
    ensure_allowed(file)
    contents = await file.read()

    # Save original
    in_path = os.path.join(UPLOADS_DIR, f"{uuid.uuid4().hex}_{file.filename}")
    with open(in_path, "wb") as f:
        f.write(contents)

    # Remove background (rembg returns PNG bytes)
    try:
        output = remove(contents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Background removal error: {e}")

    image_no_bg = Image.open(BytesIO(output)).convert("RGBA")

    # Replace background if requested
    if bg_image:
        bg_contents = await bg_image.read()
        bg = Image.open(BytesIO(bg_contents)).convert("RGBA")
        bg = bg.resize(image_no_bg.size)
        final = Image.alpha_composite(bg, image_no_bg)
    elif background_color:
        bg = Image.new("RGBA", image_no_bg.size, background_color)
        final = Image.alpha_composite(bg, image_no_bg)
    else:
        final = image_no_bg

    out_buf = BytesIO()
    final.save(out_buf, format="PNG")
    out_buf.seek(0)
    out_bytes = out_buf.read()

    out_path, url = save_image_bytes_and_get_url(out_bytes, request, prefix="no_bg", ext="png")
    increment_usage(api_key)
    return JSONResponse(content=make_success("Background removed", url, user))

# -------------------- Optimize --------------------
@app.post("/optimize")
async def optimize_image(request: Request,
                         api_key: str = Header(..., alias="x-api-key"),
                         file: UploadFile = File(...),
                         width: int = Form(None),
                         height: int = Form(None),
                         quality: int = Form(85),
                         output_format: str = Form("webp")):
    user = validate_key(api_key)
    ensure_allowed(file)
    contents = await file.read()
    img = Image.open(BytesIO(contents))

    if width or height:
        new_width = width or img.width
        new_height = height or img.height
        img = ImageOps.contain(img, (new_width, new_height))

    if output_format.lower() in ["jpeg", "jpg"] and img.mode == "RGBA":
        img = img.convert("RGB")

    out_buf = BytesIO()
    img.save(out_buf, format=output_format.upper(), optimize=True, quality=quality)
    out_buf.seek(0)
    out_bytes = out_buf.read()

    out_path, url = save_image_bytes_and_get_url(out_bytes, request, prefix="opt", ext=output_format.lower())
    increment_usage(api_key)
    return JSONResponse(content=make_success("Image optimized", url, user))

# -------------------- Crop --------------------
@app.post("/crop")
async def crop_image(request: Request,
                     api_key: str = Header(..., alias="x-api-key"),
                     file: UploadFile = File(...),
                     x: int = Form(None),
                     y: int = Form(None),
                     width: int = Form(None),
                     height: int = Form(None),
                     aspect_ratio: str = Form(None),
                     output_format: str = Form("png")):
    user = validate_key(api_key)
    ensure_allowed(file)
    contents = await file.read()
    img = Image.open(BytesIO(contents))
    img_w, img_h = img.size

    if all(v is not None for v in [x, y, width, height]):
        img = img.crop((x, y, x + width, y + height))
    elif aspect_ratio:
        try:
            w_ratio, h_ratio = map(int, aspect_ratio.split(":"))
            target_ratio = w_ratio / h_ratio
            current_ratio = img_w / img_h
            if current_ratio > target_ratio:
                new_w = int(target_ratio * img_h)
                left = (img_w - new_w) // 2
                right = left + new_w
                img = img.crop((left, 0, right, img_h))
            else:
                new_h = int(img_w / target_ratio)
                top = (img_h - new_h) // 2
                bottom = top + new_h
                img = img.crop((0, top, img_w, bottom))
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid aspect ratio format. Use like '1:1' or '16:9'.")
    else:
        raise HTTPException(status_code=400, detail="Provide coordinates or aspect_ratio.")

    out_buf = BytesIO()
    img.save(out_buf, format=output_format.upper())
    out_buf.seek(0)
    out_bytes = out_buf.read()

    out_path, url = save_image_bytes_and_get_url(out_bytes, request, prefix="crop", ext=output_format.lower())
    increment_usage(api_key)
    return JSONResponse(content=make_success("Image cropped", url, user))

# -------------------- Enhance --------------------
@app.post("/enhance")
async def enhance_image(request: Request,
                        api_key: str = Header(..., alias="x-api-key"),
                        file: UploadFile = File(...),
                        brightness: float = Form(1.0),
                        contrast: float = Form(1.0),
                        sharpness: float = Form(1.0),
                        blur: float = Form(0.0),
                        grayscale: bool = Form(False),
                        output_format: str = Form("png")):
    user = validate_key(api_key)
    ensure_allowed(file)
    contents = await file.read()
    img = Image.open(BytesIO(contents)).convert("RGB")

    img = ImageEnhance.Brightness(img).enhance(brightness)
    img = ImageEnhance.Contrast(img).enhance(contrast)
    img = ImageEnhance.Sharpness(img).enhance(sharpness)

    if blur > 0:
        img = img.filter(ImageFilter.GaussianBlur(blur))

    if grayscale:
        img = img.convert("L")

    out_buf = BytesIO()
    img.save(out_buf, format=output_format.upper())
    out_buf.seek(0)
    out_bytes = out_buf.read()

    out_path, url = save_image_bytes_and_get_url(out_bytes, request, prefix="enh", ext=output_format.lower())
    increment_usage(api_key)
    return JSONResponse(content=make_success("Image enhanced", url, user))

# -------------------- Convert --------------------
@app.post("/convert")
async def convert_image(request: Request,
                        api_key: str = Header(..., alias="x-api-key"),
                        file: UploadFile = File(...),
                        target_format: str = Form("png")):
    user = validate_key(api_key)
    ensure_allowed(file)
    contents = await file.read()
    img = Image.open(BytesIO(contents))
    if target_format.lower() == "jpg":
        target_format = "JPEG"

    out_buf = BytesIO()
    img.convert("RGB").save(out_buf, format=target_format.upper())
    out_buf.seek(0)
    out_bytes = out_buf.read()

    out_path, url = save_image_bytes_and_get_url(out_bytes, request, prefix="conv", ext=target_format.lower())
    increment_usage(api_key)
    return JSONResponse(content=make_success("Image converted", url, user))

# -------------------- Watermark (text) --------------------
@app.post("/watermark")
async def add_watermark(request: Request,
                        api_key: str = Header(..., alias="x-api-key"),
                        file: UploadFile = File(...),
                        watermark_text: str = Form("Futurist Digital"),
                        position: str = Form("bottom-right"),
                        opacity: float = Form(0.3),
                        font_size: int = Form(32),
                        output_format: str = Form("png")):
    user = validate_key(api_key)
    ensure_allowed(file)
    contents = await file.read()
    base_img = Image.open(BytesIO(contents)).convert("RGBA")

    txt_layer = Image.new("RGBA", base_img.size, (255,255,255,0))
    draw = ImageDraw.Draw(txt_layer)
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0,0), watermark_text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    margin = 10
    positions = {
        "top-left": (margin, margin),
        "top-right": (base_img.width - text_w - margin, margin),
        "center": ((base_img.width - text_w)//2, (base_img.height - text_h)//2),
        "bottom-left": (margin, base_img.height - text_h - margin),
        "bottom-right": (base_img.width - text_w - margin, base_img.height - text_h - margin)
    }
    pos = positions.get(position, positions["bottom-right"])
    draw.text(pos, watermark_text, font=font, fill=(255,255,255,int(255*opacity)))

    watermarked = Image.alpha_composite(base_img, txt_layer)
    out_buf = BytesIO()
    watermarked.convert("RGB").save(out_buf, format=output_format.upper())
    out_buf.seek(0)
    out_bytes = out_buf.read()

    out_path, url = save_image_bytes_and_get_url(out_bytes, request, prefix="wm", ext=output_format.lower())
    increment_usage(api_key)
    return JSONResponse(content=make_success("Watermark added", url, user))

# -------------------- Filter (single) --------------------
@app.post("/filter")
async def apply_filter(request: Request,
                       api_key: str = Header(..., alias="x-api-key"),
                       file: UploadFile = File(...),
                       filter_type: str = Form("grayscale"),
                       intensity: float = Form(1.0)):
    user = validate_key(api_key)
    ensure_allowed(file)
    contents = await file.read()
    img = Image.open(BytesIO(contents)).convert("RGB")

    if filter_type == "grayscale":
        img = ImageOps.grayscale(img)
    elif filter_type == "sepia":
        img = ImageOps.colorize(ImageOps.grayscale(img), "#704214", "#C0A080")
    elif filter_type == "blur":
        img = img.filter(ImageFilter.GaussianBlur(radius=intensity*2))
    elif filter_type == "sharpen":
        img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))
    elif filter_type == "invert":
        img = ImageOps.invert(img)
    else:
        raise HTTPException(status_code=400, detail="Unsupported filter type")

    out_buf = BytesIO()
    img.save(out_buf, format="PNG")
    out_buf.seek(0)
    out_bytes = out_buf.read()

    out_path, url = save_image_bytes_and_get_url(out_bytes, request, prefix="flt", ext="png")
    increment_usage(api_key)
    return JSONResponse(content=make_success("Filter applied", url, user))

# -------------------- Resize (single) --------------------
@app.post("/resize")
async def resize_image(request: Request,
                       api_key: str = Header(..., alias="x-api-key"),
                       file: UploadFile = File(...),
                       width: int = Form(None),
                       height: int = Form(None),
                       scale: float = Form(None),
                       keep_aspect_ratio: bool = Form(True),
                       output_format: str = Form("png")):
    user = validate_key(api_key)
    ensure_allowed(file)
    contents = await file.read()
    img = Image.open(BytesIO(contents))
    orig_w, orig_h = img.size

    if scale:
        new_w = int(orig_w * scale)
        new_h = int(orig_h * scale)
    elif width and height:
        new_w, new_h = width, height
    elif width and keep_aspect_ratio:
        ratio = width / orig_w
        new_w = width
        new_h = int(orig_h * ratio)
    elif height and keep_aspect_ratio:
        ratio = height / orig_h
        new_h = height
        new_w = int(orig_w * ratio)
    else:
        raise HTTPException(status_code=400, detail="Provide width, height, or scale.")

    resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    out_buf = BytesIO()
    resized.save(out_buf, format=output_format.upper())
    out_buf.seek(0)
    out_bytes = out_buf.read()

    out_path, url = save_image_bytes_and_get_url(out_bytes, request, prefix="res", ext=output_format.lower())
    increment_usage(api_key)
    return JSONResponse(content=make_success("Image resized", url, user))

# -------------------- Rotate --------------------
@app.post("/rotate")
async def rotate_image(request: Request,
                       api_key: str = Header(..., alias="x-api-key"),
                       file: UploadFile = File(...),
                       angle: float = Form(...),
                       expand: bool = Form(True),
                       output_format: str = Form("png")):
    user = validate_key(api_key)
    ensure_allowed(file)
    contents = await file.read()
    img = Image.open(BytesIO(contents))
    rotated = img.rotate(-angle, expand=expand)
    out_buf = BytesIO()
    rotated.save(out_buf, format=output_format.upper())
    out_buf.seek(0)
    out_bytes = out_buf.read()

    out_path, url = save_image_bytes_and_get_url(out_bytes, request, prefix="rot", ext=output_format.lower())
    increment_usage(api_key)
    return JSONResponse(content=make_success("Image rotated", url, user))

# -------------------- Flip --------------------
@app.post("/flip")
async def flip_image(request: Request,
                     api_key: str = Header(..., alias="x-api-key"),
                     file: UploadFile = File(...),
                     direction: str = Form(...),
                     output_format: str = Form("png")):
    user = validate_key(api_key)
    ensure_allowed(file)
    contents = await file.read()
    img = Image.open(BytesIO(contents))

    if direction.lower() == "horizontal":
        flipped = img.transpose(Image.FLIP_LEFT_RIGHT)
    elif direction.lower() == "vertical":
        flipped = img.transpose(Image.FLIP_TOP_BOTTOM)
    else:
        raise HTTPException(status_code=400, detail="Invalid direction!")

    out_buf = BytesIO()
    flipped.save(out_buf, format=output_format.upper())
    out_buf.seek(0)
    out_bytes = out_buf.read()

    out_path, url = save_image_bytes_and_get_url(out_bytes, request, prefix="flp", ext=output_format.lower())
    increment_usage(api_key)
    return JSONResponse(content=make_success("Image flipped", url, user))

# -------------------- Compress (single) --------------------
@app.post("/compress")
async def compress_image(request: Request,
                        api_key: str = Header(..., alias="x-api-key"),
                        file: UploadFile = File(...),
                        quality: int = Form(80),
                        output_format: str = Form("jpeg")):
    user = validate_key(api_key)
    ensure_allowed(file)
    contents = await file.read()
    img = Image.open(BytesIO(contents))
    if output_format.lower() in ["jpeg", "jpg", "webp"] and img.mode == "RGBA":
        img = img.convert("RGB")

    out_buf = BytesIO()
    img.save(out_buf, format=output_format.upper(), optimize=True, quality=quality)
    out_buf.seek(0)
    out_bytes = out_buf.read()

    out_path, url = save_image_bytes_and_get_url(out_bytes, request, prefix="cmp", ext=output_format.lower())
    increment_usage(api_key)
    return JSONResponse(content=make_success("Image compressed", url, user))

# -------------------- Bulk Compress --------------------
@app.post("/bulk-compress")
async def bulk_compress(request: Request,
                        api_key: str = Header(..., alias="x-api-key"),
                        files: list[UploadFile] = File(...),
                        quality: int = Form(80),
                        output_format: str = Form("jpeg")):
    user = validate_key(api_key)
    zip_buf = BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            if f.content_type not in ALLOWED_TYPES:
                continue
            contents = await f.read()
            img = Image.open(BytesIO(contents))
            if output_format.lower() in ["jpeg", "jpg", "webp"] and img.mode == "RGBA":
                img = img.convert("RGB")
            out_img_buf = BytesIO()
            img.save(out_img_buf, format=output_format.upper(), optimize=True, quality=quality)
            out_img_buf.seek(0)
            name = f"{os.path.splitext(f.filename)[0]}_compressed.{output_format.lower()}"
            zf.writestr(name, out_img_buf.read())

    zip_buf.seek(0)
    zip_bytes = zip_buf.read()
    # Save zip and provide URL
    zip_name = f"bulk_{uuid.uuid4().hex}.zip"
    zip_path = os.path.join(OUTPUTS_DIR, zip_name)
    with open(zip_path, "wb") as f:
        f.write(zip_bytes)

    base = str(request.base_url).rstrip("/")
    url = f"{base}/outputs/{zip_name}"
    increment_usage(api_key)
    return JSONResponse(content=make_success("Bulk compress ready", url, user))

# -------------------- Resize Bulk --------------------
@app.post("/resize-bulk")
async def resize_bulk(request: Request,
                      api_key: str = Header(..., alias="x-api-key"),
                      files: list[UploadFile] = File(...),
                      width: int = Form(...),
                      height: int = Form(...),
                      keep_aspect: bool = Form(True),
                      output_format: str = Form("jpeg")):
    user = validate_key(api_key)
    zip_buf = BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            if f.content_type not in ALLOWED_TYPES:
                continue
            contents = await f.read()
            img = Image.open(BytesIO(contents))
            if keep_aspect:
                img.thumbnail((width, height))
            else:
                img = img.resize((width, height))
            if output_format.lower() in ["jpeg", "jpg", "webp"] and img.mode == "RGBA":
                img = img.convert("RGB")
            out_img_buf = BytesIO()
            img.save(out_img_buf, format=output_format.upper(), optimize=True)
            out_img_buf.seek(0)
            name = f"{os.path.splitext(f.filename)[0]}_{width}x{height}.{output_format.lower()}"
            zf.writestr(name, out_img_buf.read())

    zip_buf.seek(0)
    zip_bytes = zip_buf.read()
    zip_name = f"resized_{uuid.uuid4().hex}.zip"
    zip_path = os.path.join(OUTPUTS_DIR, zip_name)
    with open(zip_path, "wb") as f:
        f.write(zip_bytes)

    base = str(request.base_url).rstrip("/")
    url = f"{base}/outputs/{zip_name}"
    increment_usage(api_key)
    return JSONResponse(content=make_success("Bulk resize ready", url, user))

# -------------------- Auto-Adjust --------------------
@app.post("/auto-adjust")
async def auto_adjust(request: Request,
                      api_key: str = Header(..., alias="x-api-key"),
                      file: UploadFile = File(...),
                      enhance_color: bool = Form(True),
                      enhance_contrast: bool = Form(True),
                      enhance_brightness: bool = Form(True)):
    user = validate_key(api_key)
    ensure_allowed(file)
    contents = await file.read()
    img = Image.open(BytesIO(contents)).convert("RGB")

    if enhance_color:
        img = ImageEnhance.Color(img).enhance(1.2)
    if enhance_contrast:
        img = ImageEnhance.Contrast(img).enhance(1.1)
    if enhance_brightness:
        img = ImageEnhance.Brightness(img).enhance(1.1)

    img = ImageOps.autocontrast(img)

    out_buf = BytesIO()
    img.save(out_buf, format="PNG")
    out_buf.seek(0)
    out_bytes = out_buf.read()

    out_path, url = save_image_bytes_and_get_url(out_bytes, request, prefix="auto", ext="png")
    increment_usage(api_key)
    return JSONResponse(content=make_success("Auto-adjust applied", url, user))
@app.get("/admin/users")
def list_all_users(x_admin_key: str = Header(None)):
    """
    🔒 Admin-only endpoint — Lists all registered API users.
    Requires header: x-admin-key
    Example curl:
    curl -X GET http://127.0.0.1:8000/admin/users \
      -H "x-admin-key: YOUR_ADMIN_SECRET_KEY"
    """
    if x_admin_key != ADMIN_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized — Invalid admin key")

    try:
        users = load_users()
        result = []

        for api_key, info in users.items():
            result.append({
                "api_key": api_key,
                "plan": info.get("plan"),
                "limit": info.get("limit"),
                "usage": info.get("usage"),
                "remaining": (
                    None if info.get("limit") is None else
                    max(0, info["limit"] - info["usage"])
                ),
                "expiry": info.get("expiry"),
                "created_at": info.get("created_at")
            })

        return {
            "status": "success",
            "total_users": len(result),
            "users": result
        }

    except Exception as e:
        raise HTTPException(st`atus_code=500, detail=f"Error loading users: {str(e)}")
@app.post("/admin/reset-usage")
def admin_reset_usage(
    api_key: str = Form(...),
    x_admin_key: str = Header(None)
):
    """
    🔒 Admin-only — Reset usage count for a user.
    Example:
    curl -X POST http://127.0.0.1:8000/admin/reset-usage \
      -H "x-admin-key: YOUR_ADMIN_SECRET_KEY" \
      -F "api_key=USER_API_KEY"
    """
    if x_admin_key != ADMIN_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized — Invalid admin key")

    users = load_users()
    if api_key not in users:
        raise HTTPException(status_code=404, detail="User not found")

    users[api_key]["usage"] = 0
    save_users(users)
    return {"status": "success", "message": f"Usage reset for {api_key}"}


@app.post("/admin/delete-user")
def admin_delete_user(
    api_key: str = Form(...),
    x_admin_key: str = Header(None)
):
    """
    🔒 Admin-only — Delete a user's API key.
    Example:
    curl -X POST http://127.0.0.1:8000/admin/delete-user \
      -H "x-admin-key: YOUR_ADMIN_SECRET_KEY" \
      -F "api_key=USER_API_KEY"
    """
    if x_admin_key != ADMIN_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized — Invalid admin key")

    users = load_users()
    if api_key not in users:
        raise HTTPException(status_code=404, detail="User not found")

    del users[api_key]
    save_users(users)
    return {"status": "success", "message": f"Deleted API key: {api_key}"}


@app.post("/admin/upgrade")
def admin_upgrade_user(
    api_key: str = Form(...),
    new_plan: str = Form("paid"),
    x_admin_key: str = Header(None)
):
    """
    🔒 Admin-only — Upgrade or downgrade a user’s plan.
    Example:
    curl -X POST http://127.0.0.1:8000/admin/upgrade \
      -H "x-admin-key: YOUR_ADMIN_SECRET_KEY" \
      -F "api_key=USER_API_KEY" \
      -F "new_plan=paid"
    """
    if x_admin_key != ADMIN_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized — Invalid admin key")

    users = load_users()
    if api_key not in users:
        raise HTTPException(status_code=404, detail="User not found")

    if new_plan not in ["free", "paid"]:
        raise HTTPException(status_code=400, detail="Invalid plan type. Use 'free' or 'paid'.")

    user = users[api_key]
    now = datetime.datetime.now()

    if new_plan == "free":
        user["plan"] = "free"
        user["limit"] = 10
        user["expiry"] = (now + datetime.timedelta(days=30)).isoformat()
    else:
        user["plan"] = "paid"
        user["limit"] = None
        user["expiry"] = (now + datetime.timedelta(days=365)).isoformat()

    save_users(users)
    return {"status": "success", "message": f"User {api_key} upgraded to {new_plan} plan"}
