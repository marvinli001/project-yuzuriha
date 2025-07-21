import os
import pytz
from datetime import datetime
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class TimeService:
    def __init__(self):
        timezone_name = os.getenv('TIMEZONE', 'UTC')
        try:
            self.timezone = pytz.timezone(timezone_name)
        except pytz.exceptions.UnknownTimeZoneError:
            logger.warning(f"未知时区 {timezone_name}，使用 UTC")
            self.timezone = pytz.UTC
    
    def get_current_time(self) -> datetime:
        """获取当前时间"""
        return datetime.now(self.timezone)
    
    def get_formatted_time(self) -> str:
        """获取格式化的当前时间"""
        current_time = self.get_current_time()
        return current_time.strftime("%Y-%m-%d %H:%M:%S %Z")
    
    def get_time_context(self) -> Dict[str, Any]:
        """获取时间上下文信息"""
        current_time = self.get_current_time()
        
        return {
            'current_time': current_time.strftime("%Y-%m-%d %H:%M:%S %Z"),
            'date': current_time.strftime("%Y-%m-%d"),
            'time': current_time.strftime("%H:%M:%S"),
            'timezone': str(self.timezone),
            'weekday': current_time.strftime("%A"),
            'month': current_time.strftime("%B"),
            'year': current_time.year,
            'hour': current_time.hour,
            'timestamp': int(current_time.timestamp())
        }
    
    def format_timestamp(self, timestamp: int) -> str:
        """安全地格式化时间戳"""
        try:
            # 验证时间戳的有效性
            if not isinstance(timestamp, (int, float)):
                logger.warning(f"时间戳类型无效: {type(timestamp)}, 值: {timestamp}")
                return "时间格式错误"
            
            if timestamp <= 0:
                logger.warning(f"时间戳值无效: {timestamp}")
                return "时间未知"
            
            # 检查是否为毫秒时间戳
            if timestamp > 1e10:
                timestamp = timestamp / 1000
            
            # 验证时间戳范围（1970-2100年）
            if timestamp < 0 or timestamp > 4102444800:
                logger.warning(f"时间戳超出合理范围: {timestamp}")
                return "时间超出范围"
            
            # 尝试转换时间戳
            dt = datetime.fromtimestamp(timestamp, self.timezone)
            return dt.strftime("%Y-%m-%d %H:%M:%S %Z")
            
        except (ValueError, OSError, OverflowError) as e:
            logger.warning(f"格式化时间戳失败: {e}, 时间戳: {timestamp}")
            return "时间格式错误"
        except Exception as e:
            logger.error(f"格式化时间戳时发生未知错误: {e}, 时间戳: {timestamp}")
            return "时间处理错误"
    
    def validate_timestamp(self, timestamp: int) -> bool:
        """验证时间戳是否有效"""
        try:
            if not isinstance(timestamp, (int, float)):
                return False
            
            if timestamp <= 0:
                return False
            
            # 检查是否为毫秒时间戳
            if timestamp > 1e10:
                timestamp = timestamp / 1000
            
            # 验证范围（1970-2100年）
            if timestamp < 0 or timestamp > 4102444800:
                return False
            
            # 尝试创建 datetime 对象
            datetime.fromtimestamp(timestamp, self.timezone)
            return True
            
        except Exception:
            return False