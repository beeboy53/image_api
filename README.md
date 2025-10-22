🧠 Image Processing API (FastAPI + Python)

An all-in-one AI image processing API built with FastAPI — includes background removal, compression, enhancement, filters, cropping, watermarking, and more.

Supports API key authentication, usage limits, and admin controls for user management.

🚀 Features

✅ Background removal (AI-powered via rembg)
✅ Resize, crop, convert, compress images
✅ Enhance brightness, contrast, sharpness
✅ Apply filters and watermarks
✅ Auto color/contrast adjustment
✅ Bulk operations
✅ API key system (free & paid plans)
✅ Admin panel for user management
✅ JSON API responses with hosted image URLs

⚙️ Requirements

Python 3.9+ (tested on 3.13)

FastAPI

Uvicorn

Pillow

rembg

onnxruntime (CPU version)

jsonschema

pymatting

scikit-image

Install everything:

pip install fastapi uvicorn pillow rembg onnxruntime

🧩 Run the API

Activate your environment:

.\venv\Scripts\activate


Start server:

python -m uvicorn main:app --reload


Open docs:
👉 http://127.0.0.1:8000/docs

🔐 API Authentication

All endpoints require:

Header: x-api-key: YOUR_KEY


Generate your own API key (admin-only):

curl -X POST "http://127.0.0.1:8000/register-key" \
  -H "x-admin-key: YOUR_ADMIN_SECRET_KEY" \
  -F "email=you@example.com" \
  -F "plan=free"

📸 Example Endpoints
Endpoint	Method	Description
/remove-bg	POST	Remove image background
/optimize	POST	Compress or resize image
/crop	POST	Crop by coordinates or aspect ratio
/enhance	POST	Brightness, contrast, sharpness
/filter	POST	Apply visual filter
/watermark	POST	Add text watermark
/auto-adjust	POST	Auto color correction
/convert	POST	Convert to JPG/PNG/WebP
/usage	GET	Get key usage & limits
/admin/users	GET	List all API users
/admin/upgrade	POST	Change user plan
/admin/reset-usage	POST	Reset usage count
/admin/delete-user	POST	Delete API key
/admin/stats	GET	Platform stats
🧑‍💻 Example Usage (JavaScript)
async function removeBg(file) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch("http://127.0.0.1:8000/remove-bg", {
    method: "POST",
    headers: {
      "x-api-key": "YOUR_API_KEY"
    },
    body: formData
  });

  const blob = await response.blob();
  const imageUrl = URL.createObjectURL(blob);
  document.querySelector("#preview").src = imageUrl;
}

🐘 Example Usage (PHP)
Remove Background
<?php
$url = "http://127.0.0.1:8000/remove-bg";
$apiKey = "YOUR_API_KEY";
$file = new CURLFile("image.jpg", "image/jpeg");

$postFields = [
  "file" => $file
];

$ch = curl_init($url);
curl_setopt($ch, CURLOPT_HTTPHEADER, ["x-api-key: $apiKey"]);
curl_setopt($ch, CURLOPT_POST, 1);
curl_setopt($ch, CURLOPT_POSTFIELDS, $postFields);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);

$response = curl_exec($ch);
curl_close($ch);
file_put_contents("output.png", $response);
echo "Background removed and saved as output.png";
?>

🧑‍💼 Admin API (Protected)

Header:

x-admin-key: YOUR_ADMIN_SECRET_KEY

Get all users
curl -X GET "http://127.0.0.1:8000/admin/users" \
  -H "x-admin-key: YOUR_ADMIN_SECRET_KEY"

Reset usage
curl -X POST "http://127.0.0.1:8000/admin/reset-usage" \
  -H "x-admin-key: YOUR_ADMIN_SECRET_KEY" \
  -F "api_key=USER_API_KEY"

Upgrade plan
curl -X POST "http://127.0.0.1:8000/admin/upgrade" \
  -H "x-admin-key: YOUR_ADMIN_SECRET_KEY" \
  -F "api_key=USER_API_KEY" \
  -F "new_plan=paid"

Get platform stats
curl -X GET "http://127.0.0.1:8000/admin/stats" \
  -H "x-admin-key: YOUR_ADMIN_SECRET_KEY"

🧠 Notes

Free plan → 10 images/month (auto-renews monthly)

Paid plan → 1-year validity, unlimited usage

Keys stored in users.json

You can move to MySQL or Firebase later easily

/outputs/ folder hosts all generated images (served automatically)
