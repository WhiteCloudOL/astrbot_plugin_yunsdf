from astrbot.api.star import StarTools
from astrbot.api import logger
import json
import os
from typing import Dict, List, Optional, Union, Tuple

class DataManager:
    """
    数据管理器类，负责改枪码的存储与管理
    使用 JSON 文件进行持久化存储

    Data Structure:
    {
        "guns": {
            "AK47": {
                "name": "AK47",
                "firezone": {
                    "1": {
                        "price": 150000,
                        "code": "AK47_FZ_001",
                        "description": "基础火力升级"
                    },
                    "2": {
                        "price": 200000,
                        "code": "AK47_FZ_002", 
                        "description": "高级火力升级"
                    }
                },
                "battlefield": {
                    "1": {
                        "code": "AK47_BF_001",
                        "description": "战场适应性提升"
                    }
                }
            },
            "M4A1": {
                "name": "M4A1",
                "firezone": {
                    "1": {
                        "price": 120000,
                        "code": "M4A1_FZ_001",
                        "description": "精准射击升级"
                    }
                },
                "battlefield": {}
            }
        }
    }
    """

    def __init__(self, data_file: str = StarTools.get_data_dir("yunsdf")/"gun_data.json"):
        """
        初始化数据管理器
        
        Args:
            data_file: 数据文件路径
        """
        self.data_file = data_file
        self.data = self._load_data()
        self._ensure_data_structure()
    
    def _ensure_data_structure(self):
        """确保数据结构正确"""
        if "guns" not in self.data:
            self.data["guns"] = {}
        self._save_data()
    
    def _load_data(self) -> Dict:
        """
        从文件加载数据，如果数据文件不存在则尝试从模板创建
        
        Returns:
            加载的数据字典
        """
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError) as e:
                logger.error(f"加载数据文件失败: {e}")
                return {}
        
        # 数据文件不存在，尝试从模板文件创建
        return self._create_from_template()
    
    def _create_from_template(self) -> Dict:
        """
        从模板文件创建数据文件
        
        Returns:
            创建的数据字典
        """
        data_dir = os.path.dirname(self.data_file) or '.'
        
        template_file = os.path.join(os.path.dirname(__file__), '..', 'template', 'default_gun_code.json')
        
        template_data = {"guns": {}}
        
        # 尝试从模板文件加载
        if os.path.exists(template_file):
            try:
                with open(template_file, 'r', encoding='utf-8') as f:
                    template_data = json.load(f)
                logger.info(f"从模板文件 {template_file} 创建数据文件")
            except (json.JSONDecodeError, FileNotFoundError) as e:
                logger.warning(f"模板文件加载失败: {e}，将创建空数据文件")
        else:
            logger.info("模板文件不存在，将创建空数据文件")
        
        os.makedirs(os.path.dirname(self.data_file) or '.', exist_ok=True)
        
        # 保存数据到目标文件
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(template_data, f, ensure_ascii=False, indent=4)
            logger.info(f"已创建数据文件: {self.data_file}")
        except Exception as e:
            logger.error(f"创建数据文件失败: {e}")
        
        return template_data
    
    def _save_data(self) -> None:
        """
        保存数据到文件
        """
        os.makedirs(os.path.dirname(self.data_file) or '.', exist_ok=True)
        
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            logger.error(f"保存数据失败: {e}")
            raise

    def get_gun_codes(self, gun_name: str, field_type: str, sort_by_price: bool = False) -> List[Tuple[int, Dict]]:
        """
        根据枪名获取firezone或battlefield的guncode
        
        Args:
            gun_name: 枪械名称
            field_type: 字段类型 ('firezone' 或 'battlefield')
            sort_by_price: 是否按价格排序（仅对firezone有效）
            
        Returns:
            包含等级和数据的元组列表 [(level, data), ...]
        """
        gun = self.get_gun(gun_name)
        if not gun or field_type not in gun:
            logger.warning(f"获取枪械代码失败: 枪械 {gun_name} 或字段类型 {field_type} 不存在")
            return []
        
        field_data = gun[field_type]
        if not field_data:
            logger.info(f"枪械 {gun_name} 的 {field_type} 字段没有数据")
            return []
        
        result = [(int(level), data) for level, data in field_data.items()]
        
        # 如果是firezone且需要按价格排序
        if field_type == "firezone" and sort_by_price:
            result.sort(key=lambda x: x[1].get("price", 0))
            logger.info(f"已按价格排序获取 {gun_name} 的 {field_type} 代码")
        else:
            result.sort(key=lambda x: x[0])
            logger.info(f"已按等级排序获取 {gun_name} 的 {field_type} 代码")
        
        return result

    def get_gun_codes_simple(self, gun_name: str, field_type: str, sort_by_price: bool = False) -> List[Dict]:
        """
        简化版：获取枪械代码列表（不包含等级信息）
        
        Args:
            gun_name: 枪械名称
            field_type: 字段类型
            sort_by_price: 是否按价格排序
            
        Returns:
            数据字典列表
        """
        codes_with_level = self.get_gun_codes(gun_name, field_type, sort_by_price)
        return [data for level, data in codes_with_level]

    def add_gun(self, gun_name: str) -> bool:
        """
        添加枪械
        
        Args:
            gun_name: 枪械名称
            
        Returns:
            是否添加成功
        """
        if gun_name in self.data["guns"]:
            logger.warning(f"枪械 {gun_name} 已存在，添加失败")
            return False
        
        self.data["guns"][gun_name] = {
            "name": gun_name,
            "firezone": {},
            "battlefield": {}
        }
        self._save_data()
        logger.info(f"成功添加枪械: {gun_name}")
        return True
    
    def delete_gun(self, gun_name: str) -> bool:
        """
        删除枪械
        
        Args:
            gun_name: 枪械名称
            
        Returns:
            是否删除成功
        """
        if gun_name in self.data["guns"]:
            del self.data["guns"][gun_name]
            self._save_data()
            logger.info(f"成功删除枪械: {gun_name}")
            return True
        
        logger.warning(f"枪械 {gun_name} 不存在，删除失败")
        return False
    
    def update_gun_name(self, old_name: str, new_name: str) -> bool:
        """
        更新枪械名称
        
        Args:
            old_name: 原名称
            new_name: 新名称
            
        Returns:
            是否更新成功
        """
        if old_name in self.data["guns"] and new_name not in self.data["guns"]:
            gun_data = self.data["guns"].pop(old_name)
            gun_data["name"] = new_name
            self.data["guns"][new_name] = gun_data
            self._save_data()
            logger.info(f"成功更新枪械名称: {old_name} -> {new_name}")
            return True
        
        logger.warning(f"枪械名称更新失败: {old_name} -> {new_name}")
        return False
    
    def get_gun(self, gun_name: str) -> Optional[Dict]:
        """
        获取枪械信息
        
        Args:
            gun_name: 枪械名称
            
        Returns:
            枪械数据或None
        """
        return self.data["guns"].get(gun_name)
    
    def add_field_data(self, gun_name: str, field_type: str, level: int, 
                      code: str, description: str, price: Optional[int] = None) -> bool:
        """
        添加字段数据
        
        Args:
            gun_name: 枪械名称
            field_type: 字段类型 ('firezone' 或 'battlefield')
            level: 等级
            code: 代码
            description: 描述
            price: 价格 (仅firezone需要)
            
        Returns:
            是否添加成功
        """
        if gun_name not in self.data["guns"] or field_type not in ['firezone', 'battlefield']:
            logger.warning(f"添加字段数据失败: 枪械 {gun_name} 或字段类型 {field_type} 不存在")
            return False
        
        field_data = {
            "code": code,
            "description": description
        }
        
        if field_type == "firezone":
            if price is None:
                logger.warning("firezone 类型必须提供 price 参数")
                return False
            field_data["price"] = price
        
        self.data["guns"][gun_name][field_type][str(level)] = field_data
        self._save_data()
        logger.info(f"成功为枪械 {gun_name} 添加 {field_type} 等级 {level} 的数据")
        return True
    
    def delete_field_data(self, gun_name: str, field_type: str, level: int) -> bool:
        """
        删除字段数据
        
        Args:
            gun_name: 枪械名称
            field_type: 字段类型
            level: 等级
            
        Returns:
            是否删除成功
        """
        gun = self.get_gun(gun_name)
        if gun and field_type in gun and str(level) in gun[field_type]:
            del gun[field_type][str(level)]
            self._save_data()
            logger.info(f"成功删除枪械 {gun_name} 的 {field_type} 等级 {level} 数据")
            return True
        
        logger.warning(f"删除字段数据失败: 枪械 {gun_name} 的 {field_type} 等级 {level} 不存在")
        return False
    
    def update_field_data(self, gun_name: str, field_type: str, level: int, 
                         code: Optional[str] = None, description: Optional[str] = None,
                         price: Optional[int] = None) -> bool:
        """
        更新字段数据
        
        Args:
            gun_name: 枪械名称
            field_type: 字段类型
            level: 等级
            code: 新代码
            description: 新描述
            price: 新价格
            
        Returns:
            是否更新成功
        """
        gun = self.get_gun(gun_name)
        if not gun or field_type not in gun or str(level) not in gun[field_type]:
            logger.warning(f"更新字段数据失败: 枪械 {gun_name} 的 {field_type} 等级 {level} 不存在")
            return False
        
        field_data = gun[field_type][str(level)]
        
        if code is not None:
            field_data["code"] = code
        if description is not None:
            field_data["description"] = description
        if price is not None and field_type == "firezone":
            field_data["price"] = price
        
        self._save_data()
        logger.info(f"成功更新枪械 {gun_name} 的 {field_type} 等级 {level} 数据")
        return True
    
    def get_field_data(self, gun_name: str, field_type: str, level: int) -> Optional[Dict]:
        """
        获取字段数据
        
        Args:
            gun_name: 枪械名称
            field_type: 字段类型
            level: 等级
            
        Returns:
            字段数据或None
        """
        gun = self.get_gun(gun_name)
        if gun and field_type in gun:
            return gun[field_type].get(str(level))
        return None
    
    def get_gun_list(self) -> List[str]:
        """
        获取所有枪械名称列表
        
        Returns:
            枪械名称列表
        """
        return list(self.data["guns"].keys())
    
    def search_guns(self, keyword: str) -> List[str]:
        """
        根据关键词模糊查找枪名
        
        Args:
            keyword: 关键词
            
        Returns:
            匹配的枪械名称列表
        """
        keyword_lower = keyword.lower()
        result = [gun_name for gun_name in self.data["guns"].keys() 
                 if keyword_lower in gun_name.lower()]
        logger.info(f"关键词 '{keyword}' 搜索到 {len(result)} 个结果")
        return result

    def get_gun_field_data(self, gun_name: str, field_type: str) -> Optional[Dict]:
        """
        获取枪械指定字段的所有数据
        
        Args:
            gun_name: 枪械名称
            field_type: 字段类型
            
        Returns:
            字段数据字典或None
        """
        gun = self.get_gun(gun_name)
        return gun.get(field_type) if gun else None
    
    def gun_exists(self, gun_name: str) -> bool:
        """
        检查枪械是否存在
        
        Args:
            gun_name: 枪械名称
            
        Returns:
            是否存在
        """
        return gun_name in self.data["guns"]
    
    def get_all_data(self) -> Dict:
        """
        获取所有数据
        
        Returns:
            完整数据字典
        """
        return self.data.copy()

    # 保留原有的模板相关方法
    def recreate_from_template(self) -> bool:
        """
        重新从模板文件创建数据文件（会覆盖现有数据）
        
        Returns:
            是否创建成功
        """
        try:
            if os.path.exists(self.data_file):
                os.remove(self.data_file)
                logger.info(f"已删除现有数据文件: {self.data_file}")
            
            self.data = self._create_from_template()
            logger.info("从模板重新创建数据文件成功")
            return True
        except Exception as e:
            logger.error(f"从模板重新创建失败: {e}")
            return False
    
    def get_template_path(self) -> str:
        """
        获取模板文件路径
        
        Returns:
            模板文件路径
        """
        data_dir = os.path.dirname(self.data_file) or '.'
        return os.path.join(data_dir, "template", "default_gun_code.json")
    
    def template_exists(self) -> bool:
        """
        检查模板文件是否存在
        
        Returns:
            模板文件是否存在
        """
        return os.path.exists(self.get_template_path())