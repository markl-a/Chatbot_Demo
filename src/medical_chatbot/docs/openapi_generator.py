"""
OpenAPI 文檔生成器

自動生成和自訂 FastAPI OpenAPI 文檔。
"""
from typing import Dict, Any, Optional, List, Callable
from pathlib import Path
import json

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.responses import HTMLResponse
from loguru import logger

from .docs_config import DocsConfig, SwaggerUIConfig, ReDocConfig


class OpenAPIGenerator:
    """OpenAPI 文檔生成器"""

    def __init__(self, app: FastAPI, config: Optional[DocsConfig] = None):
        """
        初始化生成器

        Args:
            app: FastAPI 應用實例
            config: 文檔配置
        """
        self.app = app
        self.config = config or DocsConfig()

        logger.info(f"OpenAPI 文檔生成器初始化: {self.config.title} v{self.config.version}")

    # ========================================================================
    # 基本配置
    # ========================================================================

    def setup_docs(
        self,
        swagger_ui_config: Optional[SwaggerUIConfig] = None,
        redoc_config: Optional[ReDocConfig] = None,
    ):
        """
        配置 FastAPI 文檔

        Args:
            swagger_ui_config: Swagger UI 配置
            redoc_config: ReDoc 配置
        """
        # 更新 FastAPI 應用配置
        self.app.title = self.config.title
        self.app.description = self.config.description
        self.app.version = self.config.version
        self.app.contact = self.config.contact.dict()
        self.app.license_info = self.config.license_info.dict()
        self.app.servers = [s.dict() for s in self.config.servers]
        self.app.openapi_tags = self.config.tags_metadata

        # 自訂 OpenAPI schema
        def custom_openapi():
            if self.app.openapi_schema:
                return self.app.openapi_schema

            openapi_schema = get_openapi(
                title=self.config.title,
                version=self.config.version,
                description=self.config.description,
                routes=self.app.routes,
                tags=self.config.tags_metadata,
                servers=[s.dict() for s in self.config.servers],
            )

            # 添加安全方案
            openapi_schema["components"]["securitySchemes"] = (
                self.config.security_schemes
            )

            # 添加自訂資訊
            openapi_schema["info"]["contact"] = self.config.contact.dict()
            openapi_schema["info"]["license"] = self.config.license_info.dict()

            # 添加範例
            self._add_examples_to_schema(openapi_schema)

            self.app.openapi_schema = openapi_schema
            return self.app.openapi_schema

        self.app.openapi = custom_openapi

        # 自訂 Swagger UI
        if self.config.docs_url:
            self._setup_custom_swagger_ui(swagger_ui_config or SwaggerUIConfig())

        # 自訂 ReDoc
        if self.config.redoc_url:
            self._setup_custom_redoc(redoc_config or ReDocConfig())

        logger.info("API 文檔配置完成")

    def _add_examples_to_schema(self, schema: Dict[str, Any]):
        """添加範例到 OpenAPI schema"""
        # 這裡可以根據需要添加更多範例
        for path, path_item in schema.get("paths", {}).items():
            for method, operation in path_item.items():
                if method in ["get", "post", "put", "delete", "patch"]:
                    # 添加請求範例
                    if "requestBody" in operation:
                        # 可以根據路徑添加相應的範例
                        pass

                    # 添加回覆範例
                    for status_code, response in operation.get("responses", {}).items():
                        # 可以根據狀態碼添加範例
                        pass

    # ========================================================================
    # Swagger UI 自訂
    # ========================================================================

    def _setup_custom_swagger_ui(self, config: SwaggerUIConfig):
        """設置自訂 Swagger UI"""

        @self.app.get(self.config.docs_url, include_in_schema=False)
        async def custom_swagger_ui_html():
            return get_swagger_ui_html(
                openapi_url=self.app.openapi_url,
                title=f"{self.app.title} - Swagger UI",
                swagger_ui_parameters={
                    "displayRequestDuration": config.display_request_duration,
                    "displayOperationId": config.display_operation_id,
                    "showExtensions": config.show_extensions,
                    "showCommonExtensions": config.show_common_extensions,
                    "defaultModelExpandDepth": config.default_model_expand_depth,
                    "defaultModelsExpandDepth": config.default_models_expand_depth,
                    "filter": config.filter,
                },
            )

    # ========================================================================
    # ReDoc 自訂
    # ========================================================================

    def _setup_custom_redoc(self, config: ReDocConfig):
        """設置自訂 ReDoc"""

        @self.app.get(self.config.redoc_url, include_in_schema=False)
        async def custom_redoc_html():
            return get_redoc_html(
                openapi_url=self.app.openapi_url,
                title=f"{self.app.title} - ReDoc",
                redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@latest/bundles/redoc.standalone.js",
            )

    # ========================================================================
    # 文檔導出
    # ========================================================================

    def export_openapi_spec(self, output_file: str = "openapi.json"):
        """
        導出 OpenAPI 規範

        Args:
            output_file: 輸出檔案路徑

        Returns:
            OpenAPI schema
        """
        schema = self.app.openapi()

        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(schema, f, ensure_ascii=False, indent=2)

        logger.info(f"OpenAPI 規範已導出: {output_path}")

        return schema

    def export_markdown_docs(self, output_file: str = "API_DOCS.md"):
        """
        導出 Markdown 格式的 API 文檔

        Args:
            output_file: 輸出檔案路徑

        Returns:
            Markdown 內容
        """
        schema = self.app.openapi()

        markdown = self._generate_markdown_from_schema(schema)

        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(markdown)

        logger.info(f"Markdown 文檔已導出: {output_path}")

        return markdown

    def _generate_markdown_from_schema(self, schema: Dict[str, Any]) -> str:
        """從 OpenAPI schema 生成 Markdown"""
        lines = []

        # 標題
        info = schema.get("info", {})
        lines.extend(
            [
                f"# {info.get('title', 'API Documentation')}",
                "",
                info.get("description", ""),
                "",
                f"**版本**: {info.get('version', 'N/A')}",
                "",
            ]
        )

        # 伺服器
        servers = schema.get("servers", [])
        if servers:
            lines.extend(
                [
                    "## 伺服器",
                    "",
                ]
            )
            for server in servers:
                lines.append(f"- **{server.get('description', 'Server')}**: `{server.get('url')}`")
            lines.append("")

        # 端點
        paths = schema.get("paths", {})
        if paths:
            lines.extend(
                [
                    "## API 端點",
                    "",
                ]
            )

            for path, path_item in paths.items():
                for method, operation in path_item.items():
                    if method in ["get", "post", "put", "delete", "patch"]:
                        lines.extend(self._format_operation_markdown(path, method, operation))

        # 安全方案
        security_schemes = schema.get("components", {}).get("securitySchemes", {})
        if security_schemes:
            lines.extend(
                [
                    "## 認證",
                    "",
                ]
            )
            for name, scheme in security_schemes.items():
                lines.append(f"### {name}")
                lines.append(f"- **類型**: {scheme.get('type')}")
                if "description" in scheme:
                    lines.append(f"- **說明**: {scheme.get('description')}")
                lines.append("")

        return "\n".join(lines)

    def _format_operation_markdown(
        self, path: str, method: str, operation: Dict[str, Any]
    ) -> List[str]:
        """格式化單個操作為 Markdown"""
        lines = []

        # 操作標題
        summary = operation.get("summary", path)
        lines.extend(
            [
                f"### `{method.upper()}` {path}",
                "",
                summary,
                "",
            ]
        )

        # 描述
        if "description" in operation:
            lines.extend(
                [
                    operation["description"],
                    "",
                ]
            )

        # 標籤
        tags = operation.get("tags", [])
        if tags:
            lines.append(f"**標籤**: {', '.join(tags)}")
            lines.append("")

        # 參數
        parameters = operation.get("parameters", [])
        if parameters:
            lines.extend(
                [
                    "**參數**:",
                    "",
                    "| 名稱 | 位置 | 類型 | 必需 | 說明 |",
                    "|------|------|------|------|------|",
                ]
            )
            for param in parameters:
                name = param.get("name", "")
                location = param.get("in", "")
                param_type = param.get("schema", {}).get("type", "")
                required = "是" if param.get("required", False) else "否"
                description = param.get("description", "")
                lines.append(f"| {name} | {location} | {param_type} | {required} | {description} |")
            lines.append("")

        # 請求體
        if "requestBody" in operation:
            lines.extend(
                [
                    "**請求體**:",
                    "",
                    "```json",
                ]
            )

            # 簡化的請求體範例
            content = operation["requestBody"].get("content", {})
            if "application/json" in content:
                schema = content["application/json"].get("schema", {})
                lines.append(json.dumps(self._generate_example_from_schema(schema), indent=2))

            lines.extend(
                [
                    "```",
                    "",
                ]
            )

        # 回覆
        responses = operation.get("responses", {})
        if responses:
            lines.extend(
                [
                    "**回覆**:",
                    "",
                ]
            )
            for status_code, response in responses.items():
                description = response.get("description", "")
                lines.append(f"- **{status_code}**: {description}")
            lines.append("")

        lines.append("---")
        lines.append("")

        return lines

    def _generate_example_from_schema(self, schema: Dict[str, Any]) -> Any:
        """從 schema 生成範例值"""
        if "example" in schema:
            return schema["example"]

        schema_type = schema.get("type")

        if schema_type == "object":
            properties = schema.get("properties", {})
            example = {}
            for key, prop in properties.items():
                example[key] = self._generate_example_from_schema(prop)
            return example

        elif schema_type == "array":
            items = schema.get("items", {})
            return [self._generate_example_from_schema(items)]

        elif schema_type == "string":
            return schema.get("default", "string")

        elif schema_type == "integer":
            return schema.get("default", 0)

        elif schema_type == "number":
            return schema.get("default", 0.0)

        elif schema_type == "boolean":
            return schema.get("default", False)

        else:
            return None

    # ========================================================================
    # 額外功能
    # ========================================================================

    def add_custom_route_docs(
        self,
        path: str,
        method: str,
        summary: str,
        description: str,
        tags: Optional[List[str]] = None,
        **kwargs,
    ):
        """
        為現有路由添加自訂文檔

        Args:
            path: 路由路徑
            method: HTTP 方法
            summary: 摘要
            description: 詳細說明
            tags: 標籤列表
            **kwargs: 其他 OpenAPI 屬性
        """
        # 這需要在路由定義時調用
        # 這裡提供一個工具方法
        pass

    def generate_client_sdk(self, language: str = "python", output_dir: str = "./sdk"):
        """
        生成客戶端 SDK（需要 openapi-generator）

        Args:
            language: 語言（python/javascript/java 等）
            output_dir: 輸出目錄
        """
        import subprocess

        # 導出 OpenAPI 規範
        spec_file = "openapi_temp.json"
        self.export_openapi_spec(spec_file)

        try:
            # 使用 openapi-generator-cli 生成 SDK
            cmd = [
                "openapi-generator-cli",
                "generate",
                "-i",
                spec_file,
                "-g",
                language,
                "-o",
                output_dir,
            ]

            subprocess.run(cmd, check=True)

            logger.info(f"{language} SDK 已生成: {output_dir}")

        except subprocess.CalledProcessError as e:
            logger.error(f"生成 SDK 失敗: {e}")
            logger.info("請確保已安裝 openapi-generator-cli")

        except FileNotFoundError:
            logger.error("找不到 openapi-generator-cli")
            logger.info("請安裝: npm install -g @openapitools/openapi-generator-cli")

        finally:
            # 清理臨時檔案
            Path(spec_file).unlink(missing_ok=True)

    def __repr__(self) -> str:
        """字串表示"""
        return (
            f"OpenAPIGenerator(title='{self.config.title}', "
            f"version='{self.config.version}')"
        )
