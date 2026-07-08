# GitHub Keybox Mirror for Yurikey

这个仓库用于把 TAKR 最新 `status=valid` 的 `keybox.xml` 镜像成 GitHub Raw 直链，供 Yurikey 模块直接后台下载。

## Solver 支持

支持二选一：

- CapSolver：添加 Actions Secret `CAPSOLVER_CLIENT_KEY`
- CapMonster：添加 Actions Secret `CAPMONSTER_CLIENT_KEY`

如果两个都存在，默认优先使用 CapSolver。也可以在 `Settings → Secrets and variables → Actions → Variables` 里添加：

```text
SOLVER_PROVIDER=capsolver
```

或：

```text
SOLVER_PROVIDER=capmonster
```

## 使用步骤

1. 在仓库 `Settings → Secrets and variables → Actions → New repository secret` 添加 solver API key。
2. 进入 `Actions → Update TAKR keybox → Run workflow`。
3. 成功后仓库会生成/更新：
   - `keybox.xml`
   - `metadata.json`
4. 手机模块配置 GitHub Raw 地址：

```sh
su
mkdir -p /data/adb/Yurikey
cat > /data/adb/Yurikey/keybox_source.conf <<'EOF'
TAKR_MIRROR_URL=https://raw.githubusercontent.com/YOUR_USERNAME/keybox-mirror/main/keybox.xml
EOF
chmod 600 /data/adb/Yurikey/keybox_source.conf
```

默认每 6 小时自动更新一次，也可以手动运行。
