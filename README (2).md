
# 🖼️ Image Processing API — Full Documentation

## 🚀 Overview
This is a **FastAPI-based Image Processing API** that provides multiple image manipulation tools such as:

- 🧼 **Remove Background**
- 🪄 **Enhance / Filter / Auto-adjust**
- 🖊️ **Watermark**
- 🪞 **Flip / Rotate**
- ✂️ **Crop**
- 📏 **Resize / Optimize / Compress**
- 🧩 **Convert Formats**
- 🔑 **User API Key Management (Free & Paid)**
- ⚙️ **Admin Dashboard (Stats, Users)**

You can use this API in your **HTML/JS frontend**, **PHP apps**, or even **mobile clients**.

---

## ⚙️ 1. Project Structure

```
image_api_mvp/
│
├── main.py               # Main FastAPI app with all endpoints
├── auth_utils.py         # API key & usage validation
├── users.json            # Registered users (auto-created)
├── uploads/              # Uploaded files
├── outputs/              # Processed images (output results)
└── README.md             # This documentation
```

---

## 🧠 2. How It Works Internally

### 🔹 (a) API Key Validation
Every user has a unique **API Key** (generated via `/register-key` by admin).  
All endpoints require the header:

```
x-api-key: YOUR_USER_KEY
```

The `auth_utils.py` file:
- Loads users from `users.json`
- Validates the key and plan (free/paid)
- Tracks monthly usage (e.g., 10 free images/month)
- Automatically blocks expired keys

---

### 🔹 (b) File Upload & Processing
Every image endpoint receives an uploaded file:
```python
file: UploadFile = File(...)
```

It’s temporarily saved in `/uploads`, processed using **Pillow** (and sometimes `rembg` for background removal), then stored in `/outputs`.

Each result generates a public link:
```
{
  "status": "success",
  "message": "Background removed",
  "image_url": "http://127.0.0.1:8000/outputs/processed_file.png"
}
```

---

### 🔹 (c) Admin Panel
Admin endpoints are protected using an **Admin Secret Key**:

```
x-admin-key: YOUR_ADMIN_SECRET
```

Available routes:
- `GET /admin/users` → list all users  
- `GET /admin/stats` → see total usage & remaining  
- `POST /register-key` → create a new API key

---

## 🧩 3. API Endpoints Summary

| Method | Endpoint | Description |
|---------|-----------|-------------|
| `POST` | `/remove-bg` | Remove image background (optional color/image) |
| `POST` | `/optimize` | Resize or compress image |
| `POST` | `/enhance` | Enhance image quality |
| `POST` | `/filter` | Apply filters (grayscale, blur, etc.) |
| `POST` | `/watermark` | Add watermark text or image |
| `POST` | `/convert` | Convert to PNG, JPG, WEBP, etc. |
| `POST` | `/crop` | Crop image with coordinates |
| `POST` | `/resize` | Resize single image |
| `POST` | `/resize-bulk` | Resize multiple images |
| `POST` | `/auto-adjust` | Auto color/contrast correction |
| `GET`  | `/usage` | Check remaining usage |
| `GET`  | `/admin/users` | List all registered users |
| `GET`  | `/admin/stats` | Platform usage summary |
| `POST` | `/register-key` | (Admin-only) Create new API key |

---

## 🧪 4. Example: Testing with cURL

Example: Remove background
```bash
curl -X POST "http://127.0.0.1:8000/remove-bg"   -H "x-api-key: YOUR_API_KEY"   -F "file=@sample.jpg"
```

Example: Resize an image
```bash
curl -X POST "http://127.0.0.1:8000/optimize"   -H "x-api-key: YOUR_API_KEY"   -F "file=@image.png"   -F "width=800"   -F "height=600"
```

---

## 🌐 5. Frontend Integration (HTML + JS)

You can use **Fetch API** in JavaScript to interact with it.

### Example — Remove Background
```html
<input type="file" id="fileInput">
<img id="result">
<script>
const API_URL = "http://127.0.0.1:8000/remove-bg";
const API_KEY = "YOUR_API_KEY";

document.getElementById("fileInput").addEventListener("change", async (e) => {
  const file = e.target.files[0];
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(API_URL, {
    method: "POST",
    headers: { "x-api-key": API_KEY },
    body: formData
  });

  const blob = await res.blob();
  document.getElementById("result").src = URL.createObjectURL(blob);
});
</script>
```

---

## 🧩 6. PHP Integration Example

```php
<?php
$api_key = "YOUR_API_KEY";
$file_path = "test.jpg";

$ch = curl_init("http://127.0.0.1:8000/remove-bg");
curl_setopt($ch, CURLOPT_HTTPHEADER, ["x-api-key: $api_key"]);
curl_setopt($ch, CURLOPT_POST, 1);

$post_fields = [
  'file' => new CURLFile($file_path)
];
curl_setopt($ch, CURLOPT_POSTFIELDS, $post_fields);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);

$response = curl_exec($ch);
file_put_contents("output.png", $response);
curl_close($ch);
echo "✅ Image processed and saved as output.png";
?>
```

---

## ⚡ 7. Running the API

### ▶️ Local Development
```bash
uvicorn main:app --reload
```

Visit:
- API docs → http://127.0.0.1:8000/docs  
- Test panel (your index.html) → http://127.0.0.1:5500/in/

---

### 🧱 Deployment (Live Hosting)
To go live:
1. Deploy FastAPI with **Uvicorn + Nginx** or **Render / Railway / VPS**.
2. Change `127.0.0.1` to your domain (e.g. `https://api.yourdomain.com`).
3. Add HTTPS (e.g. via Cloudflare).
4. Allow CORS for your frontend domain in FastAPI.

---

## 🔐 8. Security Tips
- Use **secure admin key** (store in `.env`)
- Regularly rotate user API keys
- Use HTTPS in production
- Set usage limits to prevent abuse
- Add rate limiting if public

---

## 🧰 9. Dependencies

Install required packages:
```bash
pip install fastapi uvicorn pillow rembg python-multipart onnxruntime
```

(If CUDA warnings appear, you can switch to CPU-only)
```bash
pip uninstall onnxruntime-gpu -y
pip install onnxruntime
```

---

## 🏁 Final Notes

✅ **Frontend app** sends images →  
✅ **FastAPI backend** processes them →  
✅ **Results saved** in `/outputs` and returned as URLs →  
✅ **Admin manages** API keys & usage.

This makes your project a **mini SaaS image API platform**, ready for users to subscribe and use your endpoints.
