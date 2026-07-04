#!/usr/bin/env bash
set -Eeuo pipefail

: "${ANKI_VERSION:=26.05}"
: "${ANKI_SHA256:=}"

case "$(uname -m)" in
  x86_64 | amd64)
    anki_arch="linux-x86_64"
    ;;
  aarch64 | arm64)
    anki_arch="linux-aarch64"
    ;;
  *)
    echo "Unsupported architecture: $(uname -m)" >&2
    exit 1
    ;;
esac

archive_name="anki-${ANKI_VERSION}-${anki_arch}.tar.zst"
download_url="${ANKI_DOWNLOAD_URL:-https://github.com/ankitects/anki/releases/download/${ANKI_VERSION}/${archive_name}}"
archive_path="/tmp/${archive_name}"

echo "Downloading ${download_url}"
curl -fL --retry 3 --retry-delay 2 -o "$archive_path" "$download_url"

if [ -n "$ANKI_SHA256" ]; then
  echo "${ANKI_SHA256}  ${archive_path}" | sha256sum -c -
fi

rm -rf /opt/anki
mkdir -p /opt/anki
tar --use-compress-program=unzstd -xf "$archive_path" -C /opt/anki --strip-components=1

anki_bin="$(find /opt/anki -maxdepth 3 -type f -name anki -perm -111 | head -n 1)"
if [ -z "$anki_bin" ]; then
  echo "Could not locate Anki executable under /opt/anki" >&2
  find /opt/anki -maxdepth 3 -type f >&2
  exit 1
fi

ln -sf "$anki_bin" /usr/local/bin/anki-desktop
echo "Installed Anki executable: $anki_bin"
"$anki_bin" --version || true
