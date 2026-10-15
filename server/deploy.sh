#!/usr/bin/env bash
# Amusnaw — installation sur un VPS Ubuntu 24.04 neuf (à lancer en root).
#
#   curl -fsSL <url-de-ce-fichier> -o deploy.sh   (ou copie-le avec scp)
#   bash deploy.sh
#
# Le script : installe Docker et le pare-feu, récupère le code depuis GitHub,
# prépare le fichier .env (mots de passe générés), lance les services et
# télécharge le modèle. Les données (data/) s'envoient à part depuis ton PC.
set -euo pipefail

REPO="https://github.com/koceilaidir/amusnaw.git"
DIR="/opt/amusnaw"
MODEL="${MODEL:-qwen2.5:3b}"

say() { printf "\n\033[1;34m==> %s\033[0m\n" "$1"; }

[ "$(id -u)" -eq 0 ] || { echo "Lance ce script en root (sudo -i)."; exit 1; }

say "1/6 Mise à jour du système"
apt-get update -y && apt-get upgrade -y
apt-get install -y ca-certificates curl git ufw openssl

# Mémoire de secours (swap 4 Go) : évite un plantage si le modèle et la base
# de données demandent un pic de mémoire en même temps.
if ! swapon --show | grep -q /swapfile; then
  fallocate -l 4G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

say "2/6 Installation de Docker"
if ! command -v docker >/dev/null; then
  curl -fsSL https://get.docker.com | sh
fi
systemctl enable --now docker

say "3/6 Pare-feu (SSH, HTTP, HTTPS uniquement)"
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

say "4/6 Récupération du code"
if [ ! -d "$DIR/.git" ]; then
  echo "Le dépôt est privé : colle un jeton GitHub (Settings → Developer settings →"
  echo "Personal access tokens → Fine-grained, accès en lecture au dépôt amusnaw)."
  read -rsp "Jeton GitHub : " GH_TOKEN; echo
  git clone "https://${GH_TOKEN}@github.com/koceilaidir/amusnaw.git" "$DIR"
  git -C "$DIR" remote set-url origin "$REPO"   # ne garde pas le jeton sur le disque
else
  git -C "$DIR" pull --ff-only || true
fi
mkdir -p "$DIR/data"

say "5/6 Configuration (.env)"
ENV="$DIR/server/.env"
if [ ! -f "$ENV" ]; then
  read -rp "Domaine de l'API (ex. api.amusnaw.com) : " API_DOMAIN
  REVIEW_TOKEN="$(openssl rand -hex 12)"
  cat > "$ENV" <<EOF
API_DOMAIN=${API_DOMAIN}
POSTGRES_PASSWORD=$(openssl rand -hex 24)
JWT_SECRET=$(openssl rand -hex 32)
JWT_DAYS=90
GOOGLE_CLIENT_IDS=
APPLE_CLIENT_IDS=dz.amusnaw.amusnaw
LLM_BASE_URL=http://ollama:11434/v1
LLM_API_KEY=ollama
LLM_MODEL=${MODEL}
REVIEW_TOKEN=${REVIEW_TOKEN}
DEV_LOGIN=true
EOF
  chmod 600 "$ENV"
  echo "Code de la page de relecture : ${REVIEW_TOKEN}  (à noter, il est aussi dans $ENV)"
fi

say "6/6 Lancement des services et téléchargement du modèle"
cd "$DIR/server"
docker compose up -d --build
docker compose exec -T ollama ollama pull "$MODEL"
docker compose restart api

# Sauvegarde quotidienne de la base (relectures, mots appris), 7 jours gardés
mkdir -p /opt/amusnaw-backups
cat > /etc/cron.daily/amusnaw-backup <<'EOF'
#!/bin/sh
cd /opt/amusnaw/server && docker compose exec -T db pg_dump -U amusnaw amusnaw \
  | gzip > /opt/amusnaw-backups/amusnaw-$(date +%F).sql.gz
find /opt/amusnaw-backups -name '*.sql.gz' -mtime +7 -delete
EOF
chmod +x /etc/cron.daily/amusnaw-backup

DOMAIN="$(grep ^API_DOMAIN "$ENV" | cut -d= -f2)"
say "Terminé"
echo "Santé de l'API   : https://${DOMAIN}/health"
echo "Relecture        : https://${DOMAIN}/review"
echo "Envoie les données depuis ton PC :"
echo "  scp -r data/* root@<IP-du-VPS>:${DIR}/data/"
echo "puis sur le VPS :"
echo "  chmod -R a+rX ${DIR}/data && cd ${DIR}/server && docker compose restart api"
