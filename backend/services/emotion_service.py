import logging
from typing import Dict, Tuple
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import textstat
import re

logger = logging.getLogger(__name__)

class EmotionAnalyzer:
    def __init__(self):
        self.analyzer = SentimentIntensityAnalyzer()
        
    def analyze_emotion(self, text: str) -> Dict[str, float]:
        """分析文本的情绪"""
        try:
            scores = self.analyzer.polarity_scores(text)
            
            # 计算情绪权重 (0-1)
            emotion_weight = abs(scores['compound'])
            
            return {
                'positive': scores['pos'],
                'negative': scores['neg'],
                'neutral': scores['neu'],
                'compound': scores['compound'],
                'emotion_weight': emotion_weight
            }
        except Exception as e:
            logger.error(f"情绪分析失败: {e}")
            return {
                'positive': 0.0,
                'negative': 0.0,
                'neutral': 1.0,
                'compound': 0.0,
                'emotion_weight': 0.0
            }

class EventClassifier:
    def __init__(self):
        self.categories = {
            'question': ['什么', '怎么', '为什么', '哪个', '如何', '?', '？'],
            'task': ['帮我', '请', '能否', '可以帮', '需要'],
            'conversation': ['你好', '再见', '谢谢', '不客气', '聊天'],
            'information': ['告诉我', '信息', '资料', '数据', '了解'],
            'creative': ['写', '创作', '设计', '想法', '创意'],
            'analysis': ['分析', '比较', '评估', '判断', '解释'],
            'emotional': ['感觉', '心情', '情绪', '开心', '难过', '担心']
        }
    
    def classify_event(self, text: str) -> Tuple[str, float]:
        """分类事件类型和置信度"""
        try:
            text_lower = text.lower()
            scores = {}
            
            for category, keywords in self.categories.items():
                score = 0
                for keyword in keywords:
                    if keyword.lower() in text_lower:
                        score += 1
                
                # 计算置信度
                if score > 0:
                    scores[category] = score / len(keywords)
            
            if not scores:
                return 'general', 0.5
            
            # 返回得分最高的类别
            best_category = max(scores.items(), key=lambda x: x[1])
            return best_category[0], min(best_category[1], 1.0)
            
        except Exception as e:
            logger.error(f"事件分类失败: {e}")
            return 'general', 0.5

    def get_complexity_score(self, text: str) -> float:
        """计算文本复杂度"""
        try:
            # 使用 Flesch Reading Ease
            reading_ease = textstat.flesch_reading_ease(text)
            # 转换为 0-1 的复杂度分数
            complexity = max(0, min(1, (100 - reading_ease) / 100))
            return complexity
        except:
            return 0.5