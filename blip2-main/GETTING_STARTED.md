# Mini-BLIP2 复现项目

## 项目结构

```
blip2-main/
├── code/
│   ├── __init__.py
│   ├── dataset.py      # 数据集加载模块
│   ├── model.py        # Mini-BLIP2 模型
│   ├── train.py        # 训练脚本
│   └── generate.py     # 生成/测试脚本
├── data/
│   ├── Images/         # 图片文件夹
│   └── captions.txt    # 标注文件
├── checkpoints/        # 模型保存文件夹
├── requirements.txt    # 依赖包列表
└── README.md
```

## 使用步骤

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 训练模型

```bash
cd code
python train.py
```

训练参数可在 `train.py` 中修改：
- `batch_size`: 批次大小（默认 4）
- `num_epochs`: 训练轮数（默认 10）
- `lr`: 学习率（默认 1e-4）
- `num_images`: 使用图片数量（默认 200）

### 3. 生成/测试模型

```bash
cd code
python generate.py
```

## 模型架构

1. **视觉编码器**: `openai/clip-vit-base-patch32`（冻结）
2. **Mini Q-Former**: 可训练的 Transformer，含 32 个可学习 queries
3. **Projection Layer**: 将视觉特征对齐到语言模型维度
4. **语言解码器**: `facebook/opt-125m`（冻结）

## 训练的模块

- Mini Q-Former
- Projection Layer

## 冻结的模块

- CLIP Vision Encoder
- OPT Language Model
