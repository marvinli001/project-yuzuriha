// 创建API客户端配置
const API_SECRET_KEY = process.env.NEXT_PUBLIC_API_SECRET_KEY || 'your_secret_api_key_here_please_change_this_to_a_strong_random_string';

export const apiClient = {
  headers: {
    'Authorization': `Bearer ${API_SECRET_KEY}`,
    'Content-Type': 'application/json',
  }
};