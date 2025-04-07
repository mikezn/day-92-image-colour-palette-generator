from PIL import Image, ExifTags
from flask import Flask, render_template, request, redirect, url_for, jsonify, send_from_directory
import os

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@app.route("/", methods=["GET"])
def home():
    return render_template(
        'index.html',
        top_colors=None,
        original_image=None,
        masked_image=None
    )


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


@app.route('/upload', methods=['POST'])
def upload_image():
    # remove existing images from upload folder
    for filename in os.listdir(UPLOAD_FOLDER):
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"Error deleting file {file_path}: {e}")

    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400

    file = request.files['image']
    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)

    image = Image.open(filepath)
    image = fix_image_orientation(image).convert('RGB')
    top_colors = analyze_img(image)

    masked_filename = 'masked.png'
    original_filename = os.path.basename(filepath)  # or rename if needed

    return render_template(
        'index.html',
        top_colors=top_colors,
        masked_image=masked_filename,
        original_image=original_filename
    )



def analyze_img(img):
    colors = img.getcolors(maxcolors=1000000)
    if not colors:
        raise ValueError("Too many unique colors in image")

    # Get top 10 most common colors
    top_colors = sorted(colors, key=lambda x: x[0], reverse=True)[:10]
    top_rgb_values = [color for count, color in top_colors]

    # Create an RGBA version for transparency
    rgba_img = img.convert('RGBA')
    width, height = rgba_img.size
    pixels = rgba_img.load()

    for y in range(height):
        for x in range(width):
            r, g, b, a = pixels[x, y]
            if (r, g, b) not in top_rgb_values:
                # Make non-top-color pixels solid gray for visibility
                pixels[x, y] = (80, 80, 80, 255)  # dark gray & fully opaque

    masked_path = os.path.join('uploads', 'masked.png')
    rgba_img.save(masked_path)

    return top_colors


# sometimes there's orientation metadata that get's lost along the way. This fixes it.
def fix_image_orientation(image):
    try:
        for orientation in ExifTags.TAGS.keys():
            if ExifTags.TAGS[orientation] == 'Orientation':
                break

        exif = image._getexif()
        if exif is not None:
            orientation_value = exif.get(orientation)
            if orientation_value == 3:
                image = image.rotate(180, expand=True)
            elif orientation_value == 6:
                image = image.rotate(270, expand=True)
            elif orientation_value == 8:
                image = image.rotate(90, expand=True)
    except (AttributeError, KeyError, IndexError):
        pass  # image doesn't have EXIF data

    return image



if __name__ == "__main__":
    app.run(debug=True)