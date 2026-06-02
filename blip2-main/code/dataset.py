import os
import pandas as pd
from PIL import Image
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms


class Flickr8kDataset(Dataset):
    def __init__(self, data_dir, num_images=200, transform=None):
        self.data_dir = data_dir
        self.image_dir = os.path.join(data_dir, "Images")
        self.captions_file = os.path.join(data_dir, "captions.txt")
        
        self.transform = transform
        
        df = pd.read_csv(self.captions_file)
        
        unique_images = df["image"].unique()[:num_images]
        self.samples = []
        
        for img_name in unique_images:
            captions = df[df["image"] == img_name]["caption"].tolist()
            for cap in captions:
                self.samples.append((img_name, cap))
        
        print(f"Loaded {len(self.samples)} samples from {len(unique_images)} images")
    
    def __len__(self):
        return len(self.samples)
    
    def __getitem__(self, idx):
        img_name, caption = self.samples[idx]
        img_path = os.path.join(self.image_dir, img_name)
        image = Image.open(img_path).convert("RGB")
        
        if self.transform:
            image = self.transform(image)
        
        return image, caption


def get_transform():
    return transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])


def get_dataloader(data_dir, batch_size=8, num_images=200):
    transform = get_transform()
    dataset = Flickr8kDataset(data_dir, num_images=num_images, transform=transform)
    num_workers = min(4, os.cpu_count() // 2) if os.cpu_count() else 0
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True, num_workers=num_workers, pin_memory=True)
    return dataloader
