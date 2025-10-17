from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register, StarTools
from astrbot.api import logger, AstrBotConfig
import astrbot.api.message_components as Comp
from astrbot.api.message_components import Image
from pathlib import Path
from playwright.async_api import async_playwright
import asyncio
import time

from .data_manager import DataManager

@register("yunsdf", "清蒸云鸭", "三角洲改枪码、每日密码等查询插件，支持自定义添加，JSON持久化", "1.0.0")
class MyPlugin(Star):
    def __init__(self, context: Context,config: AstrBotConfig):
        super().__init__(context)
        self.data_path = StarTools.get_data_dir("yunsdf")
        self.bot_config = context.get_config()
        bot_admins = self.bot_config.get("admins_id", [])
        plugin_admins = config.get("admins", [])
        
        # 合并管理员列表
        if not plugin_admins:
            self.admin_list = bot_admins
        else:
            self.admin_list = list(set(bot_admins + plugin_admins))

        self.datamanager = DataManager(data_file=self.data_path/"gun_data.json")
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
            gun_name = found_guns[0]
            async for result in self._display_gun_codes(event, gun_name):
                yield result
            return
        
        if event.get_platform_name() in ("aiocqhttp", "webchat"):
            res = f"找到 {gun_num} 个匹配的枪械：\n"
            res += "| id | 枪名 |\n"
            for i in range(gun_num):
                res += f"{i+1}. {found_guns[i]}\n"
            res += "\n请执行命令 /选择 id ，否则请输入 /取消"
            
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
        
        result = f"欢迎使用Yun's三角洲插件~\n🔫 枪械: {gun_name}\n\n"
        
        firezone_codes = self.datamanager.get_gun_codes(gun_name, "firezone", sort_by_price=True)
        if firezone_codes:
            result += "🔥 烽火地带 改枪码:\n"
            for level, data in firezone_codes:
                price = data.get('price', 0)
                price_text = f"{price/10000:.1f}万" if price >= 10000 else f"{price}元"
                if "丐版" in data['description'] or "基础" in data['description']:
                    price_text = f"{price_text}丐版"
                
                # 枪名 描述: 枪名-烽火地带-代码
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
                # 枪名 描述: 枪名-全面战场-代码
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
                "• 添加代码: /改枪码管理 添加代码 <枪名> <烽火地带|全面战场> <代码> <描述> [价格]\n"
                "• 删除代码: /改枪码管理 删除代码 <枪名> <烽火地带|全面战场> <序号>\n"
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

    async def _add_code(self, event: AstrMessageEvent, gun_name: str, field_type_cn: str, args: str):
        """添加代码 - 自动生成序号，使用中文类型"""
        if not all([gun_name, field_type_cn, args]):
            yield event.plain_result("❌参数不足！格式: /改枪码管理 添加代码 <枪名> <烽火地带|全面战场> <代码> <描述> [价格]")
            return
        
        try:
            args_list = args.split(' ', 2)
            if len(args_list) < 2:
                raise ValueError("参数不足")
            
            code = args_list[0]
            description = args_list[1]
            price = int(args_list[2]) if len(args_list) > 2 and field_type_cn == "烽火地带" else None
            
            if field_type_cn == "烽火地带":
                field_type = "firezone"
            elif field_type_cn == "全面战场":
                field_type = "battlefield"
            else:
                yield event.plain_result("❌字段类型必须是 '烽火地带' 或 '全面战场'")
                return
            
            if field_type == "firezone" and price is None:
                yield event.plain_result("❌烽火地带类型必须提供价格参数")
                return
            
            # 自动生成序号（获取当前最大序号+1）
            gun_data = self.datamanager.get_gun(gun_name)
            if not gun_data:
                yield event.plain_result(f"❌枪械 '{gun_name}' 不存在，请先添加枪械")
                return
            
            existing_codes = gun_data.get(field_type, {})
            if existing_codes:
                max_level = max(int(level) for level in existing_codes.keys())
                level = max_level + 1
            else:
                level = 1
            
            if self.datamanager.add_field_data(gun_name, field_type, level, code, description, price):
                code_line = f"{gun_name} {description}: {gun_name}-{field_type_cn}-{code}"
                yield event.plain_result(f"✅成功添加代码 (序号{level}):\n{code_line}")
            else:
                yield event.plain_result(f"❌添加代码失败，请检查枪械名称和参数")
                
        except (ValueError, IndexError) as e:
            logger.error(f"添加代码参数错误: {e}")
            yield event.plain_result("❌参数格式错误！正确格式: /改枪码管理 添加代码 <枪名> <烽火地带|全面战场> <代码> <描述> [价格]")

    async def _delete_code(self, event: AstrMessageEvent, gun_name: str, field_type_cn: str, level_str: str):
        """删除代码 - 使用中文类型"""
        if not all([gun_name, field_type_cn, level_str]):
            yield event.plain_result("❌参数不足！格式: /改枪码管理 删除代码 <枪名> <烽火地带|全面战场> <序号>")
            return
        
        try:
            level = int(level_str)
            
            # 转换中文类型为英文
            if field_type_cn == "烽火地带":
                field_type = "firezone"
            elif field_type_cn == "全面战场":
                field_type = "battlefield"
            else:
                yield event.plain_result("❌字段类型必须是 '烽火地带' 或 '全面战场'")
                return
            
            field_data = self.datamanager.get_field_data(gun_name, field_type, level)
            if not field_data:
                yield event.plain_result(f"❌要删除的代码不存在")
                return
            
            if self.datamanager.delete_field_data(gun_name, field_type, level):
                code_line = f"{gun_name} {field_data['description']}: {gun_name}-{field_type_cn}-{field_data['code']}"
                yield event.plain_result(f"✅成功删除代码 (序号{level}):\n{code_line}")
            else:
                yield event.plain_result(f"❌删除代码失败，请检查枪械名称和序号")
                
        except ValueError:
            yield event.plain_result("❌序号必须是数字")

    @filter.command("每日密码", alias=["dailycode", "密码","今日密码"])
    async def daily_password(self, event: AstrMessageEvent):
        """获取三角洲行动每日密码"""
        messages = []
        
        try:
            if event.get_platform_name() == "aiocqhttp":
                messages.append(Comp.At(qq=event.get_sender_id()))
            messages.append(Comp.Plain(" 欢迎使用Yuns三角洲插件~\n"))
            messages.append(Comp.Plain("🔄 正在从ACGICE网站获取每日密码，请稍候...\n"))
            yield event.chain_result(messages)
            messages = []
            
            # 使用带重试的版本
            screenshot_path = await self._get_daily_password_with_retry()
            
            if screenshot_path and screenshot_path.exists():
                if event.get_platform_name() == "aiocqhttp":
                    messages.append(Comp.At(qq=event.get_sender_id()))
                messages.append(Comp.Plain("🎯 今日地图密码"))
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

    async def _get_daily_password_with_retry(self, max_retries: int = 3) -> Path:
        """带重试机制的获取每日密码截图"""
        cached_path = await self._check_screenshot_cache()
        if cached_path:
            return cached_path
        
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                logger.info(f"尝试获取每日密码截图 (第 {attempt + 1}/{max_retries} 次)")
                
                screenshot_path = await self._get_daily_password_screenshot(attempt)
                
                if screenshot_path and screenshot_path.exists():
                    logger.info(f"✅ 第 {attempt + 1} 次尝试成功")
                    return screenshot_path
                else:
                    logger.warning(f"❌ 第 {attempt + 1} 次尝试失败: 截图文件未生成")
                    
            except Exception as e:
                last_exception = e
                logger.warning(f"❌ 第 {attempt + 1} 次尝试失败: {str(e)}")
                
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2
                    logger.info(f"等待 {wait_time} 秒后重试...")
                    await asyncio.sleep(wait_time)
        
        logger.error(f"所有 {max_retries} 次尝试均失败，最后错误: {last_exception}")
        return None

    async def _get_daily_password_screenshot(self, attempt: int = 0) -> Path:
        """使用 Playwright 获取每日密码截图"""
        screenshot_path = self.screenshot_dir / "daily_password.png"
        
        # 根据尝试次数调整超时时间
        timeout_multiplier = 1 + (attempt * 0.5)
        
        async with async_playwright() as p:
            browser = None
            try:
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        '--no-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-gpu',
                        '--lang=zh-CN'
                    ],
                    timeout=int(30000 * timeout_multiplier)
                )
                
                context = await browser.new_context(
                    locale='zh-CN',
                    timezone_id='Asia/Shanghai',
                    viewport={'width': 1200, 'height': 800},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
                    ignore_https_errors=True,
                )
                
                context.set_default_timeout(int(30000 * timeout_multiplier))
                page = await context.new_page()
                page.set_default_timeout(int(30000 * timeout_multiplier))
                page.set_default_navigation_timeout(int(30000 * timeout_multiplier))
                
                # 导航到目标页面
                logger.info("导航到目标页面...")
                await page.goto(
                    'https://www.acgice.com/sjz/', 
                    wait_until='domcontentloaded',
                    timeout=int(30000 * timeout_multiplier)
                )
                
                # 等待页面稳定
                await asyncio.sleep(2)
                
                # 多种选择器尝试
                selectors_to_try = [
                    '.stats.bg-base-500',
                    '.text-center.stats',
                    '.stats',
                    'div[class*="stats"]',
                ]
                
                target_element = None
                for selector in selectors_to_try:
                    try:
                        logger.info(f"尝试选择器: {selector}")
                        target_element = await page.wait_for_selector(
                            selector, 
                            timeout=int(10000 * timeout_multiplier),
                            state='attached'
                        )
                        if target_element:
                            logger.info(f"成功找到元素: {selector}")
                            break
                    except Exception as e:
                        logger.warning(f"选择器 {selector} 失败: {e}")
                        continue
                
                if not target_element:
                    logger.warning("未找到目标元素，尝试截图整个页面")
                    await page.screenshot(path=str(screenshot_path), full_page=False)
                    logger.info("已截图整个页面作为fallback")
                else:
                    await asyncio.sleep(1)
                    
                    is_visible = await target_element.is_visible()
                    bounding_box = await target_element.bounding_box()
                    
                    if not is_visible or not bounding_box:
                        logger.warning("目标元素不可见或没有尺寸，尝试截图整个页面")
                        await page.screenshot(path=str(screenshot_path), full_page=False)
                    else:
                        logger.info("截图目标元素...")
                        await target_element.screenshot(
                            path=str(screenshot_path),
                            type='png',
                            timeout=int(10000 * timeout_multiplier)
                        )
                        logger.info(f"截图保存到: {screenshot_path}")
                
                # 验证截图文件
                if screenshot_path.exists() and screenshot_path.stat().st_size > 0:
                    logger.info("截图验证成功")
                    return screenshot_path
                else:
                    logger.error("截图文件为空或不存在")
                    return None
                
            except Exception as e:
                logger.error(f"截图过程中发生错误: {e}")
                if screenshot_path.exists():
                    try:
                        screenshot_path.unlink()
                    except:
                        pass
                raise e
                
            finally:
                if browser:
                    try:
                        await browser.close()
                        logger.info("浏览器已关闭")
                    except Exception as e:
                        logger.warning(f"关闭浏览器时发生错误: {e}")

    async def _check_screenshot_cache(self) -> Path:
        """检查截图缓存是否有效"""
        screenshot_path = self.screenshot_dir / "daily_password.png"
        
        if not screenshot_path.exists():
            return None
        
        try:
            file_size = screenshot_path.stat().st_size
            if file_size == 0:
                logger.warning("缓存文件大小为0，重新获取")
                screenshot_path.unlink()
                return None
            
            file_age = time.time() - screenshot_path.stat().st_mtime
            if file_age < 1800:  # 30分钟缓存
                logger.info("使用有效的缓存截图")
                return screenshot_path
            else:
                logger.info("缓存已过期，重新获取")
                screenshot_path.unlink()
                return None
                
        except Exception as e:
            logger.warning(f"检查缓存时发生错误: {e}")
            return None

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

    async def _view_gun(self, event: AstrMessageEvent, gun_name: str = None):
        """查看枪械详情"""
        if gun_name:
            async for result in self._display_gun_codes(event, gun_name):
                yield result
        else:
            async for result in self._list_guns(event):
                yield result

    async def _list_guns(self, event: AstrMessageEvent):
        """列出所有枪械"""
        guns = self.datamanager.get_gun_list()
        if not guns:
            yield event.plain_result("❌暂无枪械数据")
            return
        
        result = "欢迎使用Yun's三角洲插件\n 🔫 所有枪械列表:\n|序号|名称|烽火地带|全面战场\n"
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

    @filter.command("三角洲帮助")
    async def guncode_help(self, event: AstrMessageEvent):
        """改枪码帮助"""
        help_text = (
            "🎯 Yun's 三角洲使用帮助：\n"
            "普通用户命令:\n"
            "• /改枪码 <枪名> - 查询枪械改枪码\n"
            "• /每日密码\n"
            "• /改枪码帮助 - 显示此帮助\n\n"
            "管理员命令:\n"
            "• /改枪码管理 - 显示管理命令帮助\n"
            "• /改枪码管理 添加枪械 <枪名>\n"
            "• /改枪码管理 删除枪械 <枪名>\n"
            "• /改枪码管理 添加代码 <枪名> <烽火地带|全面战场> <代码> <描述> [价格]\n"
            "• /改枪码管理 删除代码 <枪名> <烽火地带|全面战场> <序号>\n"
            "• /改枪码管理 查看枪械 [枪名]\n"
            "• /改枪码管理 枪械列表\n"
            "• /改枪码管理 搜索 <关键词>"
        )
        yield event.plain_result(help_text)

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
        current_time = time.time()
        for file in self.screenshot_dir.glob("*.png"):
            if current_time - file.stat().st_mtime > 86400:
                file.unlink()
        logger.info("改枪码插件已卸载")