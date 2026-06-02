import torch
import os
import sys
from PIL import Image
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


def main():
    data_dir = "../data"
    image_dir = os.path.join(data_dir, "Images")
    captions_file = os.path.join(data_dir, "captions.txt")
    
    df = pd.read_csv(captions_file)
    unique_images = df["image"].unique()[:5]
    
    model, device = load_model()
    transform = get_transform()
    
    print("=" * 80)
    print("Generating captions for sample images:")
    print("=" * 80)
    
    for img_name in unique_images:
        img_path = os.path.join(image_dir, img_name)
        real_captions = df[df["image"] == img_name]["caption"].tolist()
        
        generated_caption = generate_caption(model, img_path, transform, device)
        
        print(f"\nImage: {img_name}")
        print(f"Real captions:")
        for i, cap in enumerate(real_captions[:3], 1):
            print(f"  {i}. {cap}")
        print(f"Generated caption:")
        print(f"  {generated_caption}")
        print("-" * 80)


if __name__ == "__main__":
    main()
