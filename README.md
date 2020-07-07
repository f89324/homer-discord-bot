# Homer-bot


![homer-logo](https://github.com/f89324/homer-discord-bot/blob/develop/resources/homer.png)   
Exclusive bot for Donut Hole server.

<a name="requirements"></a>
### Requirements
*  python3
*  all dependencies from `requirements.txt`
*  ffmpeg


### Running the Bot
1. Ensure that all [requirements](#requirements) is installed.
2. Export  the [environments variables](#env).
3. `python3 homer.py`


### Permissions bot need to work 
* `VIEW_CHANNEL` - To read text channels & see voice channels.
* `READ_MESSAGE_HISTORY` - To read command messages.
* `SEND_MESSAGES` - To answer your commands and send notification messages.
* `CONNECT` - To join to a voice channel.
* `SPEAK` - To play audio in a voice channel.


### Basic Commands
* `help` - Prints a list of commands.
* `join` - Joins a voice channel.
* `leave` - Leaves a voice channel.
* `play` - Plays from a url (doesn't pre-download).
* `stop` - Stops playing to voice.
* `volume` - Changes the bot's volume.
* `pause` - Pauses the audio playing.
* `resume` - Resumes the audio playing.
* `now_playing` - Display information about the currently playing song.
 
 
<a name="env"></a>
### Environment Variables
* `DISCORD_TOKEN`(Required) - The Discord Bot token.
* `AUTHORIZED_GUILD_ID`(Optional) - list of authorized guild ids. 
* `DEBUG_ENABLED`(Optional) - Flag for debug logging. (\'true\' or \'false\')
* `MEMBERS_WITH_INTRO`(Optional) - Dictionary {id -> intro filename}.