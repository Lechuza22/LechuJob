#!/bin/zsh
# Arma LechuJob.app (lanzador para el Dock de macOS) apuntando a esta carpeta.
set -e
cd "$(dirname "$0")"
APP_DIR="$PWD"
PY="$(command -v python3)"
TMP="$(mktemp -d)"

cat > "$TMP/launcher.applescript" <<EOF
set appDir to "$APP_DIR"
try
	do shell script "curl -s -o /dev/null http://127.0.0.1:8765/api/state"
	open location "http://localhost:8765"
on error
	do shell script "cd " & quoted form of appDir & " && mkdir -p data && PATH=/opt/homebrew/bin:/usr/local/bin:\$PATH nohup $PY app.py > data/server.log 2>&1 &"
end try
EOF

rm -rf LechuJob.app
osacompile -o LechuJob.app "$TMP/launcher.applescript"

# Ícono: logo.svg -> .icns
mkdir -p "$TMP/LechuJob.iconset"
qlmanage -t -s 1024 -o "$TMP" static/logo.svg >/dev/null 2>&1
for s in 16 32 128 256 512; do
  sips -z $s $s "$TMP/logo.svg.png" --out "$TMP/LechuJob.iconset/icon_${s}x${s}.png" >/dev/null
  sips -z $((s*2)) $((s*2)) "$TMP/logo.svg.png" --out "$TMP/LechuJob.iconset/icon_${s}x${s}@2x.png" >/dev/null
done
iconutil -c icns "$TMP/LechuJob.iconset" -o LechuJob.app/Contents/Resources/applet.icns
rm -f LechuJob.app/Contents/Resources/Assets.car
/usr/libexec/PlistBuddy -c "Delete :CFBundleIconName" LechuJob.app/Contents/Info.plist 2>/dev/null || true
codesign --force --deep -s - LechuJob.app
touch LechuJob.app
rm -rf "$TMP"
echo "Listo: $APP_DIR/LechuJob.app (arrastralo al Dock)"
