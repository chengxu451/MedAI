import torch
import os
import sys
from PIL import Image, ImageDraw, ImageFont
import pandas as pd

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from model import MiniBLIP2
from dataset import get_transform


def load_model(checkpoint_path=None, device=None):
    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    model = MiniBLIP2(
        vision_model_name="openai/clip-vit-base-patch32",
        llm_model_name="facebook/opt-125m"
    ).to(device)
    
    if checkpoint_path is not None and os.path.exists(checkpoint_path):
        checkpoint = torch.load(checkpoint_path, map_location=device)
        model.load_state_dict(checkpoint["model_state_dict"])
        print(f"Loaded checkpoint from {checkpoint_path}")
    
    model.eval()
    return model, device


def generate_caption(model, image_path, transform, device, max_length=50):
    image = Image.open(image_path).convert("RGB")
    image_tensor = transform(image).unsqueeze(0).to(device)
    
    with torch.no_grad():
        captions = model.generate(image_tensor, max_length=max_length)
    
    return captions[0]


def create_visualization(image_path, real_captions, generated_caption, output_path):
    img = Image.open(image_path).convert("RGB")
    
    img_width, img_height = img.size
    
    text_height = 200
    total_height = img_height + text_height
    
    result = Image.new('RGB', (img_width, total_height), color=(255, 255, 255))
    result.paste(img, (0, 0))
    
    draw = ImageDraw.Draw(result)
    
    try:
        font = ImageFont.truetype("arial.ttf", 12)
    except:
        font = ImageFont.load_default()
    
    y = img_height + 10
    
    draw.text((10, y), "Real Captions:", fill=(0, 0, 0), font=font)
    y += 20
    
    for i, cap in enumerate(real_captions[:3], 1):
        draw.text((20, y), f"{i}. {cap[:60]}...", fill=(0, 0, 128), font=font)
        y += 18
    
    y += 10
    draw.text((10, y), "Generated Caption:", fill=(0, 0, 0), font=font)
    y += 20
    
    lines = []
    current_line = ""
    for word in generated_caption.split():
        if len(current_line) + len(word) + 1 <= 60:
            current_line += word + " "
        else:
            lines.append(current_line)
            current_line = word + " "
    if current_line:
        lines.append(current_line)
    
    for line in lines[:3]:
        draw.text((20, y), line, fill=(128, 0, 0), font=font)
        y += 18
    
    result.save(output_path)
    print(f"Saved visualization to {output_path}")


def main():
    data_dir = "../data"
    image_dir = os.path.join(data_dir, "Images")
    captions_file = os.path.join(data_dir, "captions.txt")
    output_dir = "../visualizations"
    
    os.makedirs(output_dir, exist_ok=True)
    
    df = pd.read_csv(captions_file)
    unique_images = df["image"].unique()[:5]
    
    model, device = load_model()
    transform = get_transform()
    
    print("=" * 80)
    print("Generating visualizations...")
    print("=" * 80)
    
    for img_name in unique_images:
        img_path = os.path.join(image_dir, img_name)
        real_captions = df[df["image"] == img_name]["caption"].tolist()
        
        generated_caption = generate_caption(model, img_path, transform, device)
        
        output_path = os.path.join(output_dir, f"result_{img_name}")
        create_visualization(img_path, real_captions, generated_caption, output_path)
        
        print(f"\nImage: {img_name}")
        print(f"Real captions:")
        for i, cap in enumerate(real_captions[:3], 1):
            print(f"  {i}. {cap}")
        print(f"Generated caption:")
        print(f"  {generated_caption}")
        print("-" * 80)


if __name__ == "__main__":
    main()