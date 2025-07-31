# Cloudflare D1 数据库设置指南

## 概述

本文档将指导您如何在 Cloudflare 中创建和配置 D1 数据库，用于 Project Yuzuriha 的聊天历史结构化存储。

## 前提条件

- Cloudflare 账户
- Cloudflare API Token（具有 D1 权限）
- Node.js 和 npm（用于 Wrangler CLI）

## 步骤 1: 安装 Wrangler CLI

Wrangler 是 Cloudflare 的官方 CLI 工具，用于管理 D1 数据库。

```bash
npm install -g wrangler
```

验证安装：
```bash
wrangler --version
```

## 步骤 2: 登录 Cloudflare

```bash
wrangler login
```

这将打开浏览器，要求您登录 Cloudflare 账户。

## 步骤 3: 创建 D1 数据库

```bash
wrangler d1 create yuzuriha_chat_db
```

命令执行成功后，您会看到类似输出：

```
✅ Successfully created DB 'yuzuriha_chat_db' in region APAC
Created your database using D1's new storage backend. The new storage backend is not yet recommended for production workloads, but backs up your data via point-in-time restore.

[[d1_databases]]
binding = "DB" # i.e. available in your Worker on env.DB
database_name = "yuzuriha_chat_db"
database_id = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
```

**重要：** 记下 `database_id`，您稍后需要用到它。

## 步骤 4: 获取账户 ID

```bash
wrangler whoami
```

输出中的 `Account ID` 就是您的 Cloudflare 账户 ID。

## 步骤 5: 创建数据库表

创建一个 SQL 文件来定义表结构：

```bash
cat > schema.sql << 'EOF'
-- 聊天会话表
CREATE TABLE chat_sessions (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);

-- 聊天消息表  
CREATE TABLE chat_messages (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
  content TEXT NOT NULL,
  timestamp INTEGER NOT NULL,
  FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
);

-- 创建索引
CREATE INDEX idx_chat_messages_session_id ON chat_messages(session_id);
CREATE INDEX idx_chat_sessions_updated_at ON chat_sessions(updated_at);
CREATE INDEX idx_chat_messages_timestamp ON chat_messages(timestamp);
EOF
```

执行 SQL 文件创建表：

```bash
wrangler d1 execute yuzuriha_chat_db --file=schema.sql
```

## 步骤 6: 获取 API Token

1. 访问 [Cloudflare Dashboard](https://dash.cloudflare.com/)
2. 点击右上角的用户图标，选择 "My Profile"
3. 转到 "API Tokens" 标签
4. 点击 "Create Token"
5. 选择 "Custom token"
6. 配置权限：
   - **Account**: Cloudflare D1:Edit
   - **Zone Resources**: Include - All zones（如果您需要）
7. 点击 "Continue to summary"
8. 点击 "Create Token"
9. 复制生成的 token（只显示一次）

## 步骤 7: 配置环境变量

在 `backend/.env` 文件中添加以下配置：

```env
# Cloudflare D1 配置
CLOUDFLARE_ACCOUNT_ID=your_account_id_here
CLOUDFLARE_D1_DATABASE_ID=your_database_id_here
CLOUDFLARE_API_TOKEN=your_api_token_here
CLOUDFLARE_D1_DATABASE_NAME=yuzuriha_chat_db
```

替换实际值：
- `CLOUDFLARE_ACCOUNT_ID`: 从步骤 4 获取的账户 ID
- `CLOUDFLARE_D1_DATABASE_ID`: 从步骤 3 获取的数据库 ID
- `CLOUDFLARE_API_TOKEN`: 从步骤 6 获取的 API Token
- `CLOUDFLARE_D1_DATABASE_NAME`: 数据库名称（应该是 `yuzuriha_chat_db`）

## 步骤 8: 验证配置

启动后端服务：

```bash
cd backend
python main.py
```

访问健康检查端点：

```bash
curl http://localhost:8000/health
```

在响应中，`services.d1_service` 应该为 `true`。

您也可以检查 D1 统计信息：

```bash
curl -H "Authorization: Bearer your_api_key" http://localhost:8000/api/chat/stats
```

## 步骤 9: 测试 D1 功能

### 创建聊天会话

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_api_key" \
  -d '{"title": "测试会话"}' \
  http://localhost:8000/api/chat/sessions
```

### 添加消息

使用上一步返回的 session_id：

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_api_key" \
  -d '{"role": "user", "content": "你好"}' \
  http://localhost:8000/api/chat/sessions/{session_id}/messages
```

### 获取会话列表

```bash
curl -H "Authorization: Bearer your_api_key" \
  http://localhost:8000/api/chat/sessions
```

## 高级配置

### 数据库备份

D1 支持自动备份。您可以通过 Wrangler CLI 手动创建备份：

```bash
wrangler d1 backup create yuzuriha_chat_db
```

### 查看数据库内容

```bash
wrangler d1 execute yuzuriha_chat_db --command="SELECT * FROM chat_sessions LIMIT 10;"
```

### 导出数据

```bash
wrangler d1 export yuzuriha_chat_db --output=backup.sql
```

### 生产环境注意事项

1. **API Token 安全**: 确保 API Token 安全存储，不要提交到版本控制系统
2. **访问控制**: 考虑为不同环境（开发、测试、生产）创建不同的 Token
3. **监控**: 监控 D1 的使用情况和错误率
4. **备份策略**: 设置定期备份计划

## 故障排除

### 常见错误

1. **"D1 服务不可用"**
   - 检查环境变量是否正确设置
   - 验证 API Token 权限
   - 确认数据库 ID 正确

2. **"Authentication failed"**
   - 检查 API Token 是否有效
   - 确认 Token 具有 D1 权限
   - 检查账户 ID 是否正确

3. **"Database not found"**
   - 确认数据库 ID 正确
   - 检查数据库是否在正确的账户下

### 调试命令

检查数据库状态：
```bash
wrangler d1 info yuzuriha_chat_db
```

列出所有 D1 数据库：
```bash
wrangler d1 list
```

查看数据库表结构：
```bash
wrangler d1 execute yuzuriha_chat_db --command=".schema"
```

## 成本考虑

Cloudflare D1 的定价（截至文档编写时）：

- **免费套餐**: 每天 100,000 次读取、1,000 次写入
- **付费套餐**: 超出后按使用量计费

对于个人使用或小型项目，免费套餐通常足够。

## 支持和文档

- [Cloudflare D1 官方文档](https://developers.cloudflare.com/d1/)
- [Wrangler CLI 文档](https://developers.cloudflare.com/workers/wrangler/)
- [D1 API 参考](https://developers.cloudflare.com/api/operations/cloudflare-d1-list-databases)

## 总结

完成以上步骤后，您的 Project Yuzuriha 应用就可以使用 Cloudflare D1 进行聊天历史的云端存储了。系统将自动实现双写机制，同时将数据存储到 Milvus（用于向量搜索）和 D1（用于结构化查询）。