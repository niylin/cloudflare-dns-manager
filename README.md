# Cloudflare Dns Manager
使用Cloudflare API来管理解析记录,适用于网络环境不佳,网页操作速度缓慢的场景

![][https://github.com/niylin/cloudflare-dns-manager/blob/main/123.png]

main.py 主入口,一个简单的GUI界面
cli-manager.py 在CLI中使用,或者通过main.py --cli

## 密钥存储
使用 用户名,MAC,固定前缀 组合生成密钥对配置信息进行简单加密
存储在 $HOME/.config/cfconfig/cloudflare-dns-manager_hash.json

## 依赖

本项目依赖如下 Python 包：

- `requests`
- `PyGObject`
- `colorama`

## 安装依赖

<div>
  <button class="btn" data-clipboard-target="#code"></button>
  <pre><code id="code" class="language-bash">
pip install -r requirements.txt
  </code></pre>
</div>

> 注意：`PyGObject` 在某些 Linux 发行版中需要通过系统包管理器安装 GTK 相关运行时。

## 使用方法  

<div>
  <button class="btn" data-clipboard-target="#code"></button>
  <pre><code id="code" class="language-bash">
  # GUI
  git clone https://github.com/niylin/cloudflare-dns-manager.git
  cd cloudflare-dns-manager
  python3 main.py
  </code></pre>
</div>


<div>
  <button class="btn" data-clipboard-target="#code"></button>
  <pre><code id="code" class="language-bash">
  # CLI
  git clone https://github.com/niylin/cloudflare-dns-manager.git
  cd cloudflare-dns-manager
  python3 cli-manager.py
  </code></pre>
</div>

## 卸载,删除文件夹和图标即可
<div>
  <button class="btn" data-clipboard-target="#code"></button>
  <pre><code id="code" class="language-bash">
# 删除自动创建的内容
rm $HOME/Desktop/dns-manager.desktop
rm -r $HOME/.config/cfconfig

  </code></pre>
</div>
