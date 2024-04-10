import toml
import sqlite3 as sqlite
from telegram.ext import Application, MessageHandler, ContextTypes, filters
from telegram import Update
import hashlib

class relayBot:
	def __init__(self) -> None:
		create_db()
		self.setup()
		
	def setup(self):
		loadedConfig = toml.load("config.toml")["Config"]
		self.strings = toml.load("config.toml")["Strings"]
		self.destination_Id = loadedConfig["destinationID"]
		self.commandPrefix = loadedConfig["commandPrefix"]
		self.application = Application.builder().token(loadedConfig["token"]).build()
		self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_update))
		self.splitter = "­⁮­⁮"
	
	async def handle_update(self,update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
		# If its a normal message
		if (update.message                                                  # It has a message
	  		and not update.message.reply_to_message                         # Its not a reply 
			and update.message.from_user.id != self.destination_Id          # Message is from some random
			):
			if user_is_blocked(update.message.from_user.id):
				await context.bot.sendMessage(update.message.chat.id, f"You are currently blocked from contacting {self.strings['name']}.")
				return
			
			# User is not blocked, prepare content
			messageText = update.message.text
			senderUsername = update.message.from_user.name
			
			
			encoded_chat_id = encode_chat_id(update.message.from_user.id)			
			uniqueIdentifierHash = hashlib.md5(str(update.message.from_user.id).encode('utf-8')).hexdigest()[0:6]
	
			# Content ready, SEND IT!			
			await context.bot.sendMessage(self.destination_Id, f"[{senderUsername}#{uniqueIdentifierHash}] - {messageText}{self.splitter}{encoded_chat_id}")
		
		# If its a reply by the owner of the bot
		elif (update.message.reply_to_message                               # Its a reply
			  and update.message.chat.id == self.destination_Id             # Its in the destination chat (aka owner)
			  and update.message.from_user.id == self.destination_Id        # Its from the owner
			):

			messageText = update.message.text
			responseId = int(decode_chat_id(update.message.reply_to_message.text.split(self.splitter)[-1]))
			
			#Handle Commands here
			if messageText.startswith(self.commandPrefix):
				match messageText[1:].lower():
					case "help":
						await context.bot.sendMessage(self.destination_Id,f"""Commands
							{self.commandPrefix}help - Shows this message
							{self.commandPrefix}block - Blocks the user from contacting the bot
							{self.commandPrefix}unblock - Unblocks the user from contacting the bot""" )
						return
					case "block":
						connection, cursor = getDBC()
						cursor.execute("INSERT INTO BlockedUsers VALUES (?)", (responseId,))
						connection.commit()
						connection.close()
						await context.bot.sendMessage(self.destination_Id, f"User blocked.")
						return
					case "unblock":
						connection, cursor = getDBC()
						try:
							cursor.execute("DELETE FROM BlockedUsers WHERE userId = ?", (responseId,))
							connection.commit()
							connection.close()
							await context.bot.sendMessage(self.destination_Id, f"User unblocked.")
							return
						except:
							connection.close()
							await context.bot.sendMessage(self.destination_Id, f"User is not blocked.")
							return
					case _:
						await context.bot.sendMessage(self.destination_Id,f"""Commands
							{self.commandPrefix}help - Shows this message
							{self.commandPrefix}block - Blocks the user from contacting the bot
							{self.commandPrefix}unblock - Unblocks the user from contacting the bot""" )
						return

			# Commands over
			
			# Send message to people
			await context.bot.sendMessage(responseId, messageText)
			
	def start(self):
		self.application.run_polling(allowed_updates=Update.ALL_TYPES)
			
# DB shit
def getDBC():
	connection = sqlite.connect('blockedUsers.db')
	cursor = connection.cursor()
	return connection, cursor

def create_db():
	connection, cursor = getDBC()
	cursor.execute('''
		CREATE TABLE IF NOT EXISTS BlockedUsers (
			userId INTEGER
		)''')
	connection.commit()
	connection.close()	

def user_is_blocked(user_id):
	_, cursor = getDBC()
	cursor.execute("SELECT userId FROM BlockedUsers WHERE userId = ?", (user_id,))
	if cursor.fetchone():
		# User is blocked
		return True
	# User is not blocked
	return False

def encode_chat_id(id:int):
	chars = {"zeroWidthSpace":"­","nationalDigitShapes":"⁮"} # These are 2 invisible chars used to en/decode the chatId
	return ''.join([f"{chars['zeroWidthSpace'] * int(number)}{chars['nationalDigitShapes']}" for number in str(id)])

def decode_chat_id(id:str):
    chars = {"zeroWidthSpace": "­", "nationalDigitShapes": "⁮"}
    return int(''.join([str(len(number)) for number in id.split(chars['nationalDigitShapes'])[:-1]]))
    

if __name__ == "__main__":
	bot = relayBot()
	bot.start()