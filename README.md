# Astrbot Plugin Yun's DeltaForce

AstrBot Plugin for DeltaForce

# 功能/Function  
1. 默认自带改枪码  
2. 支持自定义添加改枪码  

# 安装/Install  

### 自动安装  
Astrbot插件市场搜索 yunsdf 即可自动下载  
此外，需要确保安装playwright
默认情况下pip会自动下载playwright包，但是需要手动安装，请进入python虚拟环境，输入以下命令：  
```bash
    playwright install
```

### 手动安装  
1. 方式一：直接下载：  
点击右上角`<>Code`->`Download Zip`下载压缩包  
打开`Astrbot/data/plugins/`下载本仓库文件，创建`astrbot_plugin_guncode`目录，解压所有文件到此目录即可  
2. 方式二：Git Clone方法  
请确保系统已经安装git  
打开目录`Astrbot/data/plugins/`，在此目录下启动终端执行:  
```bash
# 全球/海外/港澳台
git clone https://github.com/WhiteCloudOL/astrbot_plugin_guncode.git  

# 大陆地区#1
git clone https://gh-proxy.com/https://github.com/WhiteCloudOL/astrbot_plugin_guncode.git  

# 大陆地区#2
git clone https://cdn.gh-proxy.com/https://github.com/WhiteCloudOL/astrbot_plugin_guncode.git  
```
以上命令任选其一执行即可  

*下载完成后*  
默认情况下pip会自动下载playwright包，但是需要手动安装，请进入python虚拟环境，输入以下命令：  
```bash
    playwright install
```

**Playwright安装失败**  
1. 缺少依赖`Playwright Host validation warning`，请在虚拟环境下执行命令，下载依赖包：  
```bash
python -m playwright install-deps   # windows

python3 -m playwright install-deps  # linux
```

# 使用/Usage  
### 命令  
  🎯 Yun's 三角洲使用帮助：   
    普通用户命令:    
     • /改枪码 <枪名> - 查询枪械改枪码  
     • /每日密码 - 从ACGICE获取每日密码  
     • /改枪码帮助 - 显示帮助  
    管理员命令:  
     • /改枪码管理 - 显示管理命令帮助  
     • /改枪码管理 添加枪械 <枪名>  
     • /改枪码管理 删除枪械 <枪名>  
     • /改枪码管理 添加代码 <枪名> <烽火地带|全面战场> <代码> <描述> [价格]  
     • /改枪码管理 删除代码 <枪名> <烽火地带|全面战场> <序号>  
     • /改枪码管理 查看枪械 [枪名]  
     • /改枪码管理 枪械列表  
     • /改枪码管理 搜索 <关键词>  

# 配置/Configure
1. 配置管理员：  
   从Astrbot本体配置机器人管理员 或 插件配置-管理员列表 均可添加管理员，本插件支持混合机器人管理员和插件管理员数据~

# 支持、鸣谢
1. Astrbot - 多平台大模型机器人基础设施  
[Astrbot帮助文档](https://astrbot.app)  
2. ACGICE[三角洲小涛查](https://www.acgice.com/) - 部分数据来源  