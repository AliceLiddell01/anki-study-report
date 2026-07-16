FROM mcr.microsoft.com/playwright:v1.55.1-noble@sha256:2f29369043d81d6d69a815ceb80760f55e85f5020371ad06a4d996f18503ad1c

ARG ANKI_VERSION=26.05
ARG ANKI_SHA256=6223d705563f71ab40ce072a5d96a3919c546d5dde1e4c49dc27975e70067274
ARG ANKI_PYTHON_PACKAGE=anki==26.5
ARG PNPM_VERSION=9.15.9
ARG PLAYWRIGHT_VERSION=1.55.1
ARG UBUNTU_MIRROR=https://archive.ubuntu.com/ubuntu

LABEL org.opencontainers.image.source="https://github.com/AliceLiddell01/anki-study-report"
LABEL org.opencontainers.image.version="env-v1"
LABEL org.opencontainers.image.title="Anki Study Report E2E Environment"
LABEL org.opencontainers.image.description="Environment-only runtime for Anki Study Report real-Anki E2E"

ENV ANKI_VERSION=${ANKI_VERSION}
ENV ANKI_SHA256=${ANKI_SHA256}
ENV ANKI_REQUIRE_SHA256=1
ENV ANKI_PYTHON_PACKAGE=${ANKI_PYTHON_PACKAGE}
ENV ANKI_BIN=/opt/anki/anki
ENV ANKI_BASE=/e2e/anki-data
ENV HOME=/e2e/home
ENV WORKSPACE=/workspace
ENV PNPM_STORE_DIR=/e2e/pnpm-store
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1
ENV PATH="/e2e/node_modules/.bin:${PATH}"
ENV PYTHONDONTWRITEBYTECODE=1
ENV QTWEBENGINE_DISABLE_SANDBOX=1
ENV QT_OPENGL=software
ENV LIBGL_ALWAYS_SOFTWARE=1
ENV NO_AT_BRIDGE=1

USER root

RUN if [ -n "$UBUNTU_MIRROR" ]; then \
        sed -i -E "s#http://(archive|security).ubuntu.com/ubuntu/?#${UBUNTU_MIRROR%/}#g" /etc/apt/sources.list /etc/apt/sources.list.d/*.sources 2>/dev/null || true; \
    fi \
    && printf '%s\n' \
        'Acquire::Retries "5";' \
        'Acquire::http::Timeout "30";' \
        'Acquire::https::Timeout "30";' \
        > /etc/apt/apt.conf.d/80-retries \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        dbus-x11 \
        git \
        jq \
        libasound2t64 \
        libegl1 \
        libfontconfig1 \
        libfreetype6 \
        libgl1 \
        libglx-mesa0 \
        libice6 \
        libopengl0 \
        libpulse0 \
        libsm6 \
        libx11-6 \
        libx11-xcb1 \
        libxcb-icccm4 \
        libxcb-cursor0 \
        libxcb-image0 \
        libxcb-keysyms1 \
        libxcb-randr0 \
        libxcb-render-util0 \
        libxcb-shape0 \
        libxcb-shm0 \
        libxcb-sync1 \
        libxcb-util1 \
        libxcb-xfixes0 \
        libxcb-xinerama0 \
        libxcb-xkb1 \
        libxext6 \
        libxi6 \
        libxkbcommon-x11-0 \
        libxrender1 \
        procps \
        python3 \
        python3-pip \
        python3-venv \
        rsync \
        unzip \
        x11-utils \
        xauth \
        xvfb \
        zstd \
    && rm -rf /var/lib/apt/lists/*

RUN install -d -m 0755 /e2e/bin /e2e/local-input /workspace \
    && install -d -m 0777 /e2e/artifacts /e2e/anki-data /e2e/home /e2e/pnpm-store \
    && cd /e2e \
    && npm init -y >/dev/null 2>&1 \
    && npm install --no-audit --no-fund --ignore-scripts \
        "pnpm@${PNPM_VERSION}" \
        "playwright@${PLAYWRIGHT_VERSION}" \
    && python3 -m pip install --break-system-packages --no-cache-dir "${ANKI_PYTHON_PACKAGE}"

COPY docker/anki-e2e/install-anki.sh /e2e/bin/install-anki.sh

RUN sed -i 's/\r$//' /e2e/bin/install-anki.sh \
    && chmod 0755 /e2e/bin/install-anki.sh \
    && /e2e/bin/install-anki.sh \
    && test -x /opt/anki/anki \
    && test -L /usr/local/bin/anki-desktop

WORKDIR /workspace

CMD ["bash"]
