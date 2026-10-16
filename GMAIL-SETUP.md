# Connect Gmail reply tracking

This is optional. Job searches, résumé tools and Discord alerts work without it.

## Get the credentials

1. Open [Google Cloud Console](https://console.cloud.google.com/) using the Google account you want to connect. Create or select a project named JobNavigator.
2. In APIs & Services → Library, enable **Gmail API**.
3. In **Google Auth Platform**, configure the app name and support/contact email. For a personal Gmail account choose **External**. While the app is in Testing, add your Gmail address under Audience → Test users.
4. Under **Clients**, create an OAuth client with application type **Desktop app**. Name it JobNavigator local.
5. Download the client JSON and save it locally as `gmail-credentials.json` in the project folder. This filename and Google's usual `client_secret*.json` filenames are ignored by Git.

Google's [Gmail Python quickstart](https://developers.google.com/workspace/gmail/api/quickstart/python) documents project/API setup and Desktop app credentials. Console labels can change.

## Connect this installation

The downloaded JSON contains an `installed` object with `client_id` and `client_secret`. Put these values in the local `.env` as `GMAIL_CLIENT_ID` and `GMAIL_CLIENT_SECRET`. Do not post the file, secret or token in chat or GitHub.

Run `python backend/gmail_oauth_setup.py` from the project folder on Windows, using Python with python-dotenv installed. It opens the system browser and listens on localhost port 8090. Sign in to the intended account and approve the read-only Gmail scope. A Desktop client supports this local loopback flow.

The existing helper displays a refresh token in its terminal. Save it in `.env` as `GMAIL_REFRESH_TOKEN`; avoid sharing terminal output or recording that token in task logs. When an assistant operates the helper, keep token handling in local files rather than returning it through tool output.

After all three values are saved, run `docker compose up -d backend` to recreate the backend with the new environment. A plain restart does not reload Compose's `.env` values. Do this when running jobs have finished. Confirm a manual email check passes before relying on the 30-minute email schedule.

## Unattended operation

Google documents that External apps in **Testing** receive refresh tokens that expire after seven days for scopes such as Gmail read-only. Before relying on ongoing tracking, review the app's Audience/publishing status and Google's personal-use verification exception. Publishing status and verification are different; follow the requirements shown for your project. Tokens can also be revoked for other reasons.

Sources: [OAuth token expiration](https://developers.google.com/identity/protocols/oauth2/), [personal-use exceptions](https://developers.google.com/identity/protocols/oauth2/production-readiness/restricted-scope-verification).

The app reads mail to classify application replies. It does not need permission to send mail. Use the smallest required scope: `https://www.googleapis.com/auth/gmail.readonly`.
