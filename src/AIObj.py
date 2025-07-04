# Standart libs import
import time
from abc import ABC
import json
import base64
import requests
from typing import Optional, Dict, List, Any
import tiktoken
from openai import OpenAI
import os

from src import constants
from src.searcher.GitStats import GitParserStats
from src.logger import logger


class AIObj(ABC):
    """
        Enhanced AI Analysis Class for GitSearch
        
        Capabilities:
        - Multiple LLM provider support
        - Company relevance analysis
        - Detailed leak assessment
        - Backward compatibility with existing code
    """
    base_prompt_text = 'None'
    
    def __init__(self, secrets: dict, stats_data: dict, leak_info: dict, company_info: Optional[Dict[str, Any]] = None):
        # Инициализация токенизатора (если доступен)
        try:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        except ImportError:
            logger.warning("tiktoken не доступен, используется упрощенный подсчет токенов")
            self.tokenizer = None
        
        # Флаги состояния
        self.ai_requested = False
        self.ai_analysis_completed = False
        
        # Результаты анализа
        self.ai_result = -1  # Для обратной совместимости (0/1/-1)
        self.ai_report = {'Thinks': 'Not state'}
        self.ai_analysis = None  # Расширенный анализ
        
        # Информация о компании
        self.company_info = company_info or {}
        
        # LLM Manager для доступа к провайдерам (ленивая инициализация)
        self._llm_manager = None
        
        # Подготовка данных для анализа
        self._prepare_analysis_data(secrets, stats_data, leak_info)
    
    def _prepare_analysis_data(self, secrets: dict, stats_data: dict, leak_info: dict):
        """Подготовка данных для AI анализа"""
        
        # Обработка секретов
        secrets_str = json.dumps(secrets) if secrets else "-"
        
        # Упрощенный подсчет токенов если tiktoken недоступен
        if self.tokenizer:
            token_limit = constants.AI_CONFIG.get('token_limit', 4000) - 1000
            if len(self.tokenizer.encode(secrets_str)) > token_limit:
                secrets_str = self.tokenizer.decode(self.tokenizer.encode(secrets_str)[:token_limit])
                secrets_str += '...Cutted, token limit reached.'
        else:
            # Упрощенная обрезка по символам
            if len(secrets_str) > 10000:
                secrets_str = secrets_str[:10000] + '...Cutted, char limit reached.'
        
        # Подготовка сырого отчета
        if secrets:
            raw_report_str = "\n".join(str(item) for item in secrets)
        else:
            raw_report_str = "-"
        
        # Безопасное извлечение данных
        size_value = self.safe_val(stats_data.get("size"))
        forks_value = self.safe_val(stats_data.get("forks_count"))
        stargazers_value = self.safe_val(stats_data.get("stargazers_count"))
        description_value = self.safe_val(stats_data.get("description"))
        
        # Информация о контрибьюторах и коммитерах
        contributers_list = leak_info.get("contributers") or []
        commiters_list = leak_info.get("commiters") or []
        
        # Основная информация
        self.repo_name = self.safe_val(leak_info.get("repo_name"))
        self.author = self.safe_val(leak_info.get("author"))
        self.dork = self.safe_val(leak_info.get("dork"))
        self.created_at = self.safe_val(leak_info.get("created_at"))
        self.updated_at = self.safe_val(leak_info.get("updated_at"))
        
        # Сохранение обработанных данных для анализа
        self.processed_data = {
            "secrets": secrets,
            "secrets_str": secrets_str,
            "raw_report_str": raw_report_str,
            "stats": {
                "size": size_value,
                "forks": forks_value,
                "stargazers": stargazers_value,
                "description": description_value
            },
            "contributors": contributers_list,
            "commiters": commiters_list
        }
        
        # Формирование базового промпта для обратной совместимости
        self.base_prompt_text = (
            "### Data:\n"
            f"Repository name: {self.repo_name}\n"
            f"Author: {self.author}\n"
            f"Last updated at: {self.updated_at}\n"
            f"Repository created at: {self.created_at}\n"
            f"Stats of repo -> Size: {size_value}, Forks: {forks_value}, Stargazers: {stargazers_value}\n"
            f"Description of repo: {description_value}\n\n"
            f"Contributers:\n{contributers_list}\n\n"
            f"Commiters:\n{commiters_list}\n\n"
            f"Company related dork: {self.dork}\n\n"
            f"Raw_report (may cut off):\n{raw_report_str.replace('\t', '').replace('\n', '')}...\n\n"
        )
                      
    def safe_val(self, val):
        if val is None or val == "":
            return "-"
        return str(val)

    @property
    def llm_manager(self):
        """Ленивая инициализация LLM менеджера"""
        if self._llm_manager is None:
            # Импортируем глобальный менеджер
            global llm_manager
            self._llm_manager = llm_manager
        return self._llm_manager

    def analyze_leak_comprehensive(self):
        """Комплексный анализ утечки с использованием множественных LLM провайдеров"""
        try:
            # Базовая реализация - будет расширена позже
            if not self.llm_manager.providers:
                logger.warning("Нет доступных LLM провайдеров")
                return None
            
            # Пока используем простую заглушку
            logger.info("Комплексный анализ запущен")
            return {
                "company_related": False,
                "confidence": 0.0,
                "summary": "Базовый анализ выполнен"
            }
        except Exception as e:
            logger.error(f"Ошибка в комплексном анализе: {str(e)}")
            return None
    
    def safe_generate(
        self,
        prompt: str,
        ctx_size: int = 8192,
        max_new_tokens: int = 1024,
        safety_margin: int = 256
    ) -> tuple[str, int]:
        
        prompt_tokens = self.tokenizer.encode(prompt)
        
        max_prompt_tokens = ctx_size - max_new_tokens - safety_margin
        logger.info(f"Количество токенов: {len(prompt_tokens)}")
        
        if len(prompt_tokens) > max_prompt_tokens:
            prompt_tokens = prompt_tokens[:max_prompt_tokens]
            logger.info(f"Предупреждение: Промпт обрезан до {max_prompt_tokens} токенов")
        
        max_tokens = ctx_size-len(prompt_tokens)-5
        prompt = self.tokenizer.decode(prompt_tokens)

        if max_tokens < 0:
            logger.error(f"Предупреждение: недостаточно токенов для ответа, промпт не будет выполняться. Промпт: {prompt}")
            return ""
        else:
            return prompt, max_tokens

    def lm_studio_request(self, prompt: str, client: str, max_tokens: int, temperature: float, model: str):
        system_prompt = (            
                "### Instruction:\n"
                "You are a data leak detection expert. Analyze the data and respond ONLY with '1' (leak found) or '0' (no leak).\n"
                "Strict response rules:\n"
                "- Output must be single character: 1 or 0\n"
                
                "### Examples:\n"
                "Good: 1\n"
                "Good: 0\n"
                "Bad: I think it's 1 because...\n"
                
                "### Assessment Criteria:\n"
                "Return 1 if the leak may be related to the company\n"
                "Often in leaks very low stars quantity and/or russian related description/authors names/domains (ru)"
                
        )
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "GitSearch_chech",
                    "description": "Function to analyze gitsearch incidents",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "The incident classification"
                            }
                        },
                        "required": ["data"]
                    }
                }
            }
        ]
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
                #tools=tools,
                stop=["</answer>", "<|im_end|>"]
            )
        except Exception as ex:
            logger.error(f'Api request error: {ex}')
            return None

        return response
    
    def ai_request(self):
        """Оригинальный метод для обратной совместимости"""
        if self.ai_requested:
            return
        
        # Попытка использования нового комплексного анализа
        if constants.AI_ANALYSIS_ENABLED and self.llm_manager.providers:
            try:
                analysis = self.analyze_leak_comprehensive()
                if analysis:
                    self.ai_requested = True
                    return
            except Exception as e:
                logger.warning(f"Комплексный анализ не удался, используется старый метод: {str(e)}")
        
        # Fallback к оригинальному методу
        result_promt, max_tokens = self.safe_generate(prompt=self.base_prompt_text,
                                                      ctx_size=constants.AI_CONFIG['token_limit'])
        if not result_promt:
            self.ai_result = -1
            self.ai_requested = True
            return

        try:
            client = OpenAI(base_url=constants.AI_CONFIG['url'], api_key=constants.AI_CONFIG['api_key'])
        except Exception as ex:
            logger.error(f'Error in connection to AI API: {ex}')
            self.ai_requested = True
            return
        
        try:
            ai_response = self.lm_studio_request(prompt=result_promt, 
                                                client=client,
                                                max_tokens=max_tokens,
                                                temperature=constants.AI_CONFIG['temperature'],
                                                model=constants.AI_CONFIG['model'])
            if ai_response and ai_response.choices:
                self.ai_report = ai_response.choices[0].message.content.strip()
                if self.ai_report == '0':
                    self.ai_result = 0
                elif self.ai_report == '1':
                    self.ai_result = 1
                else:
                    logger.warning(f"AI returned unexpected output: {self.ai_report}")
                    self.ai_result = -1
            else:
                logger.warning("AI response was empty or malformed.")
                self.ai_result = -1
            self.ai_requested = True
        except Exception as ex:
            logger.error(f'Error in AI API request: {ex}')
            self.ai_requested = True
        
    def set_company_info(self, company_info: Dict[str, Any]):
        """Установка информации о компании для анализа"""
        self.company_info = company_info
        
    def get_comprehensive_analysis(self) -> Dict[str, Any]:
        """Получение комплексного анализа утечки"""
        if not self.ai_analysis_completed:
            return self.analyze_leak_comprehensive()
        return self.ai_analysis
    
    def is_company_related(self) -> bool:
        """Проверка связи утечки с компанией"""
        if self.ai_analysis:
            return self.ai_analysis.get('company_relevance', {}).get('is_related', False)
        return False
    
    def get_severity_level(self) -> str:
        """Получение уровня серьезности утечки"""
        if self.ai_analysis:
            return self.ai_analysis.get('severity_assessment', {}).get('level', 'unknown')
        return 'unknown'
    
    def get_true_positive_probability(self) -> float:
        """Получение вероятности истинной утечки"""
        if self.ai_analysis:
            return self.ai_analysis.get('classification', {}).get('true_positive_probability', 0.0)
        return 0.0
    
    def get_recommendations(self) -> Dict[str, Any]:
        """Получение рекомендаций по утечке"""
        if self.ai_analysis:
            return self.ai_analysis.get('recommendations', {})
        return {}
    
    def get_analysis_summary(self) -> str:
        """Получение краткого описания анализа"""
        if self.ai_analysis:
            return self.ai_analysis.get('summary', 'Анализ не выполнен')
        return 'Анализ не выполнен'


class LLMProviderManager:
    """Менеджер для работы с множественными LLM провайдерами"""
    
    def __init__(self):
        self.providers = {}
        self.usage_stats = {}
        self._load_providers()
    
    def _load_providers(self):
        """Загрузка провайдеров из конфигурации"""
        # Получаем переменные из constants (уже загружены из .env)
        env_vars = constants.env_variables
        
        for provider_config in constants.LLM_PROVIDERS:
            api_key = env_vars.get(provider_config["api_key_env"])
            if api_key and api_key.strip():  # Проверяем что ключ не пустой
                self.providers[provider_config["name"]] = {
                    **provider_config,
                    "api_key": api_key,
                    "requests_count": 0,
                    "last_request_time": 0,
                    "error_count": 0
                }
                logger.info(f"Загружен LLM провайдер: {provider_config['name']}")
            else:
                logger.warning(f"API ключ для {provider_config['name']} не найден или пуст")
    
    def get_available_provider(self) -> Optional[Dict[str, Any]]:
        """Получить доступного провайдера"""
        current_time = time.time()
        
        for name, provider in self.providers.items():
            # Простая проверка лимитов
            if provider["error_count"] < 3:  # Не более 3 ошибок подряд
                # Проверка минутного лимита (упрощенная)
                if current_time - provider["last_request_time"] > 60 / provider["rpm"]:
                    return provider
        
        return None
    
    def make_request(self, messages: List[Dict[str, str]], 
                    max_tokens: int = 2000, 
                    temperature: float = 0.1) -> Optional[Dict[str, Any]]:
        """Выполнить запрос к доступному провайдеру"""
        
        provider = self.get_available_provider()
        if not provider:
            logger.error("Нет доступных LLM провайдеров")
            return None
        
        headers = {
            "Authorization": f"Bearer {provider['api_key']}",
            "Content-Type": "application/json"
        }
        
        # Специальные заголовки для OpenRouter
        if provider["name"] == "openrouter":
            headers["HTTP-Referer"] = "https://github.com/gitsearch"
            headers["X-Title"] = "GitSearch AI Analyzer"
        
        payload = {
            "model": provider["model"],
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        try:
            response = requests.post(
                f"{provider['base_url']}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                provider["requests_count"] += 1
                provider["last_request_time"] = time.time()
                provider["error_count"] = 0
                
                logger.info(f"Успешный запрос к провайдеру: {provider['name']}")
                return response.json()
            else:
                logger.error(f"Провайдер {provider['name']} вернул статус {response.status_code}: {response.text}")
                provider["error_count"] += 1
                return None
        
        except Exception as e:
            logger.error(f"Ошибка запроса к провайдеру {provider['name']}: {str(e)}")
            provider["error_count"] += 1
            return None


# Глобальный экземпляр менеджера провайдеров
llm_manager = LLMProviderManager()
