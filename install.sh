#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH

#配置插件安装目录
install_path=/www/server/panel/plugin/customfont
font_path=/www/server/panel/plugin/customfont/static/fonts
panel_css=/www/server/panel/BTPanel/static/css/base.css

#安装
Install()
{
	echo '正在安装面板自定义字体插件...'
	
	#创建插件目录
	mkdir -p $install_path
	mkdir -p $font_path
	
	#复制插件文件
	cp -r -f ./* $install_path/
	
	#创建字体配置文件
	if [ ! -f "$install_path/config.json" ]; then
		echo '{"current_font": "", "fonts": []}' > $install_path/config.json
	fi
	
	#创建自定义字体CSS文件
	if [ ! -f "$install_path/custom_font.css" ]; then
		touch $install_path/custom_font.css
	fi
	
	#在面板base.css中添加自定义字体CSS引用
	if [ -f "$panel_css" ]; then
		#检查是否已添加引用
		if ! grep -q "plugin/customfont/custom_font.css" $panel_css; then
			echo "" >> $panel_css
			echo "/* 自定义字体插件 - 请勿删除此行 */" >> $panel_css
			echo "@import url('/customfont/custom_font.css');" >> $panel_css
			echo '已添加字体CSS引用到面板样式文件'
		fi
	fi
	
	echo '================================================'
	echo '安装完成'
}

#卸载
Uninstall()
{
	echo '正在卸载面板自定义字体插件...'
	
	#从面板base.css中移除自定义字体CSS引用
	if [ -f "$panel_css" ]; then
		sed -i '/customfont\/custom_font.css/d' $panel_css
		sed -i '/自定义字体插件/d' $panel_css
	fi
	
	#删除插件目录
	rm -rf $install_path
	
	echo '================================================'
	echo '卸载完成'
}

#操作判断
if [ "${1}" == 'install' ];then
	Install
elif [ "${1}" == 'uninstall' ];then
	Uninstall
else
	echo 'Error!';
fi
