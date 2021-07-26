from menu import Menu, SentMenu


class MenuHandler:
    def __init__(self, client):
        self.client = client
        self.cache = {}

    def add_menu(self, sent_menu: 'SentMenu'):
        if sent_menu.chat_id not in self.cache:
            self.cache[sent_menu.chat_id] = {}
        self.cache[sent_menu.chat_id][sent_menu.msg_id] = sent_menu

    def send_menu(self, menu: 'Menu'):
        msg = self.client.send_message(menu)
        sent_menu = SentMenu(menu, msg)
        self.add_menu(sent_menu)

    def handle_callback(self, callback):
        chat_id = callback.chat_id
        msg_id = callback.msg_id
        if chat_id not in self.cache or msg_id not in self.cache[chat_id]:
            event.edit_message(buttons=None)
            event.answer("Sorry this menu was not recognised.")
        self.cache[chat_id][msg_id].handle_callback(callback)
        event.answer()
