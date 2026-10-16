# Discord DM setup

This fork adds Discord bot DMs for job matches, daily digests, matched Gmail
responses, and scraper health alerts. Telegram is optional and disabled by default.
For an existing installation, turn Telegram off in Settings if you only want Discord.

1. Create an application at <https://discord.com/developers/applications>.
2. Open **Bot**, create/reset the bot token, and copy it into your local `.env`:

   ```dotenv
   DISCORD_BOT_TOKEN=your_bot_token
   ```

   Keep the token private. Do not put it in GitHub, screenshots, or the user ID field.
3. In the application's **Installation** or **OAuth2 URL Generator**, create a
   server installation link with the `bot` scope and invite it to a server you own.
   Administrator permissions and privileged gateway intents are unnecessary for
   this outbound REST integration.
4. In Discord, enable **User Settings > Advanced > Developer Mode**. Right-click
   your profile and choose **Copy User ID**. Use your user ID, not a server/channel ID.
5. Allow direct messages from members of the shared server. If Discord refuses
   delivery, open a DM with the bot and check your privacy settings and blocks.
6. Copy `.env.example` to `.env` first if needed, then build this fork locally:

   ```sh
   docker compose up -d --build
   ```

   Rebuild the frontend too: upstream prebuilt images do not contain these settings.
   After changing the token later, recreate the backend with
   `docker compose up -d --force-recreate backend`.
7. Open **Settings > Notifications** (or **Accounts > Discord DMs** in the classic
   interface), enter your Discord user ID, and click **Send test DM**. The test
   works with automatic alerts off. A failed test reports an error instead of
   claiming delivery succeeded.
8. Enable **Discord DMs**. Set the score threshold and digest cron in Settings.
   The existing scheduler timezone controls the digest time.

No public URL, webhook, continuously connected gateway, or extra Discord library
is needed. The bot may appear offline while still delivering DMs. Job alerts
include the job URL; save/skip/applied actions are performed in the dashboard.
Telegram inline action buttons are not implemented as Discord interactions.

The authenticated `POST /api/discord/test` endpoint tests delivery;
`POST /api/notifications/digest` triggers the shared daily digest. Notifications
are sent only to the configured user ID. Discord rate limits are retried up to
two times for short delays; failed messages are not durably queued.

API references: [Create DM](https://docs.discord.com/developers/resources/user#create-dm),
[Create Message](https://docs.discord.com/developers/resources/message#create-message).
