"""
Скрипт: тянет участников Discord-сервера по ролям
и генерирует файл staffUPD (JSON) в формате, который ожидает сайт.

РЕЖИМЫ ЗАПУСКА:
1. Локально: заполни BOT_TOKEN / GUILD_ID ниже константами, либо
   задай переменные окружения DISCORD_BOT_TOKEN / DISCORD_GUILD_ID.
2. В GitHub Actions: токен и ID берутся из переменных окружения
   (заданы в workflow из GitHub Secrets), константы можно не трогать.

ПЕРЕД ЗАПУСКОМ:
1. pip install requests
2. Убедись, что в Discord Developer Portal у бота включён
   "Server Members Intent" (Bot -> Privileged Gateway Intents).
3. Бот должен быть добавлен на сервер (через OAuth2 invite-ссылку).
4. Заполни ROLE_RANKS (список ID ролей и подписи рангов).

ЗАПУСК ЛОКАЛЬНО:
    python sync_staff.py
"""

import json
import os
import sys
import time
import requests

# ============ НАСТРОЙКИ ============

# Для локального теста можно вписать сюда прямо значения.
# Если переменные окружения заданы (как в GitHub Actions) — они в приоритете.
BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "ВСТАВЬ_СЮДА_ТОКЕН_БОТА")
GUILD_ID = os.environ.get("DISCORD_GUILD_ID", "ВСТАВЬ_СЮДА_ID_СЕРВЕРА")

# Список ролей в порядке от старшей к младшей.
# role_id — ID роли в Discord, rank — как будет подписано на сайте.
ROLE_RANKS = [
    {"role_id": "1490676850056368189", "rank": "Президент"},
    {"role_id": "1524791150219886742", "rank": "Вице-президент"},
    {"role_id": "1490677166164410479", "rank": "Зам. Президента"},
    {"role_id": "1509517682498736299", "rank": "Председатель Гос. Думы"},
    {"role_id": "1490677108668895324", "rank": "Гос. дума"},
    {"role_id": "1493633606650695750", "rank": "Депутат"},
    # добавляй сколько нужно строк
]

# Итоговый файл — должен совпадать с тем, что грузит сайт через fetch()
OUTPUT_FILE = "staffUPD"

# ============================================================

API_BASE = "https://discord.com/api/v10"
HEADERS = {"Authorization": f"Bot {BOT_TOKEN}"}


def fetch_all_members(guild_id):
    """Постранично забирает всех участников гильдии (лимит Discord — 1000 за раз)."""
    members = []
    after = "0"
    while True:
        resp = requests.get(
            f"{API_BASE}/guilds/{guild_id}/members",
            headers=HEADERS,
            params={"limit": 1000, "after": after},
        )
        if resp.status_code == 429:
            retry_after = resp.json().get("retry_after", 1)
            print(f"Rate limit, жду {retry_after}s...")
            time.sleep(retry_after)
            continue
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        members.extend(batch)
        after = batch[-1]["user"]["id"]
        if len(batch) < 1000:
            break
    return members


def avatar_url(user):
    """Строит прямую ссылку на аватар пользователя Discord."""
    if user.get("avatar"):
        ext = "gif" if user["avatar"].startswith("a_") else "png"
        return f"https://cdn.discordapp.com/avatars/{user['id']}/{user['avatar']}.{ext}?size=256"
    # Дефолтный аватар Discord, если своего нет
    default_idx = (int(user["id"]) >> 22) % 6
    return f"https://cdn.discordapp.com/embed/avatars/{default_idx}.png"


def display_name(member):
    """Никнейм на сервере, если есть, иначе имя пользователя."""
    nick = member.get("nick")
    if nick:
        return nick
    user = member["user"]
    return user.get("global_name") or user["username"]


def main():
    if "ВСТАВЬ_СЮДА" in BOT_TOKEN or "ВСТАВЬ_СЮДА" in GUILD_ID:
        print("Заполни BOT_TOKEN и GUILD_ID в начале файла перед запуском.")
        sys.exit(1)

    print("Забираю участников сервера...")
    members = fetch_all_members(GUILD_ID)
    print(f"Всего участников: {len(members)}")

    result = []
    seen_user_ids = set()

    # Идём по ролям в заданном порядке — так сохраняется порядок вывода на сайте
    for role_entry in ROLE_RANKS:
        role_id = role_entry["role_id"]
        rank_name = role_entry["rank"]
        for member in members:
            user_id = member["user"]["id"]
            if role_id in member.get("roles", []) and user_id not in seen_user_ids:
                result.append({
                    "name": display_name(member),
                    "rank": rank_name,
                    "avatar": avatar_url(member["user"]),
                })
                seen_user_ids.add(user_id)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"Готово! Записано {len(result)} человек в {OUTPUT_FILE}")


if __name__ == "__main__":
    main()