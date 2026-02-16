import http.server
import os
import json
import linkedin.commands.command as command
import linkedin.utils.config as config
import logging
import webbrowser
from urllib import request, parse


logger = logging.getLogger(__name__)


class LoginRequestHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = parse.urlparse(self.path)
        parsed_query = parse.parse_qsl(parsed_path.query)
        query_key = parsed_query[0][0]
        query_value = parsed_query[0][1]
        if query_key == "error":
            description = parsed_query[1][1]
            logger.error(description)
            self.send_response(307)
            self.send_header('Location','https://linkedin-cli.tigillo.com/error?error=' + query_value + '&description='+description)
        elif query_key == "code":
            logger.debug("Authorization code received: %s", query_value)
            # Exchange the code for an Access Token
            token_url = "https://www.linkedin.com/oauth/v2/accessToken"
            token_data = {
                'grant_type': 'authorization_code',
                'code': query_value,
                'redirect_uri': config.getConfig().REDIRECT_URL,
                'client_id': config.getConfig().CONFIG['application']['client_id'],
                'client_secret': config.getConfig().CONFIG['application']['client_secret']
            }
            token_data = parse.urlencode(token_data).encode()
            token_req = request.Request(token_url, data=token_data)
            # LinkedIn requires x-www-form-urlencoded
            token_req.add_header('Content-Type', 'application/x-www-form-urlencoded')
            token_response = request.urlopen(token_req)
            access_token = json.loads(token_response.read())['access_token']
            config.getConfig().setAccessToken(access_token)

            # Retrieve the user details
            userinfo_url = "https://api.linkedin.com/v2/userinfo"
            userinfo_req = request.Request(userinfo_url, headers={
                'Authorization': 'Bearer ' + access_token
            })

            userinfo_response = request.urlopen(userinfo_req)
            user = json.loads(userinfo_response.read())

            config.getConfig().setUrn(user["sub"])

            self.send_response(307)
            self.send_header('Location','https://linkedin-cli.tigillo.com/success')

        else:
            description = "Unsupported response from linkedin"
            logger.error(description)
            self.send_response(307)
            self.send_header('Location','https://linkedin-cli.tigillo.com/error?error=' + query_value + '&description='+description)   
        self.end_headers()
        self.connection.close()

    def log_message(self, format, *args):
        return


class HelpCommand(command.BaseCommand):
    def execute(self, args):
        print("usage: linkedin login")


class LoginCommand(command.BaseCommand):
    def execute(self, args):
        webbrowser.open(config.getConfig().AUTH_URL)
        httpd = http.server.HTTPServer(('', 4625), LoginRequestHandler)
        httpd.socket.settimeout(120)
        httpd.handle_request()

