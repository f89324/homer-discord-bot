# Homer-bot

![homer-logo](https://github.com/f89324/homer-discord-bot/blob/develop/resources/homer.png)  
Exclusive bot for Donut Hole server.

<a name="requirements"></a>
### Requirements
*  [python 3](https://www.python.org/downloads/)
*  [ffmpeg](https://ffmpeg.org/)
*  all dependencies from `requirements.txt`


### Setup
#### Running the bot
1. Ensure that all [requirements](#requirements) is installed.
2. Export  the [environments variables](#env).
3. `python3 homer.py`

<a name="env"></a>
#### Environment variables
* `DISCORD_TOKEN`(Required) - The Discord Bot token.
* `AUTHORIZED_GUILDS`(Optional) - list of authorized guild ids.
* `DEBUG_ENABLED`(Optional) - Flag for debug logging. (\'true\' or \'false\')
* `MEMBERS_WITH_INTRO`(Optional) - Dictionary {id -> intro filename}.


### Usage

#### Common behavior
* The bot will automatically connect to the audio channel if it is idle and someone enters the audio channel.
* The bot will automatically disconnect from the audio channel if the last person left.
* The bot will play personal intro music when specific people enter an active audio channel.

#### Basic commands
* `help` - Prints a list of commands.
* `join` - Joins a voice channel.
* `leave` - Leaves a voice channel.
* `play` - Plays from a url (doesn't pre-download).
* `stop` - Stops playing to voice.
* `volume` - Changes the bot's volume. If the command is called without an argument, the bot will respond with the current sound level.
* `pause` - Pauses the audio playing.
* `resume` - Resumes the audio playing.
* `now_playing` - Display information about the currently playing song.

#### Permissions bot need to work
* `VIEW_CHANNEL` - To read text channels & see voice channels.
* `READ_MESSAGE_HISTORY` - To read command messages.
* `SEND_MESSAGES` - To answer your commands and send notification messages.
* `CONNECT` - To join to a voice channel.
* `SPEAK` - To play audio in a voice channel.