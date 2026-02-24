#!/usr/bin/python
# coding: utf-8
# +-------------------------------------------------------------------
# | 宝塔Linux面板 - 自定义字体插件 v1.2
# +-------------------------------------------------------------------
# | Copyright (c) 2015-2099 宝塔软件(http://bt.cn) All rights reserved.
# +-------------------------------------------------------------------
# | Author: BT-Plugin
# +-------------------------------------------------------------------

#+--------------------------------------------------------------------
#|   面板自定义字体插件 - 支持上传自定义字体更改面板显示字体
#|   v1.2: 修复全局字体应用问题，使用更高优先级CSS注入
#+--------------------------------------------------------------------
import sys,os,json,shutil,hashlib,uuid,re
from datetime import datetime

#设置运行目录
os.chdir("/www/server/panel")

#添加包引用位置并引用公共包
sys.path.append("class/")
import public

#在非命令行模式下引用面板缓存和session对象
if __name__ != '__main__':
    from BTPanel import cache,session,redirect

class customfont_main:
    __plugin_path = "/www/server/panel/plugin/customfont/"
    __font_path = "/www/server/panel/plugin/customfont/static/fonts/"
    __config = None
    __panel_static = "/www/server/panel/BTPanel/static/"
    __panel_font_dir = "/www/server/panel/BTPanel/static/font/"
    __panel_css_file = "/www/server/panel/BTPanel/static/css/base.min.css"
    
    # 面板使用的字体文件名
    __panel_font_regular = 'AlibabaPuHuiTi-2-75-SemiBold-new.ttf'
    __panel_font_bold = 'AlibabaPuHuiTi-2-105-Heavy-new.ttf'
    
    # 备份目录
    __backup_dir = "/www/server/panel/plugin/customfont/backup/"
    
    # 支持的字体格式（仅支持TTF以确保最佳兼容性）
    __supported_formats = ['.ttf']
    
    # 最大字体文件大小 (10MB)
    __max_font_size = 10 * 1024 * 1024
    
    # 自定义CSS标记
    __css_marker_start = '/* BT-CUSTOM-FONT-START-V1.2 */'
    __css_marker_end = '/* BT-CUSTOM-FONT-END-V1.2 */'

    #构造方法
    def __init__(self):
        if not os.path.exists(self.__font_path):
            os.makedirs(self.__font_path)
        if not os.path.exists(self.__backup_dir):
            os.makedirs(self.__backup_dir)

    #访问插件首页
    def index(self, args):
        return self.get_fonts(args)

    #获取配置
    def __get_config(self, force=False):
        if not self.__config or force:
            config_file = self.__plugin_path + 'config.json'
            if not os.path.exists(config_file):
                self.__config = {
                    "current_regular_font": "", 
                    "current_bold_font": "",
                    "fonts": []
                }
                self.__save_config()
            else:
                f_body = public.ReadFile(config_file)
                if f_body:
                    self.__config = json.loads(f_body)
                else:
                    self.__config = {
                        "current_regular_font": "", 
                        "current_bold_font": "",
                        "fonts": []
                    }
        return self.__config

    #保存配置
    def __save_config(self):
        config_file = self.__plugin_path + 'config.json'
        public.WriteFile(config_file, json.dumps(self.__config, ensure_ascii=False, indent=2))

    #获取字体列表
    def get_fonts(self, args):
        config = self.__get_config()
        fonts = config.get('fonts', [])
        
        # 检查字体文件是否存在，过滤掉不存在的
        valid_fonts = []
        for font in fonts:
            if os.path.exists(font.get('path', '')):
                valid_fonts.append(font)
        
        # 更新配置
        if len(valid_fonts) != len(fonts):
            config['fonts'] = valid_fonts
            self.__save_config()
        
        return {
            'status': True,
            'msg': '获取成功',
            'data': {
                'fonts': valid_fonts,
                'current_regular_font': config.get('current_regular_font', ''),
                'current_bold_font': config.get('current_bold_font', ''),
                'supported_formats': self.__supported_formats,
                'max_size': self.__max_font_size,
                'version': '1.2'
            }
        }

    #上传字体文件
    def upload_font(self, args):
        try:
            from flask import request
            upload_file = request.files.get('file')
            
            if not upload_file:
                return public.ReturnMsg(False, '请选择要上传的字体文件')
            
            filename = upload_file.filename
            if not filename:
                return public.ReturnMsg(False, '无效的文件名')
            
            filename = os.path.basename(filename)
            name, ext = os.path.splitext(filename)
            ext = ext.lower()
            
            if ext not in self.__supported_formats:
                return public.ReturnMsg(False, '仅支持TTF格式字体文件')
            
            font_id = str(uuid.uuid4())[:8]
            safe_filename = font_id + ext
            font_path = self.__font_path + safe_filename
            
            upload_file.save(font_path)
            
            file_size = os.path.getsize(font_path)
            if file_size > self.__max_font_size:
                os.remove(font_path)
                return public.ReturnMsg(False, '字体文件过大，最大支持10MB')
            
            file_md5 = public.FileMd5(font_path)
            
            font_name = args.get('font_name', name) if hasattr(args, 'get') else name
            if not font_name:
                font_name = name
            
            config = self.__get_config()
            font_info = {
                'id': font_id,
                'name': font_name,
                'filename': safe_filename,
                'original_name': filename,
                'path': font_path,
                'ext': ext,
                'size': file_size,
                'md5': file_md5,
                'addtime': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            config['fonts'].append(font_info)
            self.__save_config()
            
            public.WriteLog('自定义字体插件', '上传字体文件: ' + filename)
            
            return public.ReturnMsg(True, '字体上传成功')
            
        except Exception as e:
            return public.ReturnMsg(False, '上传失败: ' + str(e))

    #删除字体
    def delete_font(self, args):
        try:
            font_id = args.font_id if hasattr(args, 'font_id') else None
            if not font_id:
                return public.ReturnMsg(False, '缺少字体ID')
            
            config = self.__get_config()
            fonts = config.get('fonts', [])
            
            font_to_delete = None
            for i, font in enumerate(fonts):
                if font.get('id') == font_id:
                    font_to_delete = fonts.pop(i)
                    break
            
            if not font_to_delete:
                return public.ReturnMsg(False, '字体不存在')
            
            if config.get('current_regular_font') == font_id or config.get('current_bold_font') == font_id:
                self.__restore_panel_fonts()
                if config.get('current_regular_font') == font_id:
                    config['current_regular_font'] = ''
                if config.get('current_bold_font') == font_id:
                    config['current_bold_font'] = ''
            
            font_path = font_to_delete.get('path', '')
            if font_path and os.path.exists(font_path):
                os.remove(font_path)
            
            self.__save_config()
            
            public.WriteLog('自定义字体插件', '删除字体: ' + font_to_delete.get('name', ''))
            
            return public.ReturnMsg(True, '字体删除成功')
            
        except Exception as e:
            return public.ReturnMsg(False, '删除失败: ' + str(e))

    #备份面板字体
    def __backup_panel_fonts(self):
        try:
            for font_file in [self.__panel_font_regular, self.__panel_font_bold]:
                src = self.__panel_font_dir + font_file
                dst = self.__backup_dir + font_file
                if os.path.exists(src) and not os.path.exists(dst):
                    shutil.copy2(src, dst)
            
            css_src = self.__panel_css_file
            css_dst = self.__backup_dir + 'base.min.css.bak'
            if os.path.exists(css_src) and not os.path.exists(css_dst):
                shutil.copy2(css_src, css_dst)
            
            return True
        except Exception as e:
            public.WriteLog('自定义字体插件', '备份面板字体失败: ' + str(e))
            return False

    #恢复面板字体
    def __restore_panel_fonts(self):
        try:
            for font_file in [self.__panel_font_regular, self.__panel_font_bold]:
                src = self.__backup_dir + font_file
                dst = self.__panel_font_dir + font_file
                if os.path.exists(src):
                    shutil.copy2(src, dst)
            
            css_src = self.__backup_dir + 'base.min.css.bak'
            css_dst = self.__panel_css_file
            if os.path.exists(css_src):
                shutil.copy2(css_src, css_dst)
            
            return True
        except Exception as e:
            public.WriteLog('自定义字体插件', '恢复面板字体失败: ' + str(e))
            return False

    #生成全面的自定义字体CSS（v1.2改进版）
    def __generate_custom_font_css(self, regular_font_url, bold_font_url):
        # 使用全面的CSS选择器，确保覆盖所有元素
        css = self.__css_marker_start + '''
/* 字体定义 */
@font-face{font-family:'BT-Custom-Font';src:url(''' + regular_font_url + ''') format('truetype');font-weight:400;font-style:normal;font-display:swap;}
@font-face{font-family:'BT-Custom-Font';src:url(''' + bold_font_url + ''') format('truetype');font-weight:700;font-style:normal;font-display:swap;}
@font-face{font-family:'BT-Custom-Font';src:url(''' + regular_font_url + ''') format('truetype');font-weight:normal;font-style:normal;font-display:swap;}
@font-face{font-family:'BT-Custom-Font';src:url(''' + bold_font_url + ''') format('truetype');font-weight:bold;font-style:normal;font-display:swap;}

/* 全局覆盖 - 使用最高优先级 */
html,body,div,span,applet,object,iframe,h1,h2,h3,h4,h5,h6,p,blockquote,pre,a,abbr,acronym,address,big,cite,code,del,dfn,em,font,img,ins,kbd,q,s,samp,small,strike,strong,sub,sup,tt,var,b,u,i,center,dl,dt,dd,ol,ul,li,fieldset,form,label,legend,table,caption,tbody,tfoot,thead,tr,th,td,article,aside,canvas,details,embed,figure,figcaption,footer,header,hgroup,menu,nav,output,ruby,section,summary,time,mark,audio,video,input,textarea,select,button{font-family:'BT-Custom-Font','微软雅黑',Arial,Helvetica,sans-serif!important;}

/* 面板特定元素覆盖 */
html{font-family:'BT-Custom-Font','微软雅黑',Arial,Helvetica,sans-serif!important;}
body{font-family:'BT-Custom-Font','微软雅黑',Arial,Helvetica,sans-serif!important;}
input,select,textarea,button{font-family:'BT-Custom-Font','微软雅黑',Arial,Helvetica,sans-serif!important;}
.bt-w-menu p,.bt-w-menu,.bt-w-con,.bt-w-main,.bt-form,.sidebar-scroll,.sidebar-menu,.sidebar,.menu-item,.nav-item{font-family:'BT-Custom-Font','微软雅黑',Arial,Helvetica,sans-serif!important;}
.table,.divtable,.divtable *{font-family:'BT-Custom-Font','微软雅黑',Arial,Helvetica,sans-serif!important;}
.btn,.btn-default,.btn-primary,.btn-success,.btn-danger,.btn-warning,.btn-info{font-family:'BT-Custom-Font','微软雅黑',Arial,Helvetica,sans-serif!important;}
.layer,.layui-layer,.layui-layer-content,.layui-layer-title{font-family:'BT-Custom-Font','微软雅黑',Arial,Helvetica,sans-serif!important;}
.modal,.modal-body,.modal-header,.modal-footer{font-family:'BT-Custom-Font','微软雅黑',Arial,Helvetica,sans-serif!important;}
.alert,.panel,.card,.content,.main,.container,.container-fluid{font-family:'BT-Custom-Font','微软雅黑',Arial,Helvetica,sans-serif!important;}
.ico-font-ask{font-family:'BT-Custom-Font','微软雅黑',Arial,Helvetica,sans-serif!important;}

/* 强制覆盖所有元素的字体 */
*,:before,:after{font-family:'BT-Custom-Font','微软雅黑',Arial,Helvetica,sans-serif!important;}

/* Vue组件和动态元素 */
[data-v-],[v-cloak],[v-if],[v-for],[v-show]{font-family:'BT-Custom-Font','微软雅黑',Arial,Helvetica,sans-serif!important;}
.el-*{font-family:'BT-Custom-Font','微软雅黑',Arial,Helvetica,sans-serif!important;}
[class*="el-"]{font-family:'BT-Custom-Font','微软雅黑',Arial,Helvetica,sans-serif!important;}

/* 特殊元素保留原有字体（图标字体等） */
.glyphicon,.glyphicon *,[class*="icon-"],[class*="fa-"],.fa,.svgtofont{font-family:'Glyphicons Halflings','svgtofont',FontAwesome!important;}
'''
        return css + self.__css_marker_end

    #注入CSS到面板
    def __inject_css(self, regular_font_url, bold_font_url):
        try:
            css_content = public.ReadFile(self.__panel_css_file)
            if not css_content:
                return False
            
            # 移除所有版本的自定义CSS（兼容旧版本）
            patterns = [
                re.escape(self.__css_marker_start) + r'.*?' + re.escape(self.__css_marker_end),
                re.escape('/* BT-CUSTOM-FONT-START */') + r'.*?' + re.escape('/* BT-CUSTOM-FONT-END */'),
            ]
            for pattern in patterns:
                css_content = re.sub(pattern, '', css_content, flags=re.DOTALL)
            
            custom_css = self.__generate_custom_font_css(regular_font_url, bold_font_url)
            new_css_content = custom_css + '\n' + css_content
            public.WriteFile(self.__panel_css_file, new_css_content)
            
            return True
        except Exception as e:
            public.WriteLog('自定义字体插件', '注入CSS失败: ' + str(e))
            return False

    #移除注入的CSS
    def __remove_injected_css(self):
        try:
            css_content = public.ReadFile(self.__panel_css_file)
            if not css_content:
                return False
            
            patterns = [
                re.escape(self.__css_marker_start) + r'.*?' + re.escape(self.__css_marker_end),
                re.escape('/* BT-CUSTOM-FONT-START */') + r'.*?' + re.escape('/* BT-CUSTOM-FONT-END */'),
            ]
            for pattern in patterns:
                css_content = re.sub(pattern, '', css_content, flags=re.DOTALL)
            
            css_content = css_content.lstrip('\n')
            public.WriteFile(self.__panel_css_file, css_content)
            return True
        except Exception as e:
            public.WriteLog('自定义字体插件', '移除CSS失败: ' + str(e))
            return False

    #应用字体
    def apply_font(self, args):
        try:
            regular_font_id = args.regular_font_id if hasattr(args, 'regular_font_id') else None
            bold_font_id = args.bold_font_id if hasattr(args, 'bold_font_id') else None
            
            config = self.__get_config()
            
            if not regular_font_id and not bold_font_id:
                self.__restore_panel_fonts()
                self.__remove_injected_css()
                config['current_regular_font'] = ''
                config['current_bold_font'] = ''
                self.__save_config()
                public.WriteLog('自定义字体插件', '恢复默认字体')
                return public.ReturnMsg(True, '已恢复默认字体，刷新页面即可生效')
            
            self.__backup_panel_fonts()
            
            regular_font_path = None
            if regular_font_id:
                for f in config.get('fonts', []):
                    if f.get('id') == regular_font_id:
                        regular_font_path = f.get('path', '')
                        break
                if not regular_font_path or not os.path.exists(regular_font_path):
                    return public.ReturnMsg(False, '常规字体文件不存在')
                shutil.copy2(regular_font_path, self.__panel_font_dir + self.__panel_font_regular)
                config['current_regular_font'] = regular_font_id
            
            bold_font_path = None
            if bold_font_id:
                for f in config.get('fonts', []):
                    if f.get('id') == bold_font_id:
                        bold_font_path = f.get('path', '')
                        break
                if not bold_font_path or not os.path.exists(bold_font_path):
                    return public.ReturnMsg(False, '粗体字体文件不存在')
                shutil.copy2(bold_font_path, self.__panel_font_dir + self.__panel_font_bold)
                config['current_bold_font'] = bold_font_id
            
            if regular_font_path and not bold_font_path:
                shutil.copy2(regular_font_path, self.__panel_font_dir + self.__panel_font_bold)
            elif bold_font_path and not regular_font_path:
                shutil.copy2(bold_font_path, self.__panel_font_dir + self.__panel_font_regular)
            
            regular_url = '/static/font/' + self.__panel_font_regular
            bold_url = '/static/font/' + self.__panel_font_bold
            self.__inject_css(regular_url, bold_url)
            
            self.__save_config()
            
            public.WriteLog('自定义字体插件', '应用自定义字体: 常规={}, 粗体={}'.format(
                regular_font_id or '未指定', bold_font_id or '未指定'))
            
            return public.ReturnMsg(True, '字体已应用，刷新页面即可生效')
            
        except Exception as e:
            return public.ReturnMsg(False, '应用失败: ' + str(e))

    #预览字体
    def preview_font(self, args):
        try:
            font_id = args.font_id if hasattr(args, 'font_id') else None
            if not font_id:
                return public.ReturnMsg(False, '缺少字体ID')
            
            config = self.__get_config()
            
            font = None
            for f in config.get('fonts', []):
                if f.get('id') == font_id:
                    font = f
                    break
            
            if not font:
                return public.ReturnMsg(False, '字体不存在')
            
            return {
                'status': True,
                'msg': '获取成功',
                'data': {
                    'id': font.get('id'),
                    'name': font.get('name'),
                    'filename': font.get('filename'),
                    'url': '/customfont/static/fonts/' + font.get('filename'),
                    'ext': font.get('ext'),
                    'size': font.get('size'),
                    'addtime': font.get('addtime')
                }
            }
            
        except Exception as e:
            return public.ReturnMsg(False, '预览失败: ' + str(e))

    #重命名字体
    def rename_font(self, args):
        try:
            font_id = args.font_id if hasattr(args, 'font_id') else None
            new_name = args.new_name if hasattr(args, 'new_name') else None
            
            if not font_id or not new_name:
                return public.ReturnMsg(False, '缺少必要参数')
            
            config = self.__get_config()
            
            for font in config.get('fonts', []):
                if font.get('id') == font_id:
                    old_name = font.get('name', '')
                    font['name'] = new_name
                    self.__save_config()
                    
                    public.WriteLog('自定义字体插件', '重命名字体: {} -> {}'.format(old_name, new_name))
                    return public.ReturnMsg(True, '重命名成功')
            
            return public.ReturnMsg(False, '字体不存在')
            
        except Exception as e:
            return public.ReturnMsg(False, '重命名失败: ' + str(e))