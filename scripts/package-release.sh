#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <version>" >&2
    exit 64
fi

VERSION=$1
ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PACKAGE_NAME="kylin-gpu-control-$VERSION"
DIST_DIR="$ROOT_DIR/dist"
WORK_DIR=$(mktemp -d "${TMPDIR:-/tmp}/kylin-gpu-control-release.XXXXXX")
PACKAGE_DIR="$WORK_DIR/$PACKAGE_NAME"
ARCHIVE="$DIST_DIR/kylin-gpu-control-$VERSION.tar.gz"

cleanup() {
    rm -rf "$WORK_DIR"
}
trap cleanup EXIT HUP INT TERM

copy_path() {
    src=$1
    mkdir -p "$(dirname -- "$PACKAGE_DIR/$src")"
    cp -R "$ROOT_DIR/$src" "$PACKAGE_DIR/$src"
}

mkdir -p "$PACKAGE_DIR" "$DIST_DIR"

for path in \
    README.md \
    LICENSE \
    KWIN-OPTIMIZE-GUIDE.md \
    install-gpu-control.sh \
    kwin-optimize.sh \
    kwin-optimize.desktop \
    ukui-kwinrc-optimized \
    packaging \
    src/__init__.py \
    src/kylin_gpu_control
do
    copy_path "$path"
done

rm -f "$ARCHIVE" "$ARCHIVE.sha256"
(cd "$WORK_DIR" && COPYFILE_DISABLE=1 tar --no-xattrs -czf "$ARCHIVE" "$PACKAGE_NAME")

if command -v sha256sum >/dev/null 2>&1; then
    (cd "$DIST_DIR" && sha256sum "$(basename -- "$ARCHIVE")" > "$(basename -- "$ARCHIVE").sha256")
else
    (cd "$DIST_DIR" && shasum -a 256 "$(basename -- "$ARCHIVE")" > "$(basename -- "$ARCHIVE").sha256")
fi

echo "$ARCHIVE"
