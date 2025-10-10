from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register, StarTools
from astrbot.api import logger, AstrBotConfig
import astrbot.api.message_components as Comp

from .data_manager import DataManager

@register("guncode", "清蒸云鸭", "三角洲改枪码插件，支持自定义添加，JSON持久化", "1.0.0")
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        # self.config = config # 插件配置
        self.data_path = StarTools.get_data_dir("guncode") # 插件数据目录
        self.bot_config = context.get_config() # 机器人配置
        self.admin_list = self.bot_config.get("admins_id") # 机器人管理员列表
        self.datamanager = DataManager() # 数据管理器实例

    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""
    
    @filter.command("改枪码",alias=["guncode"])
    async def guncode(self, event: AstrMessageEvent):
        """获取改枪码"""
        pass

    @filter.command("改枪码管理")
    async def guncode_manage(self, event: AstrMessageEvent, subcommand: str = None, arg1: str = None, arg2: str = None):
        """管理改枪码"""
        messages = []
        if event.get_sender_id() not in self.admin_list:
            if event.get_platform_name == "aiocqhttp":
                messages.append(Comp.At(qq=event.get_sender_id()))
            messages.append(Comp.Plain("❌你没有权限使用此命令！"))
            yield event.chain_result(messages)
            return
        
        if subcommand is None:
            if event.get_platform_name == "aiocqhttp":
                messages.append(Comp.At(qq=event.get_sender_id()))
            messages.append(Comp.Plain("❌缺少参数！可用子命令：添加，删除，查看，清空"))
            yield event.chain_result(messages)
            return

        match subcommand:
            case "添加":
                pass
            case "删除":
                pass
            case "查看":
                pass
            case _:
                if event.get_platform_name == "aiocqhttp":
                    messages.append(Comp.At(qq=event.get_sender_id()))
                messages.append(Comp.Plain("❌无效的子命令！可用子命令：添加，删除，查看，清空"))
                yield event.chain_result(messages)
                return
        

        pass

    @filter.command("改枪码帮助")
    async def guncode_help(self, event: AstrMessageEvent):
        """改枪码帮助"""
        help_text = (
            "改枪码插件使用帮助：\n"
            "1. 获取改枪码：'/改枪码' 或 '/guncode'\n"
            "2. 管理改枪码：'/改枪码管理'\n"
            "3. 查看帮助：'/改枪码帮助'"
        )
        await event.plain_result(help_text)
        return MessageEventResult(True)
        

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
