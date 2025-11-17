"""Gradio web interface for medical chatbot"""

from typing import Optional

import gradio as gr
from loguru import logger

from medical_chatbot.inference.generator import MedicalChatGenerator
from medical_chatbot.models.model_manager import ModelManager
from medical_chatbot.utils.config import Config


class GradioInterface:
    """Gradio web interface for medical chatbot"""

    def __init__(self, config: Config):
        """Initialize Gradio interface

        Args:
            config: Application configuration
        """
        self.config = config
        self.model_manager: Optional[ModelManager] = None
        self.generator: Optional[MedicalChatGenerator] = None

    def load_model(self) -> None:
        """Load model and setup generator"""
        logger.info("Loading model for Gradio interface...")

        # Create model manager
        self.model_manager = ModelManager(
            model_name=self.config.model.base_model,
            peft_name=self.config.model.fine_tuned_model,
            torch_dtype=self.config.model.torch_dtype,
            device_map=self.config.model.device_map,
            use_fast_tokenizer=self.config.model.use_fast_tokenizer,
            token=self.config.hf_token,
        )

        # Load model and tokenizer
        tokenizer, model = self.model_manager.load(load_peft=True)

        # Create generator
        self.generator = MedicalChatGenerator(
            model=model,
            tokenizer=tokenizer,
            system_prompt=self.config.prompts.system,
            max_new_tokens=self.config.inference.max_new_tokens,
            temperature=self.config.inference.temperature,
            top_p=self.config.inference.top_p,
            top_k=self.config.inference.top_k,
            repetition_penalty=self.config.inference.repetition_penalty,
            do_sample=self.config.inference.do_sample,
        )

        logger.info("Model loaded successfully for Gradio")

    def chat_function(self, message: str, history: list) -> str:
        """Chat function for Gradio interface

        Args:
            message: User's message
            history: Chat history

        Returns:
            Generated response
        """
        if self.generator is None:
            return "錯誤：模型尚未載入"

        try:
            response = self.generator.generate(user_input=message)
            return response
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            return f"錯誤：生成失敗 - {str(e)}"

    def create_interface(self) -> gr.Blocks:
        """Create Gradio interface

        Returns:
            Gradio Blocks interface
        """
        with gr.Blocks(
            title="醫療聊天機器人", theme=gr.themes.Soft()
        ) as interface:
            gr.Markdown(
                """
                # 醫療聊天機器人 🏥

                基於 TAIDE/Breeze 模型的中文醫療問答系統

                **注意：** 本系統僅供參考，不能替代專業醫療諮詢。如有健康問題，請諮詢專業醫療人員。
                """
            )

            chatbot = gr.Chatbot(
                label="對話",
                height=500,
                show_copy_button=True,
            )

            msg = gr.Textbox(
                label="您的問題",
                placeholder="請輸入您的醫療相關問題...",
                lines=3,
            )

            with gr.Row():
                submit = gr.Button("發送", variant="primary")
                clear = gr.Button("清除對話")

            gr.Examples(
                examples=[
                    # 基礎諮詢
                    "每天肚子痛是什麼狀況？",
                    "頭痛該怎麼辦？",
                    "感冒了應該注意什麼？",
                    "如何預防高血壓？",
                    # 心血管相關
                    "我有高血壓，血壓經常在 150/95 左右，該怎麼辦？",
                    "如何降低膽固醇？",
                    "心悸是心臟有問題嗎？",
                    # 呼吸系統
                    "咳嗽有痰，黃綠色，該怎麼處理？",
                    "氣喘患者日常要注意什麼？",
                    "如何預防流感？",
                    # 慢性疾病
                    "糖尿病患者飲食上應該注意什麼？",
                    "失眠該如何改善？",
                    "如何預防骨質疏鬆？",
                    # 健康保健
                    "如何保持良好的飲食習慣？",
                    "運動對健康有什麼好處？",
                    "壓力過大會導致什麼問題？",
                ],
                inputs=msg,
                label="範例問題",
            )

            def respond(message, chat_history):
                if self.generator is None:
                    bot_message = "錯誤：模型尚未載入"
                else:
                    try:
                        bot_message = self.generator.generate(user_input=message)
                    except Exception as e:
                        logger.error(f"Generation failed: {e}")
                        bot_message = f"錯誤：生成失敗 - {str(e)}"

                chat_history.append((message, bot_message))
                return "", chat_history

            msg.submit(respond, [msg, chatbot], [msg, chatbot])
            submit.click(respond, [msg, chatbot], [msg, chatbot])
            clear.click(lambda: None, None, chatbot, queue=False)

            gr.Markdown(
                """
                ---

                **免責聲明：** 本系統提供的資訊僅供參考，不構成專業醫療建議。
                如有任何健康疑慮，請務必諮詢合格的醫療專業人員。
                """
            )

        return interface

    def launch(
        self,
        share: Optional[bool] = None,
        server_name: Optional[str] = None,
        server_port: Optional[int] = None,
    ) -> None:
        """Launch Gradio interface

        Args:
            share: Whether to create public link
            server_name: Server hostname
            server_port: Server port
        """
        # Load model if not already loaded
        if self.generator is None:
            self.load_model()

        # Create interface
        interface = self.create_interface()

        # Launch parameters
        launch_kwargs = {
            "share": share if share is not None else self.config.gradio.share,
            "server_name": server_name or self.config.gradio.server_name,
            "server_port": server_port or self.config.gradio.server_port,
            "show_error": True,
        }

        logger.info(f"Launching Gradio interface: {launch_kwargs}")
        interface.launch(**launch_kwargs)


def create_gradio_app(config: Config) -> GradioInterface:
    """Create Gradio application

    Args:
        config: Application configuration

    Returns:
        GradioInterface object
    """
    return GradioInterface(config)
