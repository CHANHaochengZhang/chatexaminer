# %%
# Import required libraries
import os
from pathlib import Path
from typing import List

import pytesseract
from PIL import Image

# Set the path to the Tesseract executable if it's not in your PATH
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'  # Windows example

# Define the directory containing images
IMAGE_DIR = Path("../knowledge/images")  # Adjust the path as necessary


def extract_text_from_images(image_directory: Path) -> List[str]:
    """Extract text from images using OCR."""
    extracted_texts = []

    for filename in os.listdir(image_directory):
        if not filename.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".gif")):
            continue

        file_path = image_directory / filename
        try:
            # Open the image file
            with Image.open(file_path) as img:
                # Use pytesseract to do OCR on the image
                text = pytesseract.image_to_string(img)
                extracted_texts.append(text.strip())
                print(
                    f"Extracted text from {filename}: {text.strip()[:100]}..."
                )  # Print a preview of the extracted text

        except Exception as e:
            print(f"Error processing {filename}: {str(e)}")
            continue

    return extracted_texts


# Extract text from images
extracted_formulas = extract_text_from_images(IMAGE_DIR)

# Print the results
print(f"Total formulas extracted: {len(extracted_formulas)}")
for idx, formula in enumerate(extracted_formulas):
    print(f"Formula {idx + 1}: {formula}")

# %%
