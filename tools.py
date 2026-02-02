import logging

logger = logging.getLogger(__name__)

def sanitize_text(text):
    if not text:
        return ''
    return text.replace('\n', ' ').strip()


def save_token_to_env(token):
    try:
        with open('.env', 'a', encoding='utf-8') as f:
            f.write(f"\nACCOUNT_HASH={token}\n")
        logger.info(f"Токен сохранен в файл .env")
    except OSError as e:
        logger.error(f"Не удалось сохранить токен: {e}")