# resource/image

任务流水线用到的**模板图**（pipeline 里 `"template": "xxx.png"` 引用的 `.png`），
以及开发期参考用的全屏截图。**被 pipeline 引用的才是模板**，其它冗余图片不会影响运行。

## 一、裁剪规范（务必遵守）

1. 必须从 **1280x720 的无损原始截图**裁剪（本机实机：MuMu12 物理 720x1280，游戏横屏渲染 1280x720）；
2. 分辨率必须与 `interface.json` 里的 `display_short_side`（当前 720）一致，**不要缩放**；
3. 抓图请用 `adb shell screencap` + `adb pull`（**不要**用 PowerShell `>` 重定向，会把二进制写成 UTF-16 导致图坏掉）：
   ```powershell
   $adb = "D:\Software\Game\Mumu12\MuMuPlayer\nx_main\adb.exe"
   & $adb -s 127.0.0.1:16384 shell screencap -p /sdcard/shot.png
   & $adb -s 127.0.0.1:16384 pull /sdcard/shot.png .\resource\image\_ref_xxx.png
   ```
   也可用框架 `tools/ImageCropper`（`install.bat` / `start.bat`）或 VSCode 插件 `nekosu.maa-support`。
4. **不要拿背景当模板**：GT 的启动页/大厅背景是动态美术（角色走动、美术轮换），
   只裁固定 UI 元素（按钮、图标栏、文字），并配合 `roi` 缩小搜索范围。

## 二、当前模板清单

| 文件名 | 尺寸 | 裁剪自（1280x720 坐标 x1,y1,x2,y2） | 用途 / 引用节点 |
| --- | --- | --- | --- |
| `btn_confirm_download.png` | 226x68 | (640,548)-(866,616) 热更弹窗 | 「下载资源」弹窗的**黄色「确认」按钮** → `GT_StartUp_ConfirmDownload` |
| `hub_nav_left.png` | 390x104 | (10,612)-(400,716) 大厅 | 大厅底部导航栏**菜单/英雄/公会/商店**四个图标 → `GT_StartUp_HubReady`（判定已进大厅） |
| `hub_nav_right.png` | 340x104 | (930,612)-(1270,716) | 备用：底部导航右侧（召唤/游玩/探险） |
| `hub_icon_menu.png` | 72x86 | (28,620)-(100,706) | 备用：单独「菜单」按钮（小型锚点，注意小模板易误匹配） |
| `hub_icon_adventure.png` | 95x91 | (1140,615)-(1235,706) | 备用：「探险」图标 |
| `hub_topright_icons.png` | 185x54 | (1080,8)-(1265,62) | 备用：右上角聊天/邮件/设置图标 |

> 备用的几张图当前未被 pipeline 引用，留着后续做任务时按需删改。

## 三、参考截图（非模板，仅供比对/重新裁剪）

| 文件名 | 内容 |
| --- | --- |
| `游戏开始界面.png` | 启动页（1608x904，MuMu 窗口缩放图，**不可直接用于裁模板**） |
| `_ref_main_screen.png` | 启动页（1280x720 原始分辨率，含「点击开始」） |
| `_ref_current.png` | 启动页 + B站账号欢迎条（1280x720） |

## 四、做新模板的流程

1. 游戏进到目标界面 → 抓 1280x720 图（见上）；
2. 用 Python/PIL 或 ImageCropper 裁出目标元素，存到本目录；
3. 在 `resource/pipeline/*.json` 里 `"template": "新图.png"` 引用，并加 `roi` 限制范围；
4. 跑一次任务，看 `debug/vision/` 里的可视化结果确认命中；
5. 回到本 README 的清单表登记文件名、尺寸、裁剪坐标、用途。

## v0.2.0 新增模板

源截图均为 MuMu 通过 ADB 获取的原始 1280×720 PNG，保存在 `dev/screenshots/`。坐标及来源另见 `dev/template-sources.json`。

| 模板 | 尺寸 | 来源截图 | 裁剪矩形 x1,y1,x2,y2 |
| --- | --- | --- | --- |
| `notice_header.png` | 105×29 | `06_after_download.png` | [496, 69, 601, 98] |
| `promo_close.png` | 30×29 | `07_after_notice.png` | [1222, 28, 1252, 57] |
| `menu_panel.png` | 389×85 | `20_menu.png` | [20, 380, 409, 465] |
| `signin_header.png` | 70×33 | `21_signin.png` | [604, 106, 674, 139] |
| `signin_footer.png` | 172×21 | `21_signin.png` | [550, 575, 722, 596] |
| `mail_title.png` | 96×44 | `18_mail.png` | [29, 16, 125, 60] |
| `mail_empty.png` | 106×20 | `19_mail_notice.png` | [745, 393, 851, 413] |
| `event_signin_footer.png` | 290×24 | `23_signin_claimed.png` | [756, 460, 1046, 484] |
| `story_title.png` | 92×44 | `28_missions.png` | [30, 16, 122, 60] |
| `daily_title.png` | 136×44 | `29_guardian_missions.png` | [30, 16, 166, 60] |
| `guild_title.png` | 94×44 | `32_guild_sign.png` | [30, 16, 124, 60] |
| `guild_sign_enabled.png` | 214×52 | `32_guild_sign.png` | [36, 618, 250, 670] |
| `guild_sign_disabled.png` | 214×52 | `34_guild_signed.png` | [36, 618, 250, 670] |
| `guild_ranking_title.png` | 102×27 | `31_guild.png` | [588, 88, 690, 115] |
| `hub_heart.png` | 21×23 | `17_clean_hub.png` | [432, 442, 453, 465] |
| `daily_claim_all.png` | 167×50 | `37_daily_claimable.png` | [1048, 618, 1215, 668] |
| `daily_claim_disabled.png` | 167×50 | `30_daily.png` | [1048, 618, 1215, 668] |
| `shop_title.png` | 93×44 | `40_shop_loaded.png` | [30, 16, 123, 60] |
| `subscription_claim.png` | 320×49 | `40_shop_loaded.png` | [275, 630, 595, 679] |
| `activity_title.png` | 93×44 | `43_activity.png` | [30, 16, 123, 60] |
| `play_title.png` | 136×44 | `46_play_loaded.png` | [30, 16, 166, 60] |
| `shop_free_daily.png` | 239×48 | `51_shop_resource.png` | [772, 478, 1011, 526] |
| `confirm_free.png` | 212×53 | `52_free_dialog.png` | [646, 555, 858, 608] |


2026-10-14新增模板（坐标与来源完整记录见dev/template-sources.json）：

| 模板 | 来源 | 裁剪矩形 |
| --- | --- | --- |
| promo_optout_unchecked.png | dev/screenshots/07_after_notice.png | [143,598,168,625] |
| mail_confirm_receive.png | 04_mail_after_click.png | [646,555,858,608] |
| friends_title.png | 01_current.png | [30,16,124,60] |
| friends_gift_all.png | 01_current.png | [367,642,561,681] |

后三张来源目录为dev/2026-10-14/screenshots。
