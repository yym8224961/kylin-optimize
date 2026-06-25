#!/bin/bash
# KWin 性能优化脚本 — 禁用不必要的特效，提升 UI 帧率
# 适用于: Huawei QingYun L420x-A121 / Kirin 9000C / Maleoon 910 GPU

DBUS="dbus-send --session --dest=org.ukui.KWin --print-reply"
KILL_EFFECT="/Effects org.ukui.kwin.Effects.unloadEffect"

echo "=== KWin 性能优化开始 ==="

# 禁用所有非必要特效（共 28 个）
EFFECTS=(
    "magnifier" "zoom" "colorfilter" "touchclick"
    "touchmotionstreak" "kwin4_effect_eyeonscreen" "desktopgrid" "slide"
    "slidingpopups" "kwin4_effect_modalshake" "kwin4_effect_squashtablet"
    "kwin4_effect_fadedropdownmenu" "kwin4_effect_fadecascadingmenu"
    "kwin4_effect_squash" "kwin4_effect_frozenapp" "ubr"
    "stickyborder" "UKUI-KWin-Windows-View" "watermark"
    "kwin4_effect_scaletooltip" "kwin4_effect_dialogparent"
    "kwin4_effect_scaledesktop" "kwin4_effect_fadingpopups"
    "kwin4_effect_login" "kwin4_effect_sessionquit"
    "kwin4_effect_logout" "screenshot" "colorpicker"
    "screencopy" "kwin4_effect_scale"
)

for effect in "${EFFECTS[@]}"; do
    $DBUS $KILL_EFFECT string:"$effect" 2>/dev/null
done

# 暂停后恢复合成器以重置渲染管线
$DBUS /Compositor org.ukui.kwin.Compositing.suspend 2>/dev/null
sleep 1
$DBUS /Compositor org.ukui.kwin.Compositing.resume 2>/dev/null

echo "=== KWin 性能优化完成 ==="
echo "活跃特效:"
$DBUS /Effects org.freedesktop.DBus.Properties.Get string:"org.ukui.kwin.Effects" string:"activeEffects" 2>/dev/null
