import asyncio
import requests
from datetime import datetime
import os

from telegram import Bot

# ===================== НАСТРОЙКИ =====================
TELEGRAM_TOKEN = "8081124486:AAF0FQRloQuukuOw-tLe6QpOLwXXp3y6ESY"
CHAT_ID = "-1003517858688"
MORALIS_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJub25jZSI6IjE2ZGIwZWY1LWFiM2ItNGQwYi1hOTUzLWIyOTU5ZjA5YTYxMyIsIm9yZ0lkIjoiNDkwNjU5IiwidXNlcklkIjoiNTA0ODI0IiwidHlwZUlkIjoiMjQ3Mzc0ZjUtMTg1Ni00ZWZlLWI5NzktZGJlYWFiM2UxZDUwIiwidHlwZSI6IlBST0pFQ1QiLCJpYXQiOjE3Njg1ODE2OTIsImV4cCI6NDkyNDM0MTY5Mn0.1F7o0isylfg8Kb23C2o_p55HB-h8VnEGP-V4aYiR3FM"

# Список кошельков для отслеживания
WALLETS = [
    "0x4AC7732Cfc2623515668202a15E9e3eedA2E308e",
    "0x32D233F791a2C924eCBc974392E3604c414C0513"
]

CHECK_INTERVAL = 180  # секунд
SENT_TX_FILE = "sent_tx.txt"  # файл для хранения отправленных хэшей
# =======================================================

bot = Bot(token=TELEGRAM_TOKEN)

# Загружаем уже отправленные транзакции из файла
sent_tx_hashes = set()
if os.path.exists(SENT_TX_FILE):
    with open(SENT_TX_FILE, "r") as f:
        sent_tx_hashes = set(line.strip() for line in f.readlines())


def get_token_transactions(wallet_address):
    """Получаем последние 10 токен-трансферов на кошелек через Moralis"""
    url = f"https://deep-index.moralis.io/api/v2/{wallet_address}/erc20/transfers"
    headers = {"X-API-Key": MORALIS_API_KEY}
    params = {"chain": "bsc", "limit": 10}  # последние 10 транзакций
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    data = response.json()
    return data.get("result", [])


def format_transaction(tx):
    """Форматируем сообщение для Telegram"""
    amount = int(tx["value"]) / (10 ** int(tx["token_decimals"]))

    # Конвертируем ISO 8601 в datetime
    dt = datetime.fromisoformat(tx["block_timestamp"].replace("Z", "+00:00"))
    time_str = dt.strftime("%a %b %d %Y %H:%M:%S GMT+0000 (UTC)")

    message = (
        f"Wallet: {tx['to_address']}\n"
        f"TxID: {tx['transaction_hash']}\n"
        f"From: {tx['from_address']}\n"
        f"To: {tx['to_address']}\n"
        f"Amount: {amount}\n"
        f"Token: {tx['token_symbol']}\n"
        f"Time: {time_str}"
    )
    return message


async def monitor_tokens():
    print("🤖 Бот запущен и отслеживает входящие токены на кошельках")
    while True:
        try:
            for wallet in WALLETS:
                txs = get_token_transactions(wallet)
                for tx in reversed(txs):  # чтобы отправлять в хронологическом порядке
                    # проверяем, что транзакция новая и пришла на один из наших кошельков
                    if tx["transaction_hash"] not in sent_tx_hashes and tx["to_address"].lower() in [w.lower() for w in
                                                                                                     WALLETS]:
                        message = format_transaction(tx)
                        await bot.send_message(chat_id=CHAT_ID, text=message)
                        # добавляем хэш в память и сохраняем в файл
                        sent_tx_hashes.add(tx["transaction_hash"])
                        with open(SENT_TX_FILE, "a") as f:
                            f.write(tx["transaction_hash"] + "\n")
        except Exception as e:
            print(f"⚠️ Ошибка мониторинга: {e}")
        await asyncio.sleep(CHECK_INTERVAL)


def main():
    asyncio.run(monitor_tokens())


if __name__ == "__main__":
    main()
