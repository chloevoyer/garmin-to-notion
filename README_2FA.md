# Garmin to Notion with Garmin 2FA

If your garmin account has 2FA enabled, you will need to generate an authentication token manually.

## Generating the connection token

The login utility `garth` can be used to generate an authentication token that can be used to connect to your Garmin account without needing to go through the 2FA process each time.

The following instructions should be run in a terminal on your machine.

### 1. Installing `uvx`

`uvx` is required to run the `garth` login utility, which will allow us to generate an authentication token to skip the 2FA verification.

Follow the [official `uvx` documentation](https://docs.astral.sh/uv/getting-started/installation/) to install `uvx` on your specific system.

### 2. Installing `garth`

Once `uvx` is properly installed, you can install `garth` using the following command:

```shell
uvx garth
```

On the first invocation, this will install the `garth` utility.

### 3. Generating the token

You can now run the `garth` login utility to generate an authentication token:

```shell
garth login
```

This will prompt you for your Garmin credentials and handle the 2FA process. Follow the on-screen instructions to complete the login.
Once the login is successful, `garth` will output an authentication token. The token should be a long, single line of random characters.

Make sure to copy the entire line, without any leading or trailing whitespace.

## Using the token

Once you have the authentication token, you need to configure it in your project's environment variables so that it can be used to authenticate with Garmin.

To do this,
1. Go to the page of your GitHub fork of this repository
2. Navigate to the "Settings" tab.
3. Using the left sidebar, navigate to the "Secrets and variables > Actions" page.
4. Click on the "New repository secret" button.
    - For the "Name" field, enter `GARMIN_AUTH_TOKEN`.
    - For the "Value" field, paste the authentication token you generated earlier.
5. Click the "Add secret" button to save the new secret.

Once the secret is added, the GitHub Actions workflow will use this token to authenticate with Garmin, bypassing the need for 2FA during each sync operation.
