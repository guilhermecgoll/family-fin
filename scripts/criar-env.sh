#!/usr/bin/env sh
# Cria o .env a partir do .env.example, com uma senha aleatória para o banco.
# Não sobrescreve um .env existente.
set -eu

cd "$(dirname "$0")/.."

if [ -f .env ]; then
    echo ".env já existe; nada a fazer."
    exit 0
fi

senha=$(od -An -N24 -tx1 /dev/urandom | tr -d ' \n')
sed "s/^POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=${senha}/" .env.example > .env
# Usuário do container de desenvolvimento igual ao do host, para os arquivos criados
# no bind mount (uv.lock, cobertura) não ficarem com outro dono.
cat >> .env <<FIM

# Gerado por scripts/criar-env.sh
DEV_UID=$(id -u)
DEV_GID=$(id -g)
FIM
chmod 600 .env
echo ".env criado. Preencha os tokens e chaves conforme as etapas avançarem."
