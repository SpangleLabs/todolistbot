# Todo list bot

A simple telegram bot to browse, modify, and manage markdown-style todo lists saved on a local filesystem.

## Installation and running
1. Install with: `poetry install`
2. Setup config: Create a config file called config.json, with this format:
```
{
  "telegram": {
    "api_id": "",
    "api_hash": "",
    "bot_token": ""
  },
  "storage_dir": "todo/",
  "allowed_chat_ids": [],
}
```
   - Add your telegram ID, hash, and bot token
   - Add your telegram user ID to the "allowed_chat_ids" list, and any other user IDs or group chat IDs which are allowed to use the bot. (All users will share the same todo list folders. There may be issues if multiple users try and update a todo list at the same time)
   - Prometheus metrics port may be optionally configured with "prometheus_port" key, defaults to 8479 otherwise
3. Run with: `poetry run python main.py`

