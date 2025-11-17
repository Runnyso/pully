import random
from web3 import Web3
import time
import datetime

# Конфигурация
RPC_URL = "https://monad-testnet.g.alchemy.com"
CONTRACT_ADDRESS = "0xD97BCe4518b886A36e345764333d77b5fAF6FE2C"
PRIVATE_KEYS_FILE = "private_keys.txt"
CHAIN_ID = 10143
DELAY_MIN = 20
DELAY_MAX = 28

# Настройки газа
GAS_MULTIPLIER = 1.18
GAS_DEVIATION = (0.01, 0.02)
MIN_GAS_LIMIT = 96258
MAX_GAS_LIMIT = 250000

def load_private_keys(file_path):
    """Загружает приватные ключи из файла"""
    with open(file_path, "r") as f:
        return [line.strip() for line in f if line.strip()]

def generate_custom_gas(base_gas):
    """Генерация кастомного газа с возвратом множителя"""
    if base_gas is None:
        return MAX_GAS_LIMIT, GAS_MULTIPLIER

    deviation = random.uniform(*GAS_DEVIATION)
    effective_multiplier = GAS_MULTIPLIER + deviation
    custom_gas = int(base_gas * effective_multiplier)
    final_gas = min(max(custom_gas, MIN_GAS_LIMIT), MAX_GAS_LIMIT)
    return final_gas, effective_multiplier


def mint_token(web3, private_key, count=1):
    account = web3.eth.account.from_key(private_key)

    # Базовые параметры транзакции
    base_tx = {
        'chainId': CHAIN_ID,
        'to': Web3.to_checksum_address(CONTRACT_ADDRESS),
        'data': '0xa0712d68' + f'{count:0>64x}',
        'value': Web3.to_wei(0.01, 'ether'),
        'gasPrice': int(web3.eth.gas_price * 1.15),
        'nonce': web3.eth.get_transaction_count(account.address),
    }

    try:
        gas_estimate = web3.eth.estimate_gas({
            'to': base_tx['to'],
            'data': base_tx['data'],
            'value': base_tx['value'],
            'from': account.address
        })
    except Exception as e:
        print(f"Ошибка оценки газа: {e}")
        gas_estimate = None

    # Получаем оба значения из функции
    custom_gas, effective_multiplier = generate_custom_gas(gas_estimate)
    base_tx['gas'] = custom_gas

    print(f"Gas: base={gas_estimate} custom={custom_gas} "
          f"multiplier={effective_multiplier:.3f}x")

    # Остальная часть функции без изменений...
    # ...

    # Проверка баланса
    balance = web3.eth.get_balance(account.address)
    required = base_tx['value'] + (base_tx['gas'] * base_tx['gasPrice'])

    if balance < required:
        raise Exception(f"Недостаточно средств. Нужно: {Web3.from_wei(required, 'ether'):.6f} MON")

    try:
        signed_tx = web3.eth.account.sign_transaction(base_tx, private_key)
        return web3.eth.send_raw_transaction(signed_tx.rawTransaction).hex()
    except Exception as e:
        raise Exception(f"Ошибка отправки: {str(e)}")


def main():
    web3 = Web3(Web3.HTTPProvider(RPC_URL))
    private_keys = load_private_keys(PRIVATE_KEYS_FILE)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f'mint_results_{timestamp}.txt'

    print(f"Найдено кошельков: {len(private_keys)}")
    print(f"Текущий Gas Price: {web3.from_wei(web3.eth.gas_price, 'gwei'):.2f} Gwei")

    with open(results_file, 'w', encoding='utf-8') as f:
        f.write("Адрес | Статус | Баланс | TX Hash\n")
        f.write("-" * 50 + "\n")

        for idx, pk in enumerate(private_keys):
            account = web3.eth.account.from_key(pk)
            status = "Ошибка"
            tx_hash = ""
            balance = 0.0

            try:
                print(f"\n[{idx + 1}/{len(private_keys)}] Обработка {account.address}")
                tx_hash = mint_token(web3, pk)
                status = "Успешно"
                print(f"TX Hash: {tx_hash}")

            except Exception as e:
                status = f"Ошибка: {str(e)}"
                print(status)

            finally:
                balance = web3.from_wei(web3.eth.get_balance(account.address), 'ether')
                f.write(f"{account.address} | {status} | {balance:.6f} MON | {tx_hash}\n")

                if idx < len(private_keys) - 1 and status == "Успешно":
                    delay = random.randint(DELAY_MIN, DELAY_MAX)
                    print(f"Пауза {delay} сек...")
                    time.sleep(delay)

    print(f"\nРезультаты сохранены в {results_file}")


if __name__ == "__main__":
    main()