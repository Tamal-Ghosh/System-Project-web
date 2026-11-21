import urllib.request, io, json, time
from PIL import Image

img = Image.new("RGB", (224, 224), (200, 100, 50))
buf = io.BytesIO()
img.save(buf, format="PNG")
boundary = "WebKitFormBoundary7MA4YWxkTrZu0gW"

parts = []
def add_field(name, val):
    parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{val}\r\n".encode("utf-8"))

add_field("age", "45")
add_field("sex", "male")
add_field("site", "unknown")
add_field("method", "integrated_gradients")
add_field("n_steps", "10")
add_field("baseline", "blur")
add_field("target_class", "INF")
add_field("fold", "0")
add_field("include_metadata", "true")

parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"image\"; filename=\"lesion.png\"\r\nContent-Type: image/png\r\n\r\n".encode("utf-8") + buf.getvalue() + b"\r\n")
parts.append(f"--{boundary}--\r\n".encode("utf-8"))

body = b"".join(parts)
req = urllib.request.Request("http://127.0.0.1:8000/api/v1/explanations", data=body, headers={
    "Content-Type": f"multipart/form-data; boundary={boundary}"
})
print("Posting to /api/v1/explanations...")
with urllib.request.urlopen(req, timeout=900) as resp:
    print("Status:", resp.status)
    raw = resp.read().decode("utf-8")
    print("Raw body:", raw)
    data = json.loads(raw)

job_id = data["job_id"]
deadline = time.monotonic() + 900
while time.monotonic() < deadline:
    time.sleep(2)
    with urllib.request.urlopen(f"http://127.0.0.1:8000/api/v1/explanations/{job_id}", timeout=30) as resp:
        data = json.load(resp)
    print("Job status:", data.get("status"), data.get("stage"))
    if data.get("status") == "done":
        data = data["result"]
        break
    if data.get("status") == "failed":
        raise RuntimeError(data.get("error", "Explanation failed"))
else:
    raise TimeoutError("Explanation did not finish within 15 minutes")

print("Method:", data.get("method"))
print("Target class:", data.get("target_class"))
print("Fold:", data.get("fold"))
print("Convergence delta:", data.get("convergence_delta"))
print("Image map keys:", list(data.get("image_map", {}).keys()))
print("Data length:", len(data.get("image_map", {}).get("data", "")))
print("Metadata attribution:", data.get("metadata_attribution"))
print("Elapsed ms:", data.get("elapsed_ms"))
