"""Command-line interface for medical chatbot"""

import os
from pathlib import Path
from typing import Optional

import typer
import uvicorn
from loguru import logger
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from medical_chatbot.api.gradio_app import create_gradio_app
from medical_chatbot.api.server import create_app
from medical_chatbot.data.dataset import load_dataset
from medical_chatbot.models.lora_trainer import LoraTrainer
from medical_chatbot.models.model_manager import ModelManager
from medical_chatbot.utils.config import load_config
from medical_chatbot.utils.logger import setup_logger

app = typer.Typer(
    name="medical-chatbot",
    help="醫療聊天機器人 - Medical Chatbot CLI",
    add_completion=False,
)
console = Console()


@app.command()
def train(
    config_path: str = typer.Option(
        "configs/config.yaml", "--config", "-c", help="Path to configuration file"
    ),
    output_dir: Optional[str] = typer.Option(
        None, "--output", "-o", help="Output directory for trained model"
    ),
    resume_from_checkpoint: Optional[str] = typer.Option(
        None, "--resume", "-r", help="Resume training from checkpoint"
    ),
):
    """Train the medical chatbot model"""
    console.print("[bold blue]Starting model training...[/bold blue]")

    # Load config
    config = load_config(config_path)
    setup_logger(config.logging.file, config.logging.level)

    # Set HF token from environment
    if "HF_TOKEN" in os.environ:
        config.hf_token = os.environ["HF_TOKEN"]

    # Override output dir if specified
    if output_dir:
        config.training.output_dir = output_dir

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        # Load dataset
        task = progress.add_task("Loading dataset...", total=None)
        dataset = load_dataset(
            dataset_path=config.dataset.raw_path,
            dataset_url=config.dataset.url,
            download_if_missing=True,
        )
        progress.update(task, description="[green]Dataset loaded")

        # Load model
        task = progress.add_task("Loading model...", total=None)
        model_manager = ModelManager(
            model_name=config.model.base_model,
            torch_dtype=config.model.torch_dtype,
            device_map=config.model.device_map,
            use_fast_tokenizer=config.model.use_fast_tokenizer,
            token=config.hf_token,
        )
        tokenizer, model = model_manager.load(load_peft=False)
        progress.update(task, description="[green]Model loaded")

        # Process dataset
        task = progress.add_task("Processing dataset...", total=None)
        tokenized_dataset = dataset.process(tokenizer)
        progress.update(task, description="[green]Dataset processed")

        # Setup trainer
        task = progress.add_task("Setting up trainer...", total=None)
        trainer = LoraTrainer(
            model=model,
            tokenizer=tokenizer,
            lora_config={
                "r": config.lora.r,
                "lora_alpha": config.lora.lora_alpha,
                "lora_dropout": config.lora.lora_dropout,
                "target_modules": config.lora.target_modules,
            },
            training_config={
                "output_dir": config.training.output_dir,
                "num_train_epochs": config.training.num_train_epochs,
                "per_device_train_batch_size": config.training.per_device_train_batch_size,
                "gradient_accumulation_steps": config.training.gradient_accumulation_steps,
                "learning_rate": config.training.learning_rate,
                "weight_decay": config.training.weight_decay,
                "logging_steps": config.training.logging_steps,
                "save_steps": config.training.save_steps,
                "save_total_limit": config.training.save_total_limit,
                "gradient_checkpointing": config.training.gradient_checkpointing,
                "bf16": config.training.bf16,
            },
        )
        trainer.setup_lora()
        trainer.setup_trainer(train_dataset=tokenized_dataset)
        progress.update(task, description="[green]Trainer setup complete")

    # Train
    console.print("[bold green]Training started...[/bold green]")
    trainer.train()

    # Save model
    save_dir = config.training.output_dir + "/final"
    console.print(f"[bold blue]Saving model to {save_dir}...[/bold blue]")
    trainer.save(save_dir)

    console.print("[bold green]Training completed successfully![/bold green]")


@app.command()
def serve(
    config_path: str = typer.Option(
        "configs/config.yaml", "--config", "-c", help="Path to configuration file"
    ),
    host: Optional[str] = typer.Option(None, "--host", "-h", help="Server host"),
    port: Optional[int] = typer.Option(None, "--port", "-p", help="Server port"),
    reload: bool = typer.Option(False, "--reload", help="Enable auto-reload"),
):
    """Start the FastAPI server"""
    console.print("[bold blue]Starting FastAPI server...[/bold blue]")

    # Load config
    config = load_config(config_path)
    setup_logger(config.logging.file, config.logging.level)

    # Set HF token from environment
    if "HF_TOKEN" in os.environ:
        config.hf_token = os.environ["HF_TOKEN"]

    # Override settings if specified
    if host:
        config.api.host = host
    if port:
        config.api.port = port

    # Create app
    fastapi_app = create_app(config)

    # Start server
    uvicorn.run(
        fastapi_app,
        host=config.api.host,
        port=config.api.port,
        reload=reload,
        log_level=config.api.log_level,
    )


@app.command()
def gradio(
    config_path: str = typer.Option(
        "configs/config.yaml", "--config", "-c", help="Path to configuration file"
    ),
    share: Optional[bool] = typer.Option(None, "--share", help="Create public link"),
    server_name: Optional[str] = typer.Option(
        None, "--host", "-h", help="Server hostname"
    ),
    server_port: Optional[int] = typer.Option(None, "--port", "-p", help="Server port"),
):
    """Start the Gradio web interface"""
    console.print("[bold blue]Starting Gradio interface...[/bold blue]")

    # Load config
    config = load_config(config_path)
    setup_logger(config.logging.file, config.logging.level)

    # Set HF token from environment
    if "HF_TOKEN" in os.environ:
        config.hf_token = os.environ["HF_TOKEN"]

    # Create and launch Gradio app
    gradio_app = create_gradio_app(config)
    gradio_app.launch(share=share, server_name=server_name, server_port=server_port)


@app.command()
def chat(
    config_path: str = typer.Option(
        "configs/config.yaml", "--config", "-c", help="Path to configuration file"
    ),
    message: Optional[str] = typer.Option(None, "--message", "-m", help="Message to send"),
):
    """Interactive chat with the medical chatbot"""
    console.print("[bold blue]Loading medical chatbot...[/bold blue]")

    # Load config
    config = load_config(config_path)
    setup_logger(config.logging.file, config.logging.level)

    # Set HF token from environment
    if "HF_TOKEN" in os.environ:
        config.hf_token = os.environ["HF_TOKEN"]

    # Load model
    from medical_chatbot.inference.generator import MedicalChatGenerator

    model_manager = ModelManager(
        model_name=config.model.base_model,
        peft_name=config.model.fine_tuned_model,
        torch_dtype=config.model.torch_dtype,
        device_map=config.model.device_map,
        use_fast_tokenizer=config.model.use_fast_tokenizer,
        token=config.hf_token,
    )

    with console.status("[bold green]Loading model..."):
        tokenizer, model = model_manager.load(load_peft=True)

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

    console.print("[bold green]Model loaded! Type 'exit' or 'quit' to exit.[/bold green]\n")

    # Single message mode
    if message:
        response = generator.generate(user_input=message)
        console.print(f"[bold cyan]You:[/bold cyan] {message}")
        console.print(f"[bold green]Bot:[/bold green] {response}\n")
        return

    # Interactive mode
    while True:
        try:
            user_input = console.input("[bold cyan]You:[/bold cyan] ")

            if user_input.lower() in ["exit", "quit", "q"]:
                console.print("[bold yellow]Goodbye![/bold yellow]")
                break

            if not user_input.strip():
                continue

            with console.status("[bold green]Thinking..."):
                response = generator.generate(user_input=user_input)

            console.print(f"[bold green]Bot:[/bold green] {response}\n")

        except KeyboardInterrupt:
            console.print("\n[bold yellow]Goodbye![/bold yellow]")
            break
        except Exception as e:
            console.print(f"[bold red]Error: {e}[/bold red]")


if __name__ == "__main__":
    app()
