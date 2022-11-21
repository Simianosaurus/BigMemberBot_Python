import logging

import os
import json
import validators
import datetime
from telegram import Update, Chat, ChatMember, ChatMemberUpdated, ParseMode
from telegram.ext import Updater, CommandHandler, MessageHandler, ChatMemberHandler, Filters

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

# TODO:
# 1) Process the profile and store the profile name when first added and save that.
#    this way, I could add a way of using a different display username (instead of the case like 12232221)
#    It also means less processing as it runs.
# 2) Allow a way of marking another message as an 'About' or 'Intro' post which can be linked to from the member list
#    Perhaps by posting it with /intro, or if that is forgotten having anyone / admin reply to it with /intro
# 3) sort out the await issues

# Define a few command handlers. These usually take the two arguments update and
# context. Error handlers also receive the raised TelegramError object in error.

FILE_AUTHORISED_USERS = "authorisedUsers"
FILE_DOMAIN_TAGS = "domainTags_"
FILE_CHAT_DATA = "chatData_"

PASSWORD = "bigscarydino"

CMD_HELP = "help"
CMD_AUTHORISE = "authorise"
CMD_ADD_TAG = "addTag"
CMD_DELETE_TAG = "deleteTag"
CMD_LIST_TAGS = "listTags"
CMD_SET_PROFILE = "setprofile"
CMD_ADD_PROFILE = "addprofile"
CMD_CLEAR_PROFILES = "clearprofiles"

MAX_TAG_LENGTH = 10
MAX_PROFILE_LENGTH = 200
MAX_PROFILES_PER_MEMBER = 10

MAX_MESSAGE_LENGTH = 4096

class BotData:
	class MemberData(dict):
		def __init__(self, firstName, lastName, username, profiles, timestamp):
			dict.__init__(
				self
				, firstName=firstName
				, lastName=lastName
				, username=username
				, profiles=profiles
				, timestamp=timestamp
			)

	class ChatData(dict):
		def __init__(self):
			dict.__init__(
				self 
				,memberData = {} # "User.Id" -> MemberData
			)

	memberListMessagesIds = {}	# Chat.Id -> MemberListMessageIds[]
	authorisedUsers = {}		# "User.Id" -> TRUE
	chatData = {}				# Chat.Id -> ChatData
	loadedChatData = {}		# Chat.Id -> TRUE
	domainTags = {}			# DomainName -> Tag
	memberSortOrder = []

def onHelp(update, context):
	#Recieved a help command
	if update.effective_chat.type == update.effective_chat.PRIVATE :
		# Private Help
		update.effective_message.reply_html(
			disable_notification = True
			, disable_web_page_preview = True
			, text = "<u><b>Authorising</b></u>\n" +
				"To authorise this bot so that you can use it in groups, us use the \"/authorise\" command and pass it the password.\n" +
				"\n<u><b>Enabling</b></u>\n" +
				"You must ensure the you have <i>Chat History</i> set to <i>Visible</i> and then once the bot has been added to your group, " +
				"you must give it admin rights so it can post and pin messages.\n\n" +
				"<u><b>Resetting</b></u>\n" +
				"If something goes wrong with the bot, or the pinned message is deleted " +
				"you should be able to reset the bot by simply removing and re-adding the admin rights for the bot.\n\n" +
				"<u><b>DirectCommands</b></u>\n" +
				"You can send commands by in here by typing a \'/\' followed by one of the following:\n" +
				"\n<b>authorise</b> - If you use specify the correct password, you will be authorised to use the bot.\n" +
				"<i>Usage: \"/authorise password\"</i>\n\n" +
				"<u><b>Group Commands</b></u>\n" +
				"You can send these commands in the group by typing a \'/\' followed by one of the following:\n" +
				"\n<b>setprofile</b> - Replaces your profiles with a supplied list.\n" +
				"<i>Usage: \"/setprofile www.mysite.com/BigMemberBot, www.othersite.com/BigMemberBot\"</i>\n" +
				"\n<b>addprofile</b> - Adds to your profiles with a supplied list.\n" +
				"<i>Usage: \"/addprofile www.mysite.com/BigMemberBot, www.othersite.com/BigMemberBot\"</i>\n" +
				"\n<b>clearprofile</b> - Clears your profiles.\n" +
				"<i>Usage: \"/clearprofile\"</i>\n" +
				"\n<b>addtag</b> - [Authorised Only] Adds a profile domain tag that will be shown in [] next to the profile.\n" +
				"<i>Usage: \"/addtag mysite.com MYS\"</i>\n" +
				"\n<b>deletetag</b> - [Authorised Only] Deletes a profile domain tag.\n" +
				"<i>Usage: \"/deletetag mysite.com\"</i>\n" +
				"\n<b>listtags</b> - [Authorised Only] Shows a list of all profile domain tags.\n" +
				"<i>Usage: \"/listtags\"</i>\n"
		)
	else:
		# Group Help
		update.effective_message.reply_html(
			disable_notification = True
			, disable_web_page_preview = True
			, text = "<u><b>Setting Profiles</b></u>\n" +
				"You can set the profiles to show under your name in the pinned members list.\n\n" +
				"The simple way to do this is to reply to the pinned members list with a list of URLs for your profiles.\n" +
				"This will replace any existing profiles.\n" +
				"<i>Usage: (in reply) \"www.mysite.com/BigMemberBot, www.othersite.com/profiles/BigMemberBot\"</i>\n\n" +
				"<u><b>Commands</b></u>\n" +
				"You can send commands by typing a \'/\' followed by one of the following:\n" +
				"\n<b>setprofile</b> - Replaces your profiles with a supplied list.\n" +
				"<i>Usage: \"/setprofile www.mysite.com/BigMemberBot, www.othersite.com/BigMemberBot\"</i>\n" +
				"\n<b>addprofile</b> - Adds to your profiles with a supplied list.\n" +
				"<i>Usage: \"/addprofile www.mysite.com/BigMemberBot, www.othersite.com/BigMemberBot\"</i>\n" +
				"\n<b>clearprofile</b> - Clears your profiles.\n" +
				"<i>Usage: \"/clearprofile\"</i>\n"
			)

def onAuthorise(update, context):
	#Authorise the user to use the bot	
	if update.effective_chat.type == update.effective_chat.PRIVATE :
		# If the user sent the password directly, add them as a good user to add the bot to groups
		if isUserAuthorised(update.effective_user.id, False):
			update.effective_message.reply_html(disable_notification = True, text = "Already authorised")
		elif update.effective_message.text[10:].strip() == PASSWORD:
			authoriseUser(update.effective_chat, update.effective_user.id)
		else:
			update.effective_message.reply_html(disable_notification = True, text = "Incorrect password")

def onChatMemberEvent(update, context):
	if update.effective_chat is None or update.effective_chat.bot is None:
		return

	if update.effective_chat.type == update.effective_chat.PRIVATE :
		return

	if update.chat_member is None:
		return

	changes = update.chat_member.difference()

	statusChanges = changes["status"]
	if statusChanges:
		if ( (statusChanges[0] == update.chat_member.old_chat_member.KICKED or statusChanges[0] == update.chat_member.old_chat_member.LEFT )
			and ( statusChanges[1] != update.chat_member.new_chat_member.KICKED and statusChanges[1] != update.chat_member.new_chat_member.LEFT )):
				addMember(update.effective_chat, update.chat_member.new_chat_member.user)
		elif ( (statusChanges[0] != update.chat_member.old_chat_member.KICKED and statusChanges[0] != update.chat_member.old_chat_member.LEFT )
			and ( statusChanges[1] == update.chat_member.new_chat_member.KICKED or statusChanges[1] == update.chat_member.new_chat_member.LEFT )):
				removeMember(update.effective_chat, update.chat_member.new_chat_member.user)
		
		if ( ( statusChanges[0] != update.chat_member.old_chat_member.ADMINISTRATOR and statusChanges[0] != update.chat_member.old_chat_member.CREATOR )
			and ( statusChanges[1] == update.chat_member.new_chat_member.ADMINISTRATOR or statusChanges[1] == update.chat_member.old_chat_member.CREATOR )):
			# User became admin.
			# Reload auth. This ensures new admin check the current data
			loadAuthorisedUsers()

def onMyChatMemberEvent(update, context):
	if update.effective_chat is None or update.effective_chat.bot is None:
		return

	if update.effective_chat.type == update.effective_chat.PRIVATE :
		# Private
		sendSimpleMessage(update.effective_chat.bot, update.effective_chat.id
			,"<u><b>Authorising</b></u>\n" +
				"To authorise this bot so that you can use it in groups, us use the \"/authorise\" command and pass it the password.\n" +
				"\n<u><b>Enabling</b></u>\n" +
				"You must ensure the you have <i>Chat History</i> set to <i>Visible</i> and then once the bot has been added to your group, " +
				"you must give it admin rights so it can post and pin messages.\n\n" +
				"<u><b>Resetting</b></u>\n" +
				"If something goes wrong with the bot, or the pinned message is deleted " +
				"you should be able to reset the bot by simply removing and re-adding the admin rights for the bot.\n\n" +
				"For additional help use the \"/help\" command."
		)
	else:
		# Group
		if update.my_chat_member is None:
			return

		changes = update.my_chat_member.difference()

		statusChanges = changes["status"]
		if statusChanges:
			if ( (statusChanges[0] == update.my_chat_member.old_chat_member.KICKED or statusChanges[0] == update.my_chat_member.old_chat_member.LEFT )
				and ( statusChanges[1] != update.my_chat_member.new_chat_member.KICKED and statusChanges[1] != update.my_chat_member.new_chat_member.LEFT )):
					onBotAdded(update.effective_chat, update.my_chat_member.from_user.id)
			elif ( (statusChanges[0] != update.my_chat_member.old_chat_member.KICKED and statusChanges[0] != update.my_chat_member.old_chat_member.LEFT )
				and ( statusChanges[1] == update.my_chat_member.new_chat_member.KICKED or statusChanges[1] == update.my_chat_member.new_chat_member.LEFT )):
					onBotRemoved(update.effective_chat)
			elif ( statusChanges[0] != update.my_chat_member.old_chat_member.ADMINISTRATOR and statusChanges[1] == update.my_chat_member.old_chat_member.ADMINISTRATOR ):
				onBotPromotedToAdmin(update.effective_chat, update.my_chat_member.from_user)
			elif ( statusChanges[0] == update.my_chat_member.old_chat_member.ADMINISTRATOR and statusChanges[1] != update.my_chat_member.old_chat_member.ADMINISTRATOR ):
				onBotDemotedFromAdmin(update.effective_chat)


def onMessage(update, context):
	if update.effective_user.is_bot:
		return

	# Check if this is a reply to the MemberListMessage
	if ( update.effective_message.reply_to_message
		and isMemberListMessageId(update.effective_message.chat_id, update.effective_message.reply_to_message.message_id)):
			# Replying to MemberList message
			profiles = update.effective_message.text.split()
			if len(profiles) == 0:
				return

			alterProfile(update.effective_chat, update.effective_user, profiles, True)

	# Give the member an update if needed
	updateMember(update.effective_chat, update.effective_message.from_user)

def onError(update, context):
	#Log Errors caused by Updates.
	logger.warning('Update "%s" caused error "%s"', update, context.error)

def onAddTag(update, context):
	if update.effective_chat.type == update.effective_chat.PRIVATE :
		sendSimpleMessage(update.effective_chat.bot, update.effective_chat.id, "Failed to add tag - must be in a group")
		return False

	if not isUserAuthorised(update.effective_user.id):
		sendSimpleMessage(update.effective_chat.bot, update.effective_chat.id, "Failed to add tag - not authorised")
		return False

	splitCommand = update.effective_message.text.split()
	if len(splitCommand) != 3:
		sendSimpleMessage(update.effective_chat.bot, update.effective_chat.id, "Failed to add tag - incorrect args")
		return False

	domain = splitCommand[1].casefold()
	tag = splitCommand[2]

	if leg(tag) > MAX_TAG_LENGTH:
		sendSimpleMessage(update.effective_chat.bot, update.effective_chat.id, "Failed to add tag - too long (Max = " + MAX_TAG_LENGTH + ")")
		return False

	if any(elem in "/\\@" for elem in domain):
		sendSimpleMessage(update.effective_chat.bot, update.effective_chat.id, "Failed to add tag - invalid domain")
		return False

	if BotData.domainTags.get(domain):
		sendSimpleMessage(update.effective_chat.bot, update.effective_chat.id, "Failed to add tag - domain already exists")
		return False

	BotData.domainTags[domain] = tag

	saveDomainTags(update.effective_chat)

	sendSimpleMessage(update.effective_chat.bot, update.effective_chat.id, "Succeeded to add tag " + domain)
	return True

def onDeleteTag(update, context):
	if update.effective_chat.type == update.effective_chat.PRIVATE:
		sendSimpleMessage(update.effective_chat.bot, update.effective_chat.id, "Failed to delete tag - must be in a group")
		return False

	if not isUserAuthorised(update.effective_user.id):
		sendSimpleMessage(update.effective_chat.bot, update.effective_chat.id, "Failed to delete tag - not authorised")
		return False

	splitCommand = update.effective_message.text.split()
	if len(splitCommand) != 2:
		sendSimpleMessage(update.effective_chat.bot, update.effective_chat.id, "Failed to delete tag - incorrect args")
		return False

	domain = splitCommand[1]

	if not BotData.domainTags.get(domain):
		sendSimpleMessage(update.effective_chat.bot, update.effective_chat.id, "Failed to delete tag - domain already exists")
		return False

	saveDomainTags(update.effective_chat)

	BotData.domainTags.pop(domain)

	sendSimpleMessage(update.effective_chat.bot, update.effective_chat.id, "Succeeded to delete tag " + domain)
	return True

def onListTags(update, context):
	if update.effective_chat.type == update.effective_chat.PRIVATE:
		sendSimpleMessage(update.effective_chat.bot, update.effective_chat.id, "Failed to list tags - must be in a group")
		return False

	if not isUserAuthorised(update.effective_user.id):
		sendSimpleMessage(update.effective_chat.bot, update.effective_chat.id, "Failed to list tags - not authorised")
		return False

	messageText = "<b>Tags</b>\n"

	if len(BotData.domainTags) == 0:
		messageText += "None"
	else:
		for domain in BotData.domainTags:
			messageText += "Domain: " + domain + " = Tag: " + BotData.domainTags[domain] + "\n"

	sendSimpleMessage(update.effective_chat.bot	, update.effective_chat.id, messageText)

def onSetProfile(update, context):
	if update.effective_chat.type == update.effective_chat.PRIVATE:
		sendSimpleMessage(update.effective_chat.bot, update.effective_chat.id, "Failed set profile - must be in a group")
		return False

	profiles = update.effective_message.text.split()
	if len(profiles) < 2:
		sendSimpleMessage(update.effective_chat.bot, update.effective_chat.id, "Failed set profile - incoorect args")
		return False

	# Remove the actual command, leaving the args
	profiles.pop(0)

	alterProfile(update.effective_chat, update.effective_user, profiles, False)

def onAddProfile(update, context):
	if update.effective_chat.type == update.effective_chat.PRIVATE:
		sendSimpleMessage(update.effective_chat.bot, update.effective_chat.id, "Failed add profile - must be in a group")
		return False

	profiles = update.effective_message.text.split()
	if len(profiles) < 2:
		sendSimpleMessage(update.effective_chat.bot, update.effective_chat.id, "Failed set profile - incoorect args")
		return False

	# Remove the actual command, leaving the args
	profiles.pop(0)

	alterProfile(update.effective_chat, update.effective_user, profiles, True)

def onClearProfiles(update, context):
	if update.effective_chat.type == update.effective_chat.PRIVATE:
		sendSimpleMessage(update.effective_chat.bot, update.effective_chat.id, "Failed clear profiles - must be in a group")
		return False

	alterProfile(update.effective_chat, update.effective_user, [], False)

def alterProfile(chat, user, profiles, asAddition):
	if user == None:
		return

	if user.is_bot:
		return

	chatId = chat.id
	userIdStr = str(user.id)

	# If the ChatData or MemberData within it doesn't exist, add the member first.
	if ( not BotData.chatData.get(chatId)
		or not BotData.chatData[chatId]["memberData"].get(userIdStr)):
			if addMember(chat, user) == False:
				return

	changesMade = False

	validProfiles = []
	if asAddition:
		# Potentially adding to old data
		validProfiles = BotData.chatData[chatId]["memberData"][userIdStr]["profiles"]
	elif len(BotData.chatData[chatId]["memberData"][userIdStr]["profiles"]) > 0:
		# Splatting old data
		changesMade = True

	for profile in profiles:
		# Remove pre and post spaces.
		profile = profile.strip()
		profile = profile.rstrip(',/')

		#Cap the profile length
		if len(profile) > MAX_PROFILE_LENGTH:
			continue

		# URL sanitising
		# Strip the scheme (storing if it was secure or not)
		# Strip www. or m. as these shouldn't be needed and can cause issues if used wrong on some badly made sites
		# Prepend the correct scheme based on if it's secure, to ensure there is always one there
		isUrl = False
		isSecure = False

		if profile[:8].casefold() == "https://":
			profile = profile[8:]
			isUrl = True
			isSecure = True
		elif profile[:7].casefold() == "http://":
			profile = profile[7:]
			isUrl = True

		if profile[:4].casefold() == "www.":
			profile = profile[4:]
			isUrl = True
		elif profile[:2].casefold() == "m.":
			profile = profile[2:]
			isUrl = True

		if isUrl == False:
			continue

		if isSecure:
			profile = "https://" + profile
		else:
			profile = "http://" + profile

		if not validators.url(profile):
			continue

		if profile.casefold() in validProfiles:
			continue

		validProfiles.append(profile)
		changesMade = True

		# Cap the #profiles each member can have
		if len(validProfiles) >= MAX_PROFILES_PER_MEMBER:
			break

	if changesMade == False:
		return

	# Store the profiles
	BotData.chatData[chatId]["memberData"][userIdStr]["profiles"] = validProfiles

	# Save the data
	saveChatData(chat)

def onBotAdded(chat, byUserId):
	#The bot was added to a chat

	if not isUserAuthorised(byUserId):
		# Not authorised
		sendSimpleMessage(chat.bot, chat.id
			, "You are not authorised to add me to groups\n" +
				"Talk to me directly to get authorised.\n" +
				"I'm leaving the group now, goodbye."
		)

		chat.bot.leave_chat(chat.id)
		return

	# Authorised
	sendSimpleMessage(chat.bot, chat.id
		, "Please ensure <i>Chat History</i> is set to <i>Visible</i> " +
			"and then promote me to an Admin so I can manage messages properly."
	)

def onBotRemoved(chat):
	#The bot was removed from a chat
	removeChat(chat.id)

def onBotPromotedToAdmin(chat, byUser):
	#The bot became admin
	sendSimpleMessage(chat.bot, chat.id
		, "Thanks for making me an admin, I'll now start working."
	)

	loadAuthorisedUsers()
	loadDomainTags(chat.id)
	addChat(chat)

	# Add the admin that add the bot to the list, as this will load latest and start things going
	addMember(chat, byUser)

def onBotDemotedFromAdmin(chat):
	#The bot is no longer admin
	removeChat(chat.id)

def isUserAuthorised(userId, reloadOnNonAuth=True):
	userIdStr = str(userId)
	isAuth = BotData.authorisedUsers.get(userIdStr)

	if not isAuth and reloadOnNonAuth == True:
		loadAuthorisedUsers()
		isAuth = BotData.authorisedUsers.get(userIdStr)

	return isAuth

	
def authoriseUser(chat, userId):
	#Authorise a user

	if isUserAuthorised(userId, False):
		return

	BotData.authorisedUsers[str(userId)] = True

	saveAuthorisedUsers()

	sendSimpleMessage(chat.bot, chat.id
		, "You are now authorised to add me to groups"
	)

def addChat(chat):
	chatId = chat.id

	loadChatData(chat)

	# If the ChatData for this chat does not exist, create it.
	if BotData.chatData.get(chatId):
		return

	BotData.chatData[chatId] = BotData.ChatData()

	saveChatData(chat, False)

def removeChat(chatId):
	# Remove the message id, and say we have removed the data, but actually don't bother
	if BotData.memberListMessagesIds.get(chatId):
		BotData.memberListMessagesIds.pop(chatId)

	if BotData.loadedChatData.get(chatId):
		BotData.loadedChatData.pop(chatId)

def addMember(chat, user):
	if user == None:
		return False

	if user.is_bot:
		return False

	chatId = chat.id
	userIdStr = str(user.id)

	# If the ChatData for this chat does not exist, drop out
	if not BotData.chatData.get(chatId):
		return False

	# Get the ChatData for this chat
	chatData = BotData.chatData[chatId]

	#If the MemberData for this member already exists, drop out
	if chatData["memberData"].get(userIdStr):
		return True

	# Store the MemberData for this member in the ChatData.
	chatData["memberData"][userIdStr] = BotData.MemberData( 
		username = user.username
		,firstName = user.first_name
		,lastName = user.last_name
		,profiles = []
		,timestamp = datetime.datetime.now().timestamp()
	)

	BotData.memberSortOrder.append(userIdStr)
	sortMembers(chat)

	saveChatData(chat)

	return True

def removeMember(chat, user):
	# If the ChatData for this chat does not exist, drop out
	if not BotData.chatData.get(chat.id):
		return False

	# Get the ChatData for this chat
	chatData = BotData.chatData[chat.id]

	userIdStr = str(user.id)

	#If the MemberData for this member does not exist, drop out
	if not chatData["memberData"].get(userIdStr):
		return True
	
	# Remove the MemberData for this member
	chatData["memberData"].pop(userIdStr)

	BotData.memberSortOrder.remove(userIdStr)
	sortMembers(chat)

	saveChatData(chat)

def isMemberAdmin(chat, memberIdStr):
	chatMember = chat.get_member(int(memberIdStr))
	return (chatMember and (chatMember.status == chatMember.ADMINISTRATOR or chatMember.status == chatMember.CREATOR) )

def memberSortCompare(chat, memberIdStr):
	# TODO Admin at the top
	
	chatData = BotData.chatData[chat.id]

	isAdmin = isMemberAdmin(chat, memberIdStr)
	
	# using (not isAdmin) as False is lower than True, and we want admin first
	return (not isAdmin), chatData["memberData"][memberIdStr]["firstName"]

def sortMembers(chat):
	# If the ChatData for this chat does not exist, drop out
	if not BotData.chatData.get(chat.id):
		return False

	BotData.memberSortOrder.sort(key=lambda memberIdStr: memberSortCompare(chat, memberIdStr))

def isMemberListMessageId(chatId, messageId):
	memberListMessageIds = BotData.memberListMessagesIds.get(chatId)
	if not memberListMessageIds:
		return False

	return (messageId in memberListMessageIds)

def updateMembersListMessage(chat):
	chatId = chat.id

	if not BotData.loadedChatData.get(chatId):
		return

	if not BotData.chatData.get(chatId):
		return

	chatData = BotData.chatData[chatId]

	# Start forming the message text
	# TODO determine potential split points, and if the message exceeds > MAX_MESSAGE_LENGTH, split the message at the last one.
	# Repeat...
	# Post a blank message for each part to get the IDs
	# Add the ID for the next message onto the previous
	# Edit the blank messages with the correct part

	messagePages = [""]
	messagePageCount = 1
	messagePageLength = 0

	# A message at the end saying what to do
	endOfMessageText = "---------------\n\n"
	endOfMessageText += "To list profiles under your name, reply to this message with their URLs.\n"
	endOfMessageText += "\nFor more details click or type \"/help\""
	endOfMessageLength = len(endOfMessageText)

	maxPageLength = 1000#MAX_MESSAGE_LENGTH - endOfMessageLength

	pageMessageText = "<b><u>USERNAMES & PROFILES</u></b>\n\n"

	# Add each (if any) member
	if len(BotData.memberSortOrder) > 0:

		listingAdmins = False

		# Show the admin title if we need to
		if isMemberAdmin(chat, BotData.memberSortOrder[0]):
			pageMessageText += "<b>ADMINS</b>\n\n"
			listingAdmins = True

		for memberId in BotData.memberSortOrder:
			memberData = chatData["memberData"][memberId]

			if listingAdmins and not isMemberAdmin(chat, memberId):
				pageMessageText += "---------------\n\n"
				listingAdmins = False
		
			# Add the name and username
			displayName = ""
			if not memberData["lastName"]:
				displayName = memberData["firstName"]
			elif not memberData["firstName"]:
				displayName = memberData["lastName"]
			else:
				displayName = memberData["firstName"] + " " + memberData["lastName"]

			# Member Text
			pageMessageText += "<b><a href = \"tg://user?id=" + str(memberId) + "\">" + displayName + "</a>"
			if memberData["username"]:
				pageMessageText += " - @" + memberData["username"]

			pageMessageText += "</b>"

			if len(memberData["profiles"]) == 0:
				# Shift down ready for the next text
				pageMessageText += "\n\n"
			else:
				# Add each of the members profiles
				pageMessageText += "\n"

				for profile in memberData["profiles"]:
					foundTagAndUser = False
					for domain in BotData.domainTags:							# bob.com
						if domain in profile.casefold():						# bob.com in http://bob.com or http://bob.com/user or http://bob.com/users/user
							domainTag = "[" + BotData.domainTags[domain] + "] "

							splitProfile = profile.rsplit('/', 1)				# http:/ | bob.com or http://bob.com | user or http://bob.com/users | user
							if len(splitProfile) == 2:
								# Show the username
								foundTagAndUser = True
								pageMessageText += domainTag + "<i><a href=\"" + profile + "\">" + splitProfile[1] + "</a></i>\n"	# user
							break
					
					if foundTagAndUser == False:
						# Show the full profile
						pageMessageText += "<i><a href=\"" + profile + "\">" + profile + "</a></i>\n"			# http://bob.com

			# Ensure the text segment has space to be added to the page
			messageSegmentLength = len(pageMessageText)
			potentialPageLength = messagePageLength + messageSegmentLength 
			if potentialPageLength < maxPageLength:
				messagePages[messagePageCount-1] += pageMessageText
				messagePageLength = potentialPageLength
			else:
				messagePageCount += 1
				messagePages.append(pageMessageText)
				messagePageLength = messageSegmentLength

			pageMessageText = ""

	# If there is only one page, edit the posted message or post a new one if none existed
	memberListMessageIds = BotData.memberListMessagesIds.get(chatId)
	messageToPageCountDifference = 0
	if memberListMessageIds:
		messageToPageCountDifference = messagePageCount - len(memberListMessageIds)
	else:
		messageToPageCountDifference = messagePageCount

	# If the number of stored messages > number of pages, delete the extra and remove the IDs
	# else post a blank message for each extra needed and store their message IDs
	if messageToPageCountDifference > 0:
		# Add messages
		for newMessageCount in range(0, messageToPageCountDifference):
			message = sendSimpleMessage(chat.bot, chatId, "Usernames Page: " + str(newMessageCount))
			if not memberListMessageIds:
				memberListMessageIds = [message.message_id]
			else:
				memberListMessageIds.append(message.message_id)
	elif messageToPageCountDifference < 0:
		# Delete pinned messages
		for deleteMessageIndex in range(0, -messageToPageCountDifference):
			chat.bot.delete_message(chat_id = chatId, message_id = memberListMessageIds[deleteMessageIndex])
			memberListMessageIds.pop(deleteMessageIndex)

	# We now have the correct amount of messages, so store them then edit them posting out each page
	BotData.memberListMessagesIds[chatId] = memberListMessageIds

	# No need to call save here to store the m_memberListMessageId
	# as this function is called from the save function to ensure it's all upto date.
	# So when the first save occurs, this would have been set and would have been saved

	# for each page except the last post a link to the next
	# for the last post the endOfMessageText 
	for messageIdIndex in range(0, messagePageCount):
		if messageIdIndex < messagePageCount-1:
			# Add a link to the next page
			messagePages[messageIdIndex] += "---------------\n"
			messagePages[messageIdIndex] += "<i><a href=\"https://t.me/c/" + str(chatId)[4:] + "/" + str(memberListMessageIds[messageIdIndex + 1]) + "\">Next Page</a></i>"
		else:
			# Add a message saying what to do
			messagePages[messageIdIndex] += endOfMessageText

		# Edit Messages
		try:
			chat.bot.edit_message_text(
				messagePages[messageIdIndex]
				, chat_id = chatId
				, message_id = memberListMessageIds[messageIdIndex]
				, parse_mode = ParseMode.HTML
				, disable_web_page_preview = True
			)
		except Exception:
			pass

	# Pin first message even if it already is, as we can not tell if it isn't.
	chat.bot.pin_chat_message(chatId, memberListMessageIds[0], disable_notification = True)


def updateMember(chat, user):
	if user == None:
		return False

	if user.is_bot:
		return False

	chatId = chat.id
	userIdStr = str(user.id)

	# If the ChatData or MemberData within it doesn't exist, just add the member
	if ( not BotData.chatData.get(chatId)
		or not BotData.chatData[chatId]["memberData"].get(userIdStr)):
			if addMember(chat, user) == False:
				return

	# If they did exist, update the user data to ensure it is the latest
	memberData = BotData.chatData[chatId]["memberData"][userIdStr]

	membersListRequiresUpdate = False

	if memberData["firstName"] != user.first_name:
		memberData["firstName"] = user.first_name
		membersListRequiresUpdate = True

	if memberData["lastName"] != user.last_name:
		memberData["lastName"] = user.last_name
		membersListRequiresUpdate = True

	if memberData["username"] != user.username:
		memberData["username"] = user.username
		membersListRequiresUpdate = True

	# We always want the time to update. If we didn't we could just not save if membersListRequiresUpdate was false
	memberData["timestamp"] = datetime.datetime.now().timestamp()

	saveChatData(chat, membersListRequiresUpdate)

def sendSimpleMessage(bot, chatId, message):
	return bot.send_message(
		chatId
		, parse_mode = ParseMode.HTML
		, disable_notification = True
		, text = message
		, disable_web_page_preview = True
	)

def loadAuthorisedUsers():
	filePath = FILE_AUTHORISED_USERS + ".json"
	if os.path.isfile(filePath):
		with open(filePath, 'r') as file:
			BotData.authorisedUsers = json.load(file)

def saveAuthorisedUsers():
	with open(FILE_AUTHORISED_USERS + ".json", 'w') as file:
		json.dump(BotData.authorisedUsers, file)

def loadDomainTags(chatId):
	filePath = FILE_DOMAIN_TAGS + str(chatId) +".json"
	if os.path.isfile(filePath):
		with open(filePath, 'r') as file:
			BotData.domainTags = json.load(file)

def saveDomainTags(chat):
	chatId = chat.id

	if not BotData.chatData.get(chatId):
		return

	updateMembersListMessage(chat)

	with open(FILE_DOMAIN_TAGS + str(chatId) + ".json", 'w') as file:
		json.dump(BotData.domainTags, file)

def loadChatData(chat):
	chatId = chat.id

	if BotData.loadedChatData.get(chatId):
		return

	# Store that the ChatData has been loaded (note: the presencse of the key is all that is needed. 'True' means nothing)
	BotData.loadedChatData[chatId] = True

	filePath = FILE_CHAT_DATA + str(chatId) +".json"
	if os.path.isfile(filePath):
		with open(filePath, 'r') as file:
			BotData.chatData[chatId] = json.load(file)

	# Fill out based on what loaded
	BotData.memberSortOrder.clear()
	if BotData.chatData:
		for memberId in BotData.chatData[chatId]["memberData"]:
			BotData.memberSortOrder.append(memberId)

	sortMembers(chat)

	# Ensure the member list message shows the latest Members
	updateMembersListMessage(chat)
	
def saveChatData(chat, membersListRequiresUpdate=True):
	chatId = chat.id

	if not BotData.chatData.get(chatId):
		return

	# Ensure the member list message shows the latest Members
	if membersListRequiresUpdate:
		updateMembersListMessage(chat)

	with open(FILE_CHAT_DATA + str(chatId) + ".json", 'w') as file:
		json.dump(BotData.chatData[chatId], file)

def main():
	#Start the bot.

	# Create the Updater and pass it your bot's token.
	# Make sure to set use_context=True to use the new context based callbacks
	# Post version 12 this will no longer be necessary
	updater = Updater("5697067002:AAHAAIC8SuvM7Y4OncV4w97wB0wmRio8k_g", use_context=True)

	# Get the dispatcher to register handlers
	dp = updater.dispatcher

	# on different commands - answer in Telegram
	dp.add_handler(CommandHandler(CMD_HELP, onHelp))
	dp.add_handler(CommandHandler(CMD_AUTHORISE, onAuthorise))
	dp.add_handler(CommandHandler(CMD_ADD_TAG, onAddTag))
	dp.add_handler(CommandHandler(CMD_DELETE_TAG, onDeleteTag))
	dp.add_handler(CommandHandler(CMD_LIST_TAGS, onListTags))
	dp.add_handler(CommandHandler(CMD_SET_PROFILE, onSetProfile))
	dp.add_handler(CommandHandler(CMD_ADD_PROFILE, onAddProfile))
	dp.add_handler(CommandHandler(CMD_CLEAR_PROFILES, onClearProfiles))

	# on noncommand i.e message - handle the message
	dp.add_handler(MessageHandler(Filters.text, onMessage))

	# on chat member changes - respond
	dp.add_handler(ChatMemberHandler(onChatMemberEvent, ChatMemberHandler.CHAT_MEMBER))
	dp.add_handler(ChatMemberHandler(onMyChatMemberEvent, ChatMemberHandler.MY_CHAT_MEMBER))

	# log all errors
	dp.add_error_handler(onError)

	# Start the Bot
	updater.start_polling(allowed_updates = [Update.CHAT_MEMBER, Update.MY_CHAT_MEMBER, Update.MESSAGE])

	# Preload the authorised users 
	loadAuthorisedUsers()

	# Run the bot until you press Ctrl-C or the process receives SIGINT,
	# SIGTERM or SIGABRT. This should be used most of the time, since
	# start_polling() is non-blocking and will stop the bot gracefully.
	updater.idle()

if __name__ == '__main__':
	main()