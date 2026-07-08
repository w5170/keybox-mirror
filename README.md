# GitHub Keybox Mirror for Yurikey

这个仓库用于把 TAKR 最新 `status=valid` 的 `keybox.xml` 镜像成 GitHub Raw 直链，供 Yurikey 模块直接后台下载。

## 你需要做的事

1. 在 GitHub 新建一个 **Public** 仓库，例如：`keybox-mirror`。
2. 上传本模板里的全部文件到仓库根目录。
3. 在仓库设置里添加 Actions Secret：
   - Name: `CAPMONSTER_CLIENT_KEY`
   - Value: 你的 CapMonster Cloud client key
4. 进入仓库 `Actions` 页，运行 `Update TAKR keybox` workflow。
5. 成功后仓库会生成/更新：
   - `keybox.xml`
   - `metadata.json`
6. 手机模块配置 GitHub Raw 地址：

```sh
su
mkdir -p /data/adb/Yurikey
cat > /data/adb/Yurikey/keybox_source.conf <<'EOF'
TAKR_MIRROR_URL=https://raw.githubusercontent.com/YOUR_USERNAME/keybox-mirror/main/keybox.xml
EOF
chmod 600 /data/adb/Yurikey/keybox_source.conf
```

把 `YOUR_USERNAME` 和 `keybox-mirror` 改成你的 GitHub 用户名和仓库名。

之后点 Yurikey 模块里的 `Yuri Keybox`，它会优先从你的 GitHub Raw 下载，不再跳 TAKR 网页。

## 自动更新频率

默认每 6 小时跑一次，也可以在 GitHub Actions 里手动运行。
