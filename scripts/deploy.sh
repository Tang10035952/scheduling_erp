#!/usr/bin/env bash
  set -euo pipefail

  APP_DIR=${APP_DIR:-$HOME/scheduling_erp}
  REPO_SSH=${REPO_SSH:-git@github.com:Tang10035952/scheduling_erp.git}
  BRANCH=${BRANCH:-release}
  DOMAIN=${DOMAIN:-hitpop2216.com}

  SUDO=${SUDO:-sudo}

  install_deps() {
    $SUDO apt-get update
    $SUDO apt-get install -y git docker.io docker-compose-plugin certbot
    $SUDO systemctl enable --now docker
  }

  ensure_repo() {
    if [ ! -d "$APP_DIR/.git" ]; then
      git clone "$REPO_SSH" "$APP_DIR"
    fi
    cd "$APP_DIR"
    git fetch origin "$BRANCH"
    git checkout "$BRANCH"
    git reset --hard "origin/$BRANCH"
  }

  ensure_env() {
    cd "$APP_DIR"
    if [ ! -f .env ]; then
      cp .env.example .env
      echo "請先編輯 $APP_DIR/.env 填入正式設定後再執行一次。"
      exit 1
    fi
  }

  ensure_cert() {
    local cert_path="/etc/letsencrypt/live/${DOMAIN}/fullchain.pem"
    if ! $SUDO test -f "$cert_path"; then
      echo "未找到 SSL 憑證，開始申請..."
      docker compose down || true
      $SUDO certbot certonly --standalone \
        -d "$DOMAIN" -d "www.$DOMAIN" \
        --agree-tos --non-interactive --register-unsafely-without-email
    fi
  }

  deploy() {
    cd "$APP_DIR"
    mkdir -p certbot/www
    docker compose build
    docker compose up -d
    printf "Deploy complete: %s\n" "$(git rev-parse --short HEAD)"
  }

  install_deps
  ensure_repo
  ensure_env
  ensure_cert
  deploy