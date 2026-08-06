"""State untuk ConversationHandler. Dipisah ke file sendiri supaya
handlers/menu.py dan handlers/conversation.py bisa saling mengimpor
tanpa circular import."""
CHOOSING_CATEGORY, CHOOSING_ACTION, WAITING_FILE, WAITING_MORE_FILES, WAITING_PARAM = range(5)
