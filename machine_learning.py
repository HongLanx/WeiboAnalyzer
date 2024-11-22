import torch
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
from transformers import BertTokenizer, BertModel, AdamW


# 自定义数据集
class CustomDataset(Dataset):
    def __init__(self, texts, labels, tokenizer, max_len):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_len = max_len

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, index):
        text = self.texts[index]
        label = self.labels[index]

        # 编码文本
        text_encoding = self.tokenizer.encode_plus(
            text,
            add_special_tokens=True,
            max_length=self.max_len,
            return_token_type_ids=False,
            padding='max_length',
            truncation=True,
            return_attention_mask=True,
            return_tensors='pt',
        )

        # 编码标签
        label_encoding = self.tokenizer.encode_plus(
            label,
            add_special_tokens=True,
            max_length=self.max_len,
            return_token_type_ids=False,
            padding='max_length',
            truncation=True,
            return_attention_mask=True,
            return_tensors='pt',
        )

        return {
            'text': text,
            'input_ids': text_encoding['input_ids'].flatten(),
            'attention_mask': text_encoding['attention_mask'].flatten(),
            'label_input_ids': label_encoding['input_ids'].flatten(),
            'label_attention_mask': label_encoding['attention_mask'].flatten()
        }


# 定义训练函数
def train_model(model, data_loader, optimizer, device, scheduler, num_epochs):
    model = model.train()
    for epoch in range(num_epochs):
        for batch in data_loader:
            input_ids = batch['input_ids'].to(device)
            attention_mask = batch['attention_mask'].to(device)
            label_input_ids = batch['label_input_ids'].to(device)
            label_attention_mask = batch['label_attention_mask'].to(device)

            outputs = model(
                input_ids=input_ids,
                attention_mask=attention_mask
            )
            label_outputs = model(
                input_ids=label_input_ids,
                attention_mask=label_attention_mask
            )

            embeddings = outputs.last_hidden_state[:, 0, :]
            label_embeddings = label_outputs.last_hidden_state[:, 0, :]

            cosine_sim = F.cosine_similarity(embeddings, label_embeddings, dim=-1)
            loss = 1 - cosine_sim.mean()

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            scheduler.step()

        print(f'Epoch {epoch + 1}/{num_epochs}, Loss: {loss.item()}')


# 定义预测函数
def predict(model, data_loader, device, tokenizer, Y):
    model = model.eval()
    predictions = []
    with torch.no_grad():
        label_encodings = [tokenizer.encode_plus(label, add_special_tokens=True, max_length=48, padding='max_length',
                                                 return_tensors='pt') for label in Y]
        label_input_ids = torch.stack([enc['input_ids'].flatten().to(device) for enc in label_encodings])
        label_attention_mask = torch.stack([enc['attention_mask'].flatten().to(device) for enc in label_encodings])
        label_outputs = model(
            input_ids=label_input_ids,
            attention_mask=label_attention_mask
        )
        label_embeddings = label_outputs.last_hidden_state[:, 0, :]

        for batch in data_loader:
            input_ids = batch['input_ids'].to(device)
            attention_mask = batch['attention_mask'].to(device)

            outputs = model(
                input_ids=input_ids,
                attention_mask=attention_mask
            )

            embeddings = outputs.last_hidden_state[:, 0, :]
            cosine_sim = F.cosine_similarity(embeddings.unsqueeze(1), label_embeddings.unsqueeze(0), dim=-1)
            preds = torch.argmax(cosine_sim, dim=1)

            predictions.extend(preds.cpu().numpy())

    return predictions


# 保存模型函数
def save_model(model, path):
    torch.save(model.state_dict(), path)
    print(f'Model saved to {path}')


# 加载模型函数
def load_model(model, path, device):
    model.load_state_dict(torch.load(path, map_location=device))
    model = model.to(device)
    print(f'Model loaded from {path}')
    return model


# 训练函数
def training(X, Y):
    model_path = 'bert_model.pth'
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    tokenizer = BertTokenizer.from_pretrained('bert-base-chinese')
    max_len = 48

    dataset = CustomDataset(X, Y, tokenizer, max_len)
    data_loader = DataLoader(dataset, batch_size=2, shuffle=True)

    # 初始化模型
    model = BertModel.from_pretrained('bert-base-chinese')
    model = model.to(device)

    # 优化器和学习率调度器
    optimizer = AdamW(model.parameters(), lr=2e-5)
    total_steps = len(data_loader) * 3  # 假设训练3个epoch
    scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=total_steps // 3, gamma=0.1)

    # 训练模型
    train_model(model, data_loader, optimizer, device, scheduler, num_epochs=3)

    # 保存模型
    save_model(model, model_path)


# 预测函数
def prediction(X_new, Y):
    model_path = 'bert_model.pth'
    device = torch.device("cpu")
    tokenizer = BertTokenizer.from_pretrained('bert-base-chinese')
    max_len = 48

    # 初始化模型
    model = BertModel.from_pretrained('bert-base-chinese')
    model = load_model(model, model_path, device)

    new_dataset = CustomDataset(X_new, [''] * len(X_new), tokenizer, max_len)
    new_data_loader = DataLoader(new_dataset, batch_size=1, shuffle=False)

    predictions = predict(model, new_data_loader, device, tokenizer, Y)
    Y_new = [Y[pred] for pred in predictions]

    for x in X_new:
        print("输入：", x)
    for y in Y_new:
        print("预测输出：", y)
    return Y_new

