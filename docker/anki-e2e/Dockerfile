FROM mcr.microsoft.com/playwright:v1.49.1-noble

ARG ANKI_VERSION=26.05
ARG ANKI_SHA256=
ARG ANKI_PYTHON_PACKAGE=anki==26.5
ARG UBUNTU_MIRROR=https://archive.ubuntu.com/ubuntu

ENV ANKI_VERSION=${ANKI_VERSION}
ENV ANKI_SHA256=${ANKI_SHA256}
ENV ANKI_PYTHON_PACKAGE=${ANKI_PYTHON_PACKAGE}
ENV ANKI_BIN=/opt/anki/anki
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

RUN mkdir -p /e2e/bin /e2e/artifacts /e2e/anki-data \
    && cd /e2e \
    && npm init -y >/dev/null 2>&1 \
    && npm install pnpm@9.15.4 playwright@1.49.1 \
    && python3 -m pip install --break-system-packages "${ANKI_PYTHON_PACKAGE}"

COPY docker/anki-e2e/*.sh docker/anki-e2e/*.py docker/anki-e2e/*.mjs /e2e/bin/

RUN chmod +x /e2e/bin/*.sh /e2e/bin/*.py /e2e/bin/*.mjs \
    && /e2e/bin/install-anki.sh

WORKDIR /workspace

ENTRYPOINT ["/e2e/bin/entrypoint.sh"]
CMD ["/e2e/bin/run-e2e.sh"]
