from typing import List, Tuple, Type, Any
from src.plugin_system import (
    BasePlugin,
    register_plugin,
    BaseAction,
    BaseCommand,
    BaseTool,
    ComponentInfo,
    ActionActivationType,
    ConfigField,
    BaseEventHandler,
    EventType,
    MaiMessages,
    ToolParamType,
)
import aiohttp
import json


class WebSearchTool(BaseTool):
    """从网络上搜索的工具"""

    name = "search_web"
    description = "使用工具 从网络上搜索某关键字的相关网页"
    parameters = [
        (
            "keywords",
            ToolParamType.STRING,
            "搜索关键字，支持多个关键字用空格分隔，若关键字必须包含则用双引号\"\"包裹，若关键字必须排除则在关键字前加' -'(英文空格减号)",
            True,
            None,
        ),
    ]
    available_for_llm = True

    async def search(self, kw: str):
        endpoint = "https://s.jina.ai/"
        headers = {
            "Authorization": f"Bearer {self.plugin_config['provider']['jina_api_key']}",
            "Content-Type": "application/json",
        }
        body = {
            "q": kw,
        }

        if self.plugin_config["search"]["search_nation"] != "not-specified":
            body["gl"] = self.plugin_config["search"]["search_nation"]
        if self.plugin_config["search"]["search_language"] != "not-specified":
            body["hl"] = self.plugin_config["search"]["search_language"]

        if self.plugin_config["search"]["crawl_details"]:
            match self.plugin_config["search"]["engine_mode"]:
                case "fast":
                    headers["X-Engine"] = "direct"
                case "quality":
                    headers["X-Engine"] = "browser"
            if self.plugin_config["search"]["timeout"] > 0:
                headers["X-Timeout"] = str(self.plugin_config["search"]["timeout"])
            if self.plugin_config["search"]["remove_pictures"]:
                headers["X-Retain-Images"] = "none"
            if self.plugin_config["search"]["move_links_to_end"]:
                headers["X-With-Links-Summary"] = "true"        
            if self.plugin_config["search"]["move_pics_to_end"]:
                headers["X-With-Images-Summary"] = "true"
            if self.plugin_config["search"]["add_pic_alt"]:
                headers["X-With-Generated-Alt"] = "true"    
        else:
            headers["X-Respond-With"] = "no-content"

        async with aiohttp.ClientSession() as session:
            async with session.post(
                endpoint, headers=headers, data=json.dumps(body)
            ) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    raise Exception(f"搜索请求失败，状态码: {response.status}")

    async def execute(self, function_args: dict[str, Any]) -> dict[str, Any]:
        """执行从网络上搜索某关键字的相关网页

        Args:
            function_args: 工具参数

        Returns:
            dict: 工具执行结果
        """
        keywords: str = function_args.get("keywords")  # type: ignore

        try:
            search_results = await self.search(keywords)
            return {"name": self.name, "content": search_results}
        except Exception as e:
            return {"name": self.name, "content": f"搜索失败: {str(e)}"}

class UrlCrawlTool(BaseTool):
    """从URL提取内容的工具"""

    name = "crawl_url"
    description = "使用工具 从指定URL提取网页内容"
    parameters = [
        (
            "url",
            ToolParamType.STRING,
            "要提取内容的网页URL，必须以http://或https://开头",
            True,
            None,
        ),
    ]
    available_for_llm = True

    async def crawl(self, url: str):
        endpoint = "https://r.jina.ai/"
        headers = {
            "Authorization": f"Bearer {self.plugin_config['provider']['jina_api_key']}",
            "Content-Type": "application/json",
        }
        body = {
            "url": url,
        }

        match self.plugin_config["extract"]["engine_mode"]:
            case "fast":
                headers["X-Engine"] = "direct"
            case "quality":
                headers["X-Engine"] = "browser"
        if self.plugin_config["extract"]["timeout"] > 0:
            headers["X-Timeout"] = str(self.plugin_config["extract"]["timeout"])
        if self.plugin_config["extract"]["follow_redirect"]:
            headers["X-Follow-Redirects"] = "true"
        if self.plugin_config["extract"]["use_custom_prehandler_scripts"]:
            headers["X-Use-Custom-Prehandler-Scripts"] = "true"
            if self.plugin_config["extract"]["custom_prehandler_scripts_list"]:
                headers["X-Custom-Prehandler-Scripts-List"] = ",".join(
                    self.plugin_config["extract"]["custom_prehandler_scripts_list"]
                )
        if self.plugin_config["extract"]["include_shadow_dom"]:
            headers["X-Include-Shadow-DOM"] = "true"
        if self.plugin_config["extract"]["include_iframes"]:
            headers["X-Include-Iframes"] = "true"
        if self.plugin_config["extract"]["remove_pictures"]:
            headers["X-Retain-Images"] = "none"
        if self.plugin_config["extract"]["use_readerlm_v2"]:
            headers["X-Use-ReaderLM-V2"] = "true"
        if self.plugin_config["extract"]["move_links_to_end"]:
            headers["X-With-Links-Summary"] = "true"        
        if self.plugin_config["extract"]["move_pics_to_end"]:
            headers["X-With-Images-Summary"] = "true"
        if self.plugin_config["extract"]["add_pic_alt"]:
            headers["X-With-Generated-Alt"] = "true"    
        if self.plugin_config["extract"]["optimize_for_gpt_oss"]:
            headers["X-Optimize-For-GPT-OSS"] = "true"

        async with aiohttp.ClientSession() as session:
            async with session.post(
                endpoint, headers=headers, data=json.dumps(body)
            ) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    raise Exception(f"内容提取请求失败，状态码: {response.status}")
                
    async def execute(self, function_args: dict[str, Any]) -> dict[str, Any]:
        """执行从指定URL提取网页内容

        Args:
            function_args: 工具参数

        Returns:
            dict: 工具执行结果
        """
        url: str = function_args.get("url")  # type: ignore

        try:
            crawl_result = await self.crawl(url)
            return {"name": self.name, "content": crawl_result}
        except Exception as e:
            return {"name": self.name, "content": f"内容提取失败: {str(e)}"}

# ===== 插件注册 =====


@register_plugin
class WebCrawlPlugin(BasePlugin):
    """WebCrawl 插件 - 基于Jina服务提供网页爬虫相关的工具和功能"""

    # 插件基本信息
    plugin_name: str = "cky-web-crawl"  # 内部标识符
    enable_plugin: bool = True
    dependencies: List[str] = []  # 插件依赖列表
    python_dependencies: List[str] = []  # Python包依赖列表
    config_file_name: str = "config.toml"  # 配置文件名

    # 配置节描述
    config_section_descriptions = {
        "plugin": "插件基本信息",
        "provider": "Jina 服务配置",
        "search": "搜索功能配置",
        "extract": "URL 内容提取功能配置",
    }

    # 配置Schema定义
    config_schema: dict = {
        "plugin": {
            "name": ConfigField(
                type=str, default="cky-web-crawl", description="插件名称"
            ),
            "version": ConfigField(type=str, default="1.0.0", description="插件版本"),
            "enabled": ConfigField(
                type=bool, default=False, description="是否启用插件"
            ),
        },
        "provider": {
            # "use_api_key": ConfigField(
            #     type=bool, default=False, description="是否使用Jina API Key"
            # ),
            "jina_api_key": ConfigField(
                type=str, default="", description="Jina API Key", required=True
            ),
        },
        "search": {
            "search_nation": ConfigField(
                type=str,
                default="CN",
                description="搜索国家/地区代码",
                choices=[
                    "not-specified",
                    "US",
                    "CN",
                    "JP",
                    "DE",
                    "FR",
                    "GB",
                    "IN",
                    "CA",
                    "AU",
                    "BR",
                    "RU",
                    "IT",
                    "ES",
                ],
            ),
            "search_language": ConfigField(
                type=str,
                default="zh-cn",
                description="搜索语言代码",
                choices=["not-specified", "en", "zh-cn", "ja", "de", "fr", "es"],
            ),
            "crawl_details": ConfigField(
                type=bool, default=False, description="获取每个搜索结果 URL 的具体信息"
            ),
            "timeout": ConfigField(
                type=int,
                default=10,
                description="加载超时时间（秒）(获取每个 URL 结果时)",
            ),
            "engine_mode": ConfigField(
                type=str,
                default="default",
                description="引擎模式 (平衡/快速/质量) (获取每个 URL 结果时)",
                choices=["default", "fast", "quality"],
            ),
            "remove_pictures": ConfigField(
                type=bool,
                default=True,
                description="移除图片内容 (获取每个 URL 结果时)",
            ),
            "move_links_to_end": ConfigField(
                type=bool,
                default=True,
                description="将链接移到内容末尾 (获取每个 URL 结果时)",
            ),
            "move_pics_to_end": ConfigField(
                type=bool,
                default=True,
                description="将图片链接移到内容末尾 (获取每个 URL 结果时)",
            ),
            "add_pic_alt": ConfigField(
                type=bool,
                default=True,
                description="包含图片说明Alt文本 (获取每个 URL 结果时)",
            ),
        },
        "extract": {
            "timeout": ConfigField(
                type=int, default=10, description="加载超时时间（秒）"
            ),
            "follow_redirect": ConfigField(
                type=bool, default=True, description="跟随重定向"
            ),
            "use_custom_prehandler_scripts": ConfigField(
                type=bool, default=False, description="是否使用自定义预处理脚本"
            ),
            "custom_prehandler_scripts_list": ConfigField(
                type=list, default=[], description="自定义预处理脚本列表"
            ),
            "include_shadow_dom": ConfigField(
                type=bool, default=False, description="包含Shadow DOM内容"
            ),
            "include_iframes": ConfigField(
                type=bool, default=False, description="包含iframe内容"
            ),
            "remove_pictures": ConfigField(
                type=bool, default=True, description="移除图片内容"
            ),
            "use_readerlm_v2": ConfigField(
                type=bool, default=False, description="使用ReaderLM V2进行内容提取"
            ),
            "move_links_to_end": ConfigField(
                type=bool, default=True, description="将链接移到内容末尾"
            ),
            "move_pics_to_end": ConfigField(
                type=bool, default=True, description="将图片链接移到内容末尾"
            ),
            "add_pic_alt": ConfigField(
                type=bool, default=True, description="包含图片说明Alt文本"
            ),
            "optimize_for_gpt_oss": ConfigField(
                type=bool, default=False, description="启用为GPT-OSS优化"
            ),
            "engine_mode": ConfigField(
                type=str,
                default="default",
                description="引擎模式 (平衡/快速/质量)",
                choices=["default", "fast", "quality"],
            ),
        },
    }

    def get_plugin_components(self) -> List[Tuple[ComponentInfo, Type]]:
        return [
            (WebSearchTool.get_tool_info(), WebSearchTool), 
            (UrlCrawlTool.get_tool_info(), UrlCrawlTool),
        ]
