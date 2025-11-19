"""Enhanced FastAPI server with safety and monitoring features"""

from contextlib import asynccontextmanager
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from pydantic import BaseModel, Field

from medical_chatbot.inference.generator import MedicalChatGenerator
from medical_chatbot.models.model_manager import ModelManager
from medical_chatbot.utils.config import Config
from medical_chatbot.utils.safety import MedicalSafetyFilter
from medical_chatbot.utils.monitoring import RequestTimer, get_health_status, metrics_collector
from medical_chatbot.utils.error_handler import register_error_handlers, async_handle_errors
from medical_chatbot.utils.exceptions import (
    ModelNotLoadedException,
    ModelInferenceException,
    UnsafeContentException,
)


# Global variables
model_manager: Optional[ModelManager] = None
generator: Optional[MedicalChatGenerator] = None
config: Optional[Config] = None
safety_filter: Optional[MedicalSafetyFilter] = None


class ChatRequest(BaseModel):
    """Chat request model"""

    message: str = Field(..., description="User's message/question")
    system_prompt: Optional[str] = Field(None, description="Optional system prompt override")
    max_new_tokens: Optional[int] = Field(None, description="Maximum tokens to generate")
    temperature: Optional[float] = Field(None, description="Sampling temperature")
    top_p: Optional[float] = Field(None, description="Nucleus sampling parameter")
    top_k: Optional[int] = Field(None, description="Top-k sampling parameter")


class ChatResponse(BaseModel):
    """Chat response model"""

    response: str = Field(..., description="Generated response")
    message: str = Field(..., description="Original user message")
    is_emergency: Optional[bool] = Field(False, description="Whether emergency was detected")


class ConversationRequest(BaseModel):
    """Conversation request model"""

    messages: List[Dict[str, str]] = Field(
        ..., description="List of messages with 'role' and 'content'"
    )
    max_new_tokens: Optional[int] = Field(None, description="Maximum tokens to generate")
    temperature: Optional[float] = Field(None, description="Sampling temperature")


class HealthResponse(BaseModel):
    """Health check response"""

    status: str = Field(..., description="Service status")
    model_loaded: bool = Field(..., description="Whether model is loaded")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events"""
    global model_manager, generator, config, safety_filter

    logger.info("Loading model on startup...")

    try:
        # Initialize safety filter
        safety_filter = MedicalSafetyFilter(add_disclaimer=True, detect_emergency=True)

        # Load model
        tokenizer, model = model_manager.load(load_peft=True)

        # Create generator
        generator = MedicalChatGenerator(
            model=model,
            tokenizer=tokenizer,
            system_prompt=config.prompts.system,
            max_new_tokens=config.inference.max_new_tokens,
            temperature=config.inference.temperature,
            top_p=config.inference.top_p,
            top_k=config.inference.top_k,
            repetition_penalty=config.inference.repetition_penalty,
            do_sample=config.inference.do_sample,
        )

        logger.info("Model loaded successfully")

    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down...")
    if model_manager:
        model_manager.unload()


def create_app(app_config: Config) -> FastAPI:
    """Create enhanced FastAPI application"""
    global model_manager, config

    config = app_config
    model_manager = ModelManager(
        model_name=config.model.base_model,
        peft_name=config.model.fine_tuned_model,
        torch_dtype=config.model.torch_dtype,
        device_map=config.model.device_map,
        use_fast_tokenizer=config.model.use_fast_tokenizer,
        token=config.hf_token,
    )

    app = FastAPI(
        title="Medical Chatbot API",
        description="Enhanced Medical Chatbot with Safety Features",
        version="0.2.0",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/")
    async def root():
        """Root endpoint"""
        return {
            "name": "Medical Chatbot API",
            "version": "0.2.0",
            "description": "Enhanced Medical Chatbot with Safety Features",
        }

    @app.get("/health", response_model=HealthResponse)
    async def health():
        """Basic health check"""
        return HealthResponse(
            status="healthy" if generator is not None else "unhealthy",
            model_loaded=generator is not None,
        )

    @app.get("/health/detailed")
    async def health_detailed():
        """Detailed health check with metrics"""
        health_status = get_health_status()
        health_status["model_loaded"] = generator is not None
        return health_status

    @app.get("/metrics")
    async def metrics():
        """Get service metrics"""
        return metrics_collector.get_metrics()

    @app.post("/chat", response_model=ChatResponse)
    async def chat(request: ChatRequest):
        """Enhanced chat endpoint with safety features"""
        if generator is None:
            raise ModelNotLoadedException("生成器未初始化，請稍後再試")

        with RequestTimer("chat"):
            try:
                # Sanitize input
                sanitized_message = safety_filter.sanitize_input(request.message)

                # Build generation kwargs
                gen_kwargs = {}
                if request.max_new_tokens is not None:
                    gen_kwargs["max_new_tokens"] = request.max_new_tokens
                if request.temperature is not None:
                    gen_kwargs["temperature"] = request.temperature
                if request.top_p is not None:
                    gen_kwargs["top_p"] = request.top_p
                if request.top_k is not None:
                    gen_kwargs["top_k"] = request.top_k

                # Generate response
                response = generator.generate(
                    user_input=sanitized_message,
                    system_prompt=request.system_prompt,
                    **gen_kwargs,
                )

                # Apply safety filter
                filtered_response, is_emergency = safety_filter.filter_response(
                    sanitized_message, response
                )

                if is_emergency:
                    logger.warning(f"Emergency detected: {sanitized_message[:100]}")

                return ChatResponse(
                    response=filtered_response,
                    message=request.message,
                    is_emergency=is_emergency,
                )

            except Exception as e:
                logger.error(f"Generation failed: {e}")
                raise ModelInferenceException(
                    f"生成回應失敗: {str(e)}",
                    details={"original_error": type(e).__name__}
                )

    @app.post("/conversation", response_model=ChatResponse)
    async def conversation(request: ConversationRequest):
        """Multi-turn conversation endpoint"""
        if generator is None:
            raise ModelNotLoadedException("生成器未初始化，請稍後再試")

        with RequestTimer("conversation"):
            try:
                # Build generation kwargs
                gen_kwargs = {}
                if request.max_new_tokens is not None:
                    gen_kwargs["max_new_tokens"] = request.max_new_tokens
                if request.temperature is not None:
                    gen_kwargs["temperature"] = request.temperature

                # Generate response
                response = generator.chat(messages=request.messages, **gen_kwargs)

                # Get last user message
                last_user_message = ""
                for msg in reversed(request.messages):
                    if msg.get("role") == "user":
                        last_user_message = msg.get("content", "")
                        break

                # Apply safety filter
                filtered_response, is_emergency = safety_filter.filter_response(
                    last_user_message, response
                )

                return ChatResponse(
                    response=filtered_response,
                    message=last_user_message,
                    is_emergency=is_emergency,
                )

            except Exception as e:
                logger.error(f"Generation failed: {e}")
                raise ModelInferenceException(
                    f"生成回應失敗: {str(e)}",
                    details={"original_error": type(e).__name__}
                )

    # 註冊錯誤處理器
    register_error_handlers(app)

    return app
