from flask import Flask, request, send_file
from PIL import Image
import requests
import io
import tempfile
import os
from flask_cors import CORS

# Enable CORS for all routes
app = Flask(__name__)

# Enable CORS for all routes
CORS(app)

# Path to the background image
BACKGROUND_IMAGE_PATH = "./Background_image/bg.jpg"

# Define the pixels equivalent to 0.5 cm assuming 72 DPI (1 inch = 2.54 cm, 1 inch = 72 pixels)
SPACING_PX = 50  # 0.5 cm in pixels at 72 DPI
HORIZONTAL_SPACING_PX = 50  # Remove horizontal space completely (set to 0 pixels)
VERTICAL_SPACING_PX = SPACING_PX  # Space between images vertically (0.5 cm)

# Image size is 8x10.5 inches, so at 72 DPI:
IMAGE_WIDTH_PX = 500  # 8 inches * 72 DPI
IMAGE_HEIGHT_PX = 500  # 10.5 inches * 72 DPI

# Updated background image size
BACKGROUND_WIDTH_PX = 1600
BACKGROUND_HEIGHT_PX = 1600
def resize_and_crop_image(image, target_width, target_height):
    """Resize and crop the image to fit the target dimensions by zooming in on the center, removing any black bars."""
    original_width, original_height = image.size
    aspect_ratio = original_width / original_height

    # Resize the image so that it fully covers the target width and height, zooming in if necessary
    if aspect_ratio > 1:  # Image is wider than it is tall
        new_width = max(target_width, original_width)
        new_height = int(new_width / aspect_ratio)
        if new_height < target_height:  # If the resized image is shorter, adjust it to fit target height
            new_height = target_height
            new_width = int(new_height * aspect_ratio)
    else:  # Image is taller than it is wide
        new_height = max(target_height, original_height)
        new_width = int(new_height * aspect_ratio)
        if new_width < target_width:  # If the resized image is narrower, adjust it to fit target width
            new_width = target_width
            new_height = int(new_width / aspect_ratio)

    # Resize the image to fill the target dimensions, potentially zooming in
    resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

    # Calculate the crop box to center the image within the target size
    left = (new_width - target_width) / 2
    top = (new_height - target_height) / 2
    right = (new_width + target_width) / 2
    bottom = (new_height + target_height) / 2

    # Crop the image to the target dimensions (zoomed in without black bars)
    cropped_image = resized_image.crop((left, top, right, bottom))

    return cropped_image


def download_and_resize_image(url):
    """Download an image, resize and crop it to fit within max width and height."""
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        img = Image.open(io.BytesIO(response.content))
        img = img.convert("RGB")  # Ensure consistent mode

        # Resize and crop to fit within the desired dimensions
        cropped_img = resize_and_crop_image(img, IMAGE_WIDTH_PX, IMAGE_HEIGHT_PX)

        return cropped_img
    except Exception as e:
        print(f"Error downloading or processing image: {e}")
        return None


def create_image_grid(image_urls, rows, cols, horizontal_spacing, vertical_spacing):
    """Combine images into a grid with space between them while zooming in each image."""
    # Calculate the total grid size (including spacing)
    total_width = cols * IMAGE_WIDTH_PX + (cols - 1) * horizontal_spacing
    total_height = rows * IMAGE_HEIGHT_PX + (rows - 1) * vertical_spacing

    # Load the background image and resize it to match the new size
    try:
        background = Image.open(BACKGROUND_IMAGE_PATH)
        background = background.resize((BACKGROUND_WIDTH_PX, BACKGROUND_HEIGHT_PX))
    except Exception as e:
        print(f"Error loading background image: {e}")
        background = Image.new("RGB", (BACKGROUND_WIDTH_PX, BACKGROUND_HEIGHT_PX), (255, 255, 255))  # Blank white background

    grid_image = background  # Use the background image

    for idx, url in enumerate(image_urls):
        if idx >= rows * cols:
            break
        img = download_and_resize_image(url)

        # Apply zoom-in and crop to each image
        if img:
            img = resize_and_crop_image(img, IMAGE_WIDTH_PX, IMAGE_HEIGHT_PX)

            row, col = divmod(idx, cols)
            x_offset = col * (IMAGE_WIDTH_PX + horizontal_spacing)  # Add horizontal spacing between columns
            y_offset = row * (IMAGE_HEIGHT_PX + vertical_spacing)  # Add vertical spacing between rows
            grid_image.paste(img, (x_offset, y_offset))

    return grid_image


@app.route('/api/combine-images', methods=['GET'])
def combine_images():
    """API endpoint to combine images into a grid."""
    image_urls = [request.args.get(f'pic{i}') for i in range(1, 13)]
    image_urls = [url for url in image_urls if url]

    rows, cols = 3, 3  # Default grid of 4 rows by 3 columns
    horizontal_spacing = HORIZONTAL_SPACING_PX  # No space between images horizontally
    vertical_spacing = VERTICAL_SPACING_PX  # Space between each image vertically (0.5 cm)

    if not image_urls:
        return "No images provided", 400

    # Adjust the number of columns and resize images to fill the grid
    grid_image = create_image_grid(image_urls, rows, cols, horizontal_spacing, vertical_spacing)

    # Use a temporary file to save the image
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
        temp_path = temp_file.name
        grid_image.save(temp_path)

    # Serve the image and schedule cleanup
    response = send_file(temp_path, mimetype='image/png')

    # Ensure the file is deleted after sending
    @response.call_on_close
    def cleanup_temp_file():
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception as cleanup_error:
            print(f"Error cleaning up temporary file: {cleanup_error}")

    return response

if __name__ == '__main__':
    app.run(debug=True)
