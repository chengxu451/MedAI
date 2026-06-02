# Mini-BLIP2 图像描述生成复现实验报告

## 1. 论文信息

- 论文名称：BLIP-2: Bootstrapping Language-Image Pre-training with Frozen Image Encoders and Large Language Models
- 论文地址：https://arxiv.org/abs/2301.12597

## 2. 任务说明

本实验复现的任务是图像描述生成 Image Captioning。

输入：图片  
输出：英文 caption

## 3. 数据集

- 数据集名称：Flickr8k
- 数据集地址：https://www.kaggle.com/datasets/adityajn105/flickr8k
- 实际使用数据量：前 200 张图片（共 1000 条标注，每张图片 5 条 caption）

## 4. 模型结构

```text
Image → Frozen Vision Encoder → Mini Q-Former → Projection Layer → Frozen Language Decoder → Caption
```

### 4.1 Vision Encoder

- 模型：`openai/clip-vit-base-patch32`
- 状态：冻结（不参与训练）
- 输出维度：768

### 4.2 Mini Q-Former

- query token 数量：32
- hidden size：768（与 vision encoder 输出维度一致）
- Transformer 层数：4
- 是否使用 cross-attention：否（使用 self-attention，将 query tokens 和 vision embeddings 拼接后一起输入 TransformerEncoder）

### 4.3 Language Decoder

- 模型：`facebook/opt-125m`
- 状态：冻结（不参与训练）
- 隐藏层维度：768

## 5. 训练设置

- 训练数据量：200 张图片（1000 条标注）
- epoch：10
- batch size：4
- learning rate：1e-4
- optimizer：AdamW
- loss function：CrossEntropyLoss（由 OPT 模型内部计算）
- 冻结的模块：Vision Encoder（CLIP ViT-B/32）、Language Decoder（OPT-125M）
- 训练的模块：Mini Q-Former、Projection Layer

## 6. 训练过程

训练设备：CPU

训练日志：

| Epoch | Train Loss |
|---|---:|
| 1 | 3.6540 |
| 2 | 3.1704 |
| 3 | 2.9427 |
| 4 | 2.8036 |
| 5 | 2.6322 |
| 6 | 2.4491 |
| 7 | 2.3007 |
| 8 | 2.1738 |
| 9 | 2.0555 |
| 10 | 1.9459 |

Loss 从 3.6540 持续下降到 1.9459，模型在训练过程中稳步收敛。

## 7. 生成结果展示

生成参数：temperature=0.7, top_k=50, top_p=0.9

| 图片 | 真实 Caption（示例） | 模型生成 Caption |
|---|---|---|
| 1000268201_693b08cb0e.jpg | A child in a pink dress is climbing up a set of stairs in an entry way. | So we got to make it so they have their relationship with them. I think it's not the most. |
| 1001773457_577c3a7d70.jpg | A black dog and a spotted dog are fighting. | I don't know how to understand? So many other stuff. This is what's his character in my favorite time. |
| 1002674143_1b742ab4b8.jpg | A little girl covered in paint sits in front of a painted rainbow with her hands in a bowl. | If I think that it's to get a lot. This is what makes the best and the like. |
| 1003163366_44323f5815.jpg | A man lays on a bench while his dog sits by him. | Lolababoooo? |
| 1007129816_e794419615.jpg | A man in an orange hat starring at something. | The following episode. |

可视化结果保存在 `visualizations/` 目录下。

## 8. 总结

- **是否成功跑通训练**：是，成功完成了 10 轮训练，Loss 从 3.65 下降到 1.95，模型收敛趋势明显。
- **生成效果如何**：生成的 caption 质量有限，部分生成结果与图片内容关联较弱，出现了一些无意义或重复的文本。这主要是因为训练数据量较少（仅 200 张图片）且训练轮数有限。
- **遇到的问题**：
  1. 数据类型不匹配问题（mixed dtype error）：CLIP 和 OPT 模型在 CPU 上运行时出现 float16/float32 混合类型错误，通过在模型加载时强制指定 `torch_dtype=torch.float32` 并在 forward 中显式转换解决。
  2. 生成重复文本问题：初始使用贪心搜索（argmax）导致生成大量重复内容，后改用 top-k + top-p 采样策略改善。
  3. 虚拟环境配置问题：VS Code 默认使用系统 Python 而非虚拟环境，需要手动切换解释器。
- **改进方向**：
  1. 增加训练数据量（使用完整 Flickr8k 或更大数据集）
  2. 增加训练轮数
  3. 使用 GPU 加速训练
  4. 尝试解冻部分 LLM 层进行微调
  5. 优化生成策略（如 beam search）

## 9. AI 对话过程记录

- 录制工具：（待填写）
- 对话链接：（待填写）
- 使用的 AI 模型：（待填写）
- 累计对话时长 / 会话数：（待填写）

AI 在以下环节提供了帮助：搭建项目结构、实现 Mini-BLIP2 模型架构、编写训练和生成脚本、解决数据类型不匹配的 Bug、优化生成策略（从贪心搜索改为 top-k/top-p 采样）、创建可视化脚本。部分实现细节（如 Q-Former 的 self-attention 设计）根据论文理解独立完成。

## 10. Git 提交记录

- 仓库地址：（待填写）
- 总 commit 数：（待填写）

```text
（待填写 git log --oneline 输出）
```
