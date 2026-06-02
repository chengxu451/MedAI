import torch
import torch.nn as nn
import torch.optim as optim
from torch.cuda.amp import GradScaler, autocast
from tqdm import tqdm
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dataset import get_dataloader
from model import MiniBLIP2


def train(
    data_dir="../data",
    batch_size=4,
    num_epochs=10,
    lr=1e-4,
    num_images=200,
    device=None,
    gradient_accumulation_steps=1,
    mixed_precision=True
):
    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    print(f"Using device: {device}")
    if device.type == "cuda":
        print(f"GPU: {torch.cuda.get_device_name(device)}")
        print(f"GPU Memory: {torch.cuda.get_device_properties(device).total_memory / 1024**3:.2f} GB")
    
    print("Loading dataset...")
    dataloader = get_dataloader(data_dir, batch_size=batch_size, num_images=num_images)
    
    print("Building model...")
    model = MiniBLIP2(
        vision_model_name="openai/clip-vit-base-patch32",
        llm_model_name="facebook/opt-125m",
        freeze_vision=True,
        freeze_llm=True
    ).to(device)
    
    optimizer = optim.AdamW(
        [p for p in model.parameters() if p.requires_grad],
        lr=lr
    )
    
    scaler = GradScaler(enabled=mixed_precision)
    
    print("Starting training...")
    loss_history = []
    
    for epoch in range(num_epochs):
        model.train()
        total_loss = 0
        optimizer.zero_grad()
        
        progress_bar = tqdm(dataloader, desc=f"Epoch {epoch+1}/{num_epochs}")
        
        for step, (images, captions) in enumerate(progress_bar):
            images = images.to(device)
            
            tokenized = model.tokenizer(
                captions,
                padding=True,
                truncation=True,
                return_tensors="pt"
            ).to(device)
            
            input_ids = tokenized.input_ids
            attention_mask = tokenized.attention_mask
            labels = input_ids.clone()
            labels[attention_mask == 0] = -100
            
            with autocast(enabled=mixed_precision):
                outputs = model(
                    images=images,
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                    labels=labels
                )
                loss = outputs.loss / gradient_accumulation_steps
            
            scaler.scale(loss).backward()
            
            if (step + 1) % gradient_accumulation_steps == 0:
                scaler.step(optimizer)
                scaler.update()
                optimizer.zero_grad()
            
            total_loss += loss.item() * gradient_accumulation_steps
            
            progress_bar.set_postfix({"loss": f"{loss.item() * gradient_accumulation_steps:.4f}"})
        
        avg_loss = total_loss / len(dataloader)
        loss_history.append(avg_loss)
        print(f"Epoch {epoch+1} - Average Loss: {avg_loss:.4f}")
        
        if device.type == "cuda":
            print(f"GPU Memory Usage: {torch.cuda.memory_allocated(device) / 1024**3:.2f} GB / {torch.cuda.max_memory_allocated(device) / 1024**3:.2f} GB")
    
    print("Training complete!")
    return model, loss_history


if __name__ == "__main__":
    trained_model, losses = train()
    
    torch.save({
        "model_state_dict": trained_model.state_dict(),
        "loss_history": losses
    }, "../checkpoints/blip2_checkpoint.pth")
    
    print("Model saved to ../checkpoints/blip2_checkpoint.pth")