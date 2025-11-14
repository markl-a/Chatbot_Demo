"""FastAPI server for medical chatbot"""

from contextlib import asynccontextmanager
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from pydantic import BaseModel, Field

from medical_chatbot.inference.generator import MedicalChatGenerator
from medical_chatbot.models.model_manager import ModelManager
from medical_chatbot.utils.config import Config


# Global variables for model and generator
model_manager: Optional[ModelManager] = None
generator: Optional[MedicalChatGenerator] = None
config: Optional[Config] = None


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
    """Lifespan events for FastAPI app"""
    # Startup
    global model_manager, generator, config

    logger.info("Loading model on startup...")

    try:
        # Load model and tokenizer
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
    """Create FastAPI application

    Args:
        app_config: Application configuration

    Returns:
        FastAPI application
    """
    global model_manager, config

    config = app_config

    # Create model manager
    model_manager = ModelManager(
        model_name=config.model.base_model,
        peft_name=config.model.fine_tuned_model,
        torch_dtype=config.model.torch_dtype,
        device_map=config.model.device_map,
        use_fast_tokenizer=config.model.use_fast_tokenizer,
        token=config.hf_token,
    )

    # Create FastAPI app
    app = FastAPI(
        title="Medical Chatbot API",
        description="醫療聊天機器人 API - 基於 TAIDE/Breeze 模型的中文醫療問答系統",
        version="0.2.0",
        lifespan=lifespan,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/", response_model=dict)
    async def root():
        """Root endpoint"""
        return {
            "name": "Medical Chatbot API",
            "version": "0.2.0",
            "description": "醫療聊天機器人 API",
        }

    @app.get("/health", response_model=HealthResponse)
    async def health():
        """Health check endpoint"""
        return HealthResponse(
            status="healthy" if generator is not None else "unhealthy",
            model_loaded=generator is not None,
        )

    @app.post("/chat", response_model=ChatResponse)
    async def chat(request: ChatRequest):
        """Chat endpoint for single-turn conversation

        Args:
            request: Chat request with user message

        Returns:
            Generated response

        Raises:
            HTTPException: If model is not loaded or generation fails
        """
        if generator is None:
            raise HTTPException(status_code=503, detail="Model not loaded")

        try:
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
                user_input=request.message,
                system_prompt=request.system_prompt,
                **gen_kwargs,
            )

            return ChatResponse(response=response, message=request.message)

        except Exception as e:
            logger.error(f"Generation failed: {e}")
            raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")

    @app.post("/conversation", response_model=ChatResponse)
    async def conversation(request: ConversationRequest):
        """Conversation endpoint for multi-turn conversation

        Args:
            request: Conversation request with message history

        Returns:
            Generated response

        Raises:
            HTTPException: If model is not loaded or generation fails
        """
        if generator is None:
            raise HTTPException(status_code=503, detail="Model not loaded")

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

            return ChatResponse(response=response, message=last_user_message)

        except Exception as e:
            logger.error(f"Generation failed: {e}")
            raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")

    return app
