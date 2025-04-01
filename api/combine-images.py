from flask import Flask, request, send_file
from PIL import Image
import requests
import io
import os
import tempfile
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Move background image to static folder for Vercel
BACKGROUND_IMAGE_PATH = "./Background_image/bg.jpg"

# Spacing adjustments
SPACING_PX = 40
HORIZONTAL_SPACING_PX = 25
VERTICAL_SPACING_PX = 40

# Album dimensions
CROP_SIZE = 250  # Crop size for uniformity
ROWS, COLS = 3, 3  # Grid size

def crop_center(image, crop_width, crop_height):
    """Crop image to center to ensure uniform size."""
    width, height = image.size
    left = (width - crop_width) / 2
    top = (height - crop_height) / 2
    right = (width + crop_width) / 2
    bottom = (height + crop_height) / 2
    return image.crop((left, top, right, bottom))

def download_and_process_image(url):
    """Download an image, convert it to a square, and resize it."""
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        img = Image.open(io.BytesIO(response.content)).convert("RGB")

        # Crop image to square format
        img = crop_center(img, CROP_SIZE, CROP_SIZE)

        return img
    except Exception as e:
        print(f"Error downloading image: {e}")
        return None

def create_album(image_urls):
    """Arrange images into an album-style format."""
    total_width = COLS * CROP_SIZE + (COLS - 1) * HORIZONTAL_SPACING_PX
    total_height = ROWS * CROP_SIZE + (ROWS - 1) * VERTICAL_SPACING_PX

    try:
        background = Image.open(BACKGROUND_IMAGE_PATH).resize((total_width, total_height))
    except Exception as e:
        print(f"Error loading background: {e}")
        background = Image.new("RGB", (total_width, total_height), (255, 255, 255))

    album_image = background

    for idx, url in enumerate(image_urls):
        if idx >= ROWS * COLS:
            break
        img = download_and_process_image(url)
        if img:
            row, col = divmod(idx, COLS)
            x_offset = col * (CROP_SIZE + HORIZONTAL_SPACING_PX)
            y_offset = row * (CROP_SIZE + VERTICAL_SPACING_PX)
            album_image.paste(img, (x_offset, y_offset))

    return album_image

@app.route('/api/generate-album', methods=['GET'])
def generate_album():
    """API endpoint to create an album-style image."""
    image_urls = [request.args.get(f'pic{i}') for i in range(1, 10)]
    image_urls = [url for url in image_urls if url]

    if not image_urls:
        return "No images provided", 400

    album_image = create_album(image_urls)

    # Save image in Vercel's writable `/tmp/` directory
    temp_path = os.path.join(tempfile.gettempdir(), "album.jpg")
    album_image.save(temp_path, format="JPEG", quality=85, optimize=True)

    return send_file(temp_path, mimetype='image/jpeg')

# Run only when not on Vercel
if __name__ == "__main__":
    app.run(debug=True)
