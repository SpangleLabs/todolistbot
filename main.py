import json

from todo_list_bot.bot import TodoListBot, BotConfig

if __name__ == '__main__':
    with open("config.json", "r") as f:
        config = BotConfig.from_json(json.load(f))
    bot = TodoListBot(config)
    bot.start()
