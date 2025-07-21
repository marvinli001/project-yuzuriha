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
        """格式化时间戳"""
        dt = datetime.fromtimestamp(timestamp, self.timezone)
        return dt.strftime("%Y-%m-%d %H:%M:%S %Z")