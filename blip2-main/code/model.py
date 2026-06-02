import torch
import torch.nn as nn
from transformers import CLIPVisionModel, CLIPImageProcessor, AutoModelForCausalLM, AutoTokenizer


class MiniQFormer(nn.Module):
    def __init__(self, vision_dim=768, qformer_hidden_dim=768, num_queries=32, num_layers=4):
        super().__init__()
        
        self.num_queries = num_queries
        self.queries = nn.Parameter(torch.randn(1, num_queries, qformer_hidden_dim))
        
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=qformer_hidden_dim,
            nhead=8,
            dim_feedforward=qformer_hidden_dim * 4,
            dropout=0.1,
            batch_first=True
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        
        self.vision_proj = nn.Linear(vision_dim, qformer_hidden_dim)
    
    def forward(self, vision_embeds):
        batch_size = vision_embeds.shape[0]
        
        vision_embeds = self.vision_proj(vision_embeds)
        
        queries = self.queries.repeat(batch_size, 1, 1)
        
        combined = torch.cat([queries, vision_embeds], dim=1)
        output = self.transformer(combined)
        
        query_output = output[:, :self.num_queries, :]
        return query_output


class MiniBLIP2(nn.Module):
    def __init__(
        self,
        vision_model_name="openai/clip-vit-base-patch32",
        llm_model_name="facebook/opt-125m",
        num_queries=32,
        qformer_layers=4,
        freeze_vision=True,
        freeze_llm=True
    ):
        super().__init__()
        
        self.vision_model = CLIPVisionModel.from_pretrained(vision_model_name)
        self.image_processor = CLIPImageProcessor.from_pretrained(vision_model_name)
        
        vision_dim = self.vision_model.config.hidden_size
        
        self.qformer = MiniQFormer(
            vision_dim=vision_dim,
            qformer_hidden_dim=vision_dim,
            num_queries=num_queries,
            num_layers=qformer_layers
        )
        
        self.llm = AutoModelForCausalLM.from_pretrained(llm_model_name)
        self.tokenizer = AutoTokenizer.from_pretrained(llm_model_name)
        
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        
        llm_dim = self.llm.config.hidden_size
        self.projection = nn.Linear(vision_dim, llm_dim)
        
        if freeze_vision:
            for param in self.vision_model.parameters():
                param.requires_grad = False
        
        if freeze_llm:
            for param in self.llm.parameters():
                param.requires_grad = False
    
    def get_vision_embeds(self, images):
        outputs = self.vision_model(pixel_values=images)
        return outputs.last_hidden_state.float()
    
    def forward(self, images, input_ids, attention_mask=None, labels=None):
        vision_embeds = self.get_vision_embeds(images)
        
        query_output = self.qformer(vision_embeds)
        
        projected_queries = self.projection(query_output).float()
        
        inputs_embeds = self.llm.get_input_embeddings()(input_ids).float()
        
        combined_embeds = torch.cat([projected_queries, inputs_embeds], dim=1)
        
        if attention_mask is not None:
            query_attention_mask = torch.ones(
                attention_mask.shape[0], 
                projected_queries.shape[1],
                dtype=attention_mask.dtype,
                device=attention_mask.device
            )
            combined_attention_mask = torch.cat([query_attention_mask, attention_mask], dim=1)
        else:
            combined_attention_mask = None
        
        if labels is not None:
            query_labels = torch.full(
                (labels.shape[0], projected_queries.shape[1]),
                -100,
                dtype=labels.dtype,
                device=labels.device
            )
            combined_labels = torch.cat([query_labels, labels], dim=1)
        else:
            combined_labels = None
        
        outputs = self.llm(
            inputs_embeds=combined_embeds,
            attention_mask=combined_attention_mask,
            labels=combined_labels,
            return_dict=True
        )
        
        return outputs
    
    @torch.no_grad()
    def generate(self, images, max_length=50, temperature=0.7, top_k=50, top_p=0.9):
        self.eval()
        
        vision_embeds = self.get_vision_embeds(images)
        query_output = self.qformer(vision_embeds)
        projected_queries = self.projection(query_output).float()
        
        batch_size = images.shape[0]
        device = images.device
        
        input_ids = torch.full(
            (batch_size, 1),
            self.tokenizer.bos_token_id if self.tokenizer.bos_token_id is not None else self.tokenizer.eos_token_id,
            dtype=torch.long,
            device=device
        )
        
        generated = input_ids
        
        for _ in range(max_length):
            inputs_embeds = self.llm.get_input_embeddings()(generated).float()
            combined_embeds = torch.cat([projected_queries, inputs_embeds], dim=1)
            
            outputs = self.llm(inputs_embeds=combined_embeds)
            logits = outputs.logits
            
            next_token_logits = logits[:, -1, :] / temperature
            
            if top_k is not None:
                next_token_logits = self.top_k_logits(next_token_logits, top_k)
            
            if top_p is not None:
                next_token_logits = self.top_p_logits(next_token_logits, top_p)
            
            probs = torch.nn.functional.softmax(next_token_logits, dim=-1)
            next_token = torch.multinomial(probs, num_samples=1)
            
            generated = torch.cat([generated, next_token], dim=1)
            
            if (next_token == self.tokenizer.eos_token_id).all():
                break
        
        captions = []
        for seq in generated:
            caption = self.tokenizer.decode(seq, skip_special_tokens=True)
            captions.append(caption.strip())
        
        return captions
    
    def top_k_logits(self, logits, k):
        v, ix = torch.topk(logits, k)
        out = logits.clone()
        out[out < v[:, [-1]]] = float('-inf')
        return out
    
    def top_p_logits(self, logits, p):
        sorted_logits, sorted_indices = torch.sort(logits, descending=True)
        cumulative_probs = torch.cumsum(torch.nn.functional.softmax(sorted_logits, dim=-1), dim=-1)
        
        sorted_indices_to_remove = cumulative_probs > p
        sorted_indices_to_remove[..., 1:] = sorted_indices_to_remove[..., :-1].clone()
        sorted_indices_to_remove[..., 0] = 0
        
        indices_to_remove = sorted_indices[sorted_indices_to_remove]
        logits[:, indices_to_remove] = float('-inf')
        return logits
