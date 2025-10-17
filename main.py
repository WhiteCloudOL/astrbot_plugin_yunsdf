from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register, StarTools
from astrbot.api import logger, AstrBotConfig
import astrbot.api.message_components as Comp
from pathlib import Path
from playwright.async_api import async_playwright

from .data_manager import DataManager

@register("yunsdf", "清蒸云鸭", "三角洲改枪码、每日密码、交易行查询插件，支持自定义添加，JSON持久化", "1.0.0")
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.data_path = StarTools.get_data_dir("yunsdf")
        self.bot_config = context.get_config()
        self.admin_list = self.bot_config.get("admins_id", [])
        self.datamanager = DataManager(data_file=self.data_path/"gun_data.json")
        
        # 用户临时数据存储
        self.user_temp_data = {}
        self.screenshot_dir = self.data_path / "screenshots"
        self.screenshot_dir.mkdir(exist_ok=True)

    async def initialize(self):
        """插件初始化"""
        logger.info("改枪码插件初始化完成")

    @filter.command("改枪码", alias=["guncode"])
    async def guncode(self, event: AstrMessageEvent, gun_name: str = None):
        """获取改枪码"""
        if gun_name is None:
            messages = []
            if event.get_platform_name() == "aiocqhttp":
                messages.append(Comp.At(qq=event.get_sender_id()))
            messages.append(Comp.Plain("❌缺少参数！请提供枪械名称。"))
            yield event.chain_result(messages)
            return
        
        # 搜索匹配的枪械
        found_guns = self.datamanager.search_guns(gun_name)
        gun_num = len(found_guns)
        
        if gun_num < 1:
            messages = []
            if event.get_platform_name() == "aiocqhttp":
                messages.append(Comp.At(qq=event.get_sender_id()))
            messages.append(Comp.Plain(f"❌未找到名称包含 '{gun_name}' 的枪械。"))
            yield event.chain_result(messages)
            return
        
        if gun_num == 1:
            # 直接显示单个匹配结果
            gun_name = found_guns[0]
            async for result in self._display_gun_codes(event, gun_name):
                yield result
            return
        
        # 多个匹配结果，让用户选择
        if event.get_platform_name() in ("aiocqhttp", "webchat"):
            res = f"找到 {gun_num} 个匹配的枪械：\n"
            res += "| id | 枪名 |\n"
            for i in range(gun_num):
                res += f"{i+1}. {found_guns[i]}\n"
            res += "\n请执行命令 /选择 id ，否则请输入 /取消"
            
            # 存储临时数据
            self._set_user_temp_data(event.get_sender_id(), event.get_group_id(), found_guns)
            
            messages = []
            if event.get_platform_name() == "aiocqhttp":
                messages.append(Comp.At(qq=event.get_sender_id()))
            messages.append(Comp.Plain(res))
            yield event.chain_result(messages)

    @filter.command("选择")
    async def select_gun(self, event: AstrMessageEvent, choose_id: int):
        """选择枪械"""
        try:
            choose_id = int(choose_id)
        except (ValueError, TypeError):
            yield event.plain_result("❌ID参数无效，请输入数字")
            return
        
        user_id = event.get_sender_id()
        group_id = event.get_group_id()
        
        guns = self._get_user_temp_data(user_id, group_id)
        if not guns:
            yield event.plain_result("❌请先使用 '/改枪码 枪名' 命令查询枪械，然后再 '/选择 id'")
            return
        
        if choose_id < 1 or choose_id > len(guns):
            yield event.plain_result(f"❌ID范围错误，请输入 1-{len(guns)} 之间的数字")
            return
        
        gun_name = guns[choose_id - 1]
        async for result in self._display_gun_codes(event, gun_name):
            yield result
        
        # 清除临时数据
        self._clear_user_temp_data(user_id, group_id)

    @filter.command("取消")
    async def cancel_selection(self, event: AstrMessageEvent):
        """取消选择"""
        user_id = event.get_sender_id()
        group_id = event.get_group_id()
        self._clear_user_temp_data(user_id, group_id)
        
        messages = []
        if event.get_platform_name() == "aiocqhttp":
            messages.append(Comp.At(qq=event.get_sender_id()))
        messages.append(Comp.Plain("✅已取消选择"))
        yield event.chain_result(messages)

    async def _display_gun_codes(self, event: AstrMessageEvent, gun_name: str):
        """显示枪械的改枪码"""
        gun_data = self.datamanager.get_gun(gun_name)
        if not gun_data:
            messages = []
            if event.get_platform_name() == "aiocqhttp":
                messages.append(Comp.At(qq=event.get_sender_id()))
            messages.append(Comp.Plain(f"❌未找到枪械 '{gun_name}' 的数据"))
            yield event.chain_result(messages)
            return
        
        # 构建回复消息
        result = f"欢迎使用Yun's GunCode~\n🔫 枪械: {gun_name}\n\n"
        
        # Firezone 数据 - 按价格升序排列
        firezone_codes = self.datamanager.get_gun_codes(gun_name, "firezone", sort_by_price=True)
        if firezone_codes:
            result += "🔥 烽火地带 改枪码:\n"
            for level, data in firezone_codes:
                price = data.get('price', 0)
                price_text = f"{price/10000:.1f}万" if price >= 10000 else f"{price}元"
                if "丐版" in data['description'] or "基础" in data['description']:
                    price_text = f"{price_text}丐版"
                
                # 按照新格式：枪名 描述: 枪名-烽火地带-代码
                code_line = f"{gun_name} {data['description']}: {gun_name}-烽火地带-{data['code']}"
                result += f"  {code_line}\n"
            result += "\n"
        else:
            result += "🔥 烽火地带: 暂无数据\n\n"
        
        # Battlefield 数据
        battlefield_codes = self.datamanager.get_gun_codes(gun_name, "battlefield")
        if battlefield_codes:
            result += "⚔️ 全面战场 改枪码:\n"
            for level, data in battlefield_codes:
                # 按照新格式：枪名 描述: 枪名-全面战场-代码
                code_line = f"{gun_name} {data['description']}: {gun_name}-全面战场-{data['code']}"
                result += f"  {code_line}\n"
        else:
            result += "⚔️ 全面战场: 暂无数据"
        
        messages = []
        if event.get_platform_name() == "aiocqhttp":
            messages.append(Comp.At(qq=event.get_sender_id()))
        messages.append(Comp.Plain(result))
        yield event.chain_result(messages)

    @filter.command("改枪码管理")
    async def guncode_manage(self, event: AstrMessageEvent, subcommand: str = None, arg1: str = None, arg2: str = None, arg3: str = None):
        """管理改枪码"""
        if event.get_sender_id() not in self.admin_list:
            messages = []
            if event.get_platform_name() == "aiocqhttp":
                messages.append(Comp.At(qq=event.get_sender_id()))
            messages.append(Comp.Plain("❌你没有权限使用此命令！"))
            yield event.chain_result(messages)
            return
        
        if subcommand is None:
            help_text = (
                "🔧 Yun's改枪码管理命令:\n"
                "• 添加枪械: /改枪码管理 添加枪械 <枪名>\n"
                "• 删除枪械: /改枪码管理 删除枪械 <枪名>\n"
                "• 添加代码: /改枪码管理 添加代码 <枪名> <firezone|battlefield> <等级> <代码> <描述> [价格]\n"
                "• 删除代码: /改枪码管理 删除代码 <枪名> <firezone|battlefield> <等级>\n"
                "• 查看枪械: /改枪码管理 查看枪械 [枪名]\n"
                "• 枪械列表: /改枪码管理 枪械列表\n"
                "• 搜索枪械: /改枪码管理 搜索 <关键词>"
            )
            yield event.plain_result(help_text)
            return

        match subcommand:
            case "添加枪械":
                async for result in self._add_gun(event, arg1):
                    yield result
            case "删除枪械":
                async for result in self._delete_gun(event, arg1):
                    yield result
            case "添加代码":
                async for result in self._add_code(event, arg1, arg2, arg3):
                    yield result
            case "删除代码":
                async for result in self._delete_code(event, arg1, arg2, arg3):
                    yield result
            case "查看枪械":
                async for result in self._view_gun(event, arg1):
                    yield result
            case "枪械列表":
                async for result in self._list_guns(event):
                    yield result
            case "搜索":
                async for result in self._search_guns(event, arg1):
                    yield result
            case _:
                messages = []
                if event.get_platform_name() == "aiocqhttp":
                    messages.append(Comp.At(qq=event.get_sender_id()))
                messages.append(Comp.Plain("❌无效的子命令！使用 '/改枪码管理' 查看可用命令"))
                yield event.chain_result(messages)

    @filter.command("每日密码", alias=["dailycode", "密码"])
    async def daily_password(self, event: AstrMessageEvent):
        """获取三角洲行动每日密码"""
        messages = []
        
        try:
            # 显示处理中消息
            if event.get_platform_name() == "aiocqhttp":
                messages.append(Comp.At(qq=event.get_sender_id()))
            messages.append(Comp.Plain("欢迎使用Yuns三角洲插件~"))
            messages.append(Comp.Plain("🔄 正在从ACGICE网站获取每日密码，请稍候..."))
            yield event.chain_result(messages)
            messages = []  # 清空消息列表
            
            # 获取截图
            screenshot_path = await self._get_daily_password_screenshot()
            
            if screenshot_path and screenshot_path.exists():
                # 构建图片消息
                if event.get_platform_name() == "aiocqhttp":
                    # QQ平台使用Image组件
                    from astrbot.api.message_components import Image
                    messages.append(Comp.At(qq=event.get_sender_id()))
                    messages.append(Image(file=str(screenshot_path)))
                    messages.append(Comp.Plain("🎯 三角洲行动 - 今日地图密码"))
                else:
                    messages.append(Comp.Plain("🎯 三角洲行动 - 今日地图密码"))
                    messages.append(Comp.Image(file=str(screenshot_path)))
                yield event.chain_result(messages)
            else:
                if event.get_platform_name() == "aiocqhttp":
                    messages.append(Comp.At(qq=event.get_sender_id()))
                messages.append(Comp.Plain("❌ 获取每日密码失败，请稍后重试"))
                yield event.chain_result(messages)
                
        except Exception as e:
            logger.error(f"获取每日密码时发生错误: {e}")
            messages = []
            if event.get_platform_name() == "aiocqhttp":
                messages.append(Comp.At(qq=event.get_sender_id()))
            messages.append(Comp.Plain("❌ 获取每日密码时发生错误，请稍后重试"))
            yield event.chain_result(messages)

    async def _get_daily_password_screenshot(self) -> Path:
        """
        使用 Playwright 获取每日密码截图
        
        Returns:
            截图文件路径
        """
        screenshot_path = self.screenshot_dir / "daily_password.png"
        
        async with async_playwright() as p:
            try:
                # 启动浏览器，使用中文语言环境
                browser = await p.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-dev-shm-usage', '--lang=zh-CN']
                )
                
                # 创建上下文，设置中文语言和用户代理
                context = await browser.new_context(
                    locale='zh-CN',
                    timezone_id='Asia/Shanghai',
                    viewport={'width': 1200, 'height': 800},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                )
                
                # 创建页面
                page = await context.new_page()
                
                # 设置超时时间
                page.set_default_timeout(30000)
                
                # 导航到目标页面
                logger.info("正在导航到目标页面...")
                await page.goto('https://www.acgice.com/sjz/', wait_until='networkidle')
                
                # 等待页面加载完成
                await page.wait_for_timeout(3000)
                
                # 等待目标元素加载
                logger.info("等待目标元素加载...")
                await page.wait_for_selector('.stats.bg-base-500', timeout=15000)
                
                # 定位到指定的元素
                target_element = await page.query_selector('.stats.bg-base-500')
                
                if target_element:
                    # 截图指定元素
                    logger.info("正在截图...")
                    await target_element.screenshot(path=str(screenshot_path))
                    logger.info(f"截图保存到: {screenshot_path}")
                else:
                    logger.error("未找到目标元素")
                    screenshot_path = None
                
                # 关闭浏览器
                await browser.close()
                
                return screenshot_path
                
            except Exception as e:
                logger.error(f"截图过程中发生错误: {e}")
                try:
                    await browser.close()
                except:
                    pass
                return None

    # 可选：添加缓存机制，避免频繁请求
    async def _get_daily_password_with_cache(self) -> Path:
        """
        带缓存的获取每日密码截图
        
        Returns:
            截图文件路径
        """
        screenshot_path = self.screenshot_dir / "daily_password.png"
        
        # 检查缓存是否有效（1小时内）
        if screenshot_path.exists():
            import time
            file_age = time.time() - screenshot_path.stat().st_mtime
            if file_age < 3600:  # 1小时缓存
                logger.info("使用缓存的截图")
                return screenshot_path
        
        # 重新获取截图
        return await self._get_daily_password_screenshot()

    async def _add_gun(self, event: AstrMessageEvent, gun_name: str):
        """添加枪械"""
        if not gun_name:
            yield event.plain_result("❌请提供枪械名称")
            return
        
        if self.datamanager.add_gun(gun_name):
            yield event.plain_result(f"✅成功添加枪械: {gun_name}")
        else:
            yield event.plain_result(f"❌添加枪械失败: {gun_name} 可能已存在")

    async def _delete_gun(self, event: AstrMessageEvent, gun_name: str):
        """删除枪械"""
        if not gun_name:
            yield event.plain_result("❌请提供枪械名称")
            return
        
        if self.datamanager.delete_gun(gun_name):
            yield event.plain_result(f"✅成功删除枪械: {gun_name}")
        else:
            yield event.plain_result(f"❌删除枪械失败: {gun_name} 不存在")

    async def _add_code(self, event: AstrMessageEvent, gun_name: str, field_type: str, args: str):
        """添加代码"""
        if not all([gun_name, field_type, args]):
            yield event.plain_result("❌参数不足！格式: /改枪码管理 添加代码 <枪名> <firezone|battlefield> <等级> <代码> <描述> [价格]")
            return
        
        try:
            args_list = args.split(' ', 3)  # 最多分割4部分
            if len(args_list) < 3:
                raise ValueError("参数不足")
            
            level = int(args_list[0])
            code = args_list[1]
            description = args_list[2]
            price = int(args_list[3]) if len(args_list) > 3 and field_type == "firezone" else None
            
            if field_type not in ["firezone", "battlefield"]:
                yield event.plain_result("❌字段类型必须是 'firezone' 或 'battlefield'")
                return
            
            # 对于firezone必须提供价格
            if field_type == "firezone" and price is None:
                yield event.plain_result("❌firezone类型必须提供价格参数")
                return
            
            if self.datamanager.add_field_data(gun_name, field_type, level, code, description, price):
                # 显示添加后的完整格式
                field_name = "烽火地带" if field_type == "firezone" else "全面战场"
                code_line = f"{gun_name} {description}: {gun_name}-{field_name}-{code}"
                yield event.plain_result(f"✅成功添加代码:\n{code_line}")
            else:
                yield event.plain_result(f"❌添加代码失败，请检查枪械名称和参数")
                
        except (ValueError, IndexError) as e:
            yield event.plain_result("❌参数格式错误！正确格式: /改枪码管理 添加代码 <枪名> <firezone|battlefield> <等级> <代码> <描述> [价格]")

    async def _delete_code(self, event: AstrMessageEvent, gun_name: str, field_type: str, level_str: str):
        """删除代码"""
        if not all([gun_name, field_type, level_str]):
            yield event.plain_result("❌参数不足！格式: /改枪码管理 删除代码 <枪名> <firezone|battlefield> <等级>")
            return
        
        try:
            level = int(level_str)
            if field_type not in ["firezone", "battlefield"]:
                yield event.plain_result("❌字段类型必须是 'firezone' 或 'battlefield'")
                return
            
            # 先获取要删除的数据信息
            field_data = self.datamanager.get_field_data(gun_name, field_type, level)
            if not field_data:
                yield event.plain_result(f"❌要删除的代码不存在")
                return
            
            if self.datamanager.delete_field_data(gun_name, field_type, level):
                field_name = "烽火地带" if field_type == "firezone" else "全面战场"
                code_line = f"{gun_name} {field_data['description']}: {gun_name}-{field_name}-{field_data['code']}"
                yield event.plain_result(f"✅成功删除代码:\n{code_line}")
            else:
                yield event.plain_result(f"❌删除代码失败，请检查枪械名称和等级")
                
        except ValueError:
            yield event.plain_result("❌等级必须是数字")

    async def _view_gun(self, event: AstrMessageEvent, gun_name: str = None):
        """查看枪械详情"""
        if gun_name:
            # 查看特定枪械
            async for result in self._display_gun_codes(event, gun_name):
                yield result
        else:
            # 查看所有枪械列表
            async for result in self._list_guns(event):
                yield result

    async def _list_guns(self, event: AstrMessageEvent):
        """列出所有枪械"""
        guns = self.datamanager.get_gun_list()
        if not guns:
            yield event.plain_result("❌暂无枪械数据")
            return
        
        result = "🔫 所有枪械列表:\n"
        for i, gun_name in enumerate(guns, 1):
            gun_data = self.datamanager.get_gun(gun_name)
            firezone_count = len(gun_data.get("firezone", {}))
            battlefield_count = len(gun_data.get("battlefield", {}))
            result += f"{i}. {gun_name} (🔥{firezone_count} ⚔️{battlefield_count})\n"
        
        yield event.plain_result(result)

    async def _search_guns(self, event: AstrMessageEvent, keyword: str):
        """搜索枪械"""
        if not keyword:
            yield event.plain_result("❌请提供搜索关键词")
            return
        
        found_guns = self.datamanager.search_guns(keyword)
        if not found_guns:
            yield event.plain_result(f"❌未找到包含 '{keyword}' 的枪械")
            return
        
        result = f"🔍 搜索 '{keyword}' 结果:\n"
        for i, gun_name in enumerate(found_guns, 1):
            result += f"{i}. {gun_name}\n"
        
        yield event.plain_result(result)

    @filter.command("改枪码帮助")
    async def guncode_help(self, event: AstrMessageEvent):
        """改枪码帮助"""
        help_text = (
            "🎯 Yun's 改枪码插件使用帮助：\n"
            "普通用户命令:\n"
            "• /改枪码 <枪名> - 查询枪械改枪码\n"
            "• /选择 <id> - 选择查询结果中的枪械\n"
            "• /取消 - 取消当前选择\n"
            "• /改枪码帮助 - 显示此帮助\n\n"
            "管理员命令:\n"
            "• /改枪码管理 - 显示管理命令帮助\n"
            "• /改枪码管理 添加枪械 <枪名>\n"
            "• /改枪码管理 删除枪械 <枪名>\n"
            "• /改枪码管理 添加代码 <枪名> <firezone|battlefield> <等级> <代码> <描述> [价格]\n"
            "• /改枪码管理 删除代码 <枪名> <firezone|battlefield> <等级>\n"
            "• /改枪码管理 查看枪械 [枪名]\n"
            "• /改枪码管理 枪械列表\n"
            "• /改枪码管理 搜索 <关键词>"
        )
        yield event.plain_result(help_text)

    # 用户临时数据管理方法
    def _set_user_temp_data(self, user_id: str, group_id: str, data):
        """设置用户临时数据"""
        key = f"{user_id}_{group_id}"
        self.user_temp_data[key] = data

    def _get_user_temp_data(self, user_id: str, group_id: str):
        """获取用户临时数据"""
        key = f"{user_id}_{group_id}"
        return self.user_temp_data.get(key)

    def _clear_user_temp_data(self, user_id: str, group_id: str):
        """清除用户临时数据"""
        key = f"{user_id}_{group_id}"
        if key in self.user_temp_data:
            del self.user_temp_data[key]

    async def terminate(self):
        """插件销毁"""
        self.user_temp_data.clear()
        import time
        current_time = time.time()
        for file in self.screenshot_dir.glob("*.png"):
            if current_time - file.stat().st_mtime > 86400:
                file.unlink()
        logger.info("改枪码插件已卸载")