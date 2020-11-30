import base64
import json
from requests.auth import AuthBase
import os
import requests
from urllib.parse import urlparse


class Gen3AuthError(Exception):
    pass


def decode_token(token_str):
    """
    jq -r '.api_key' < ~/.gen3/qa-covid19.planx-pla.net.json | awk -F . '{ print $2 }' | base64 --decode | jq -r .
    """
    tokenParts = token_str.split('.')
    if len(tokenParts) < 3:
        raise Exception('invalid jwt token')
    padding = "===="
    infoStr = tokenParts[1] + padding[0:len(tokenParts[1])%4]
    jsonStr = base64.urlsafe_b64decode(infoStr)
    return json.loads(jsonStr)

def endpoint_from_token(token_str):
    """
    Extract the endpoint from a JWT issuer - ex:
    """
    info = decode_token(token_str)
    urlparts = urlparse(info["iss"])
    endpoint = urlparts.scheme + "://" + urlparts.hostname
    if urlparts.port:
        endpoint += str(urlparts.port)
    return endpoint

def _handle_access_token_response(resp, token_key):
    """
    Shared helper for both get_access_token_with_key and get_access_token_from_wts
    """
    err_msg = "Failed to get an access token from {}:\n{}"
    if resp.status_code != 200:
        raise Gen3AuthError(err_msg.format(resp.url, resp.text))
    try:
        json_resp = resp.json()
        return json_resp[token_key]
    except ValueError:  # cannot parse JSON
        raise Gen3AuthError(err_msg.format(resp.url, resp.text))
    except KeyError:  # no access_token in JSON response
        raise Gen3AuthError(err_msg.format(resp.url, json_resp))

def get_access_token_with_key(api_key):
    """
    Try to fetch an access token given the api key
    """
    endpoint = endpoint_from_token(api_key["api_key"])
    # attempt to get a token from Fence
    auth_url = "{}/user/credentials/cdis/access_token".format(endpoint)
    resp = requests.post(auth_url, json=api_key)
    token_key = "access_token"
    return _handle_access_token_response(resp, token_key)

def get_wts_endpoint(namespace=os.getenv("NAMESPACE", "default")):
    return "http://workspace-token-service.{}.svc.cluster.local".format(namespace)

def get_wts_idps(namespace=os.getenv("NAMESPACE", "default")):
    resp = requests.get(get_wts_endpoint(namespace) + "/external_oidc")
    if resp.status_code != 200:
        raise Exception("non-200 status {} - {}".format(resp.status_code, resp.text))
    return resp.json()

def get_access_token_from_wts(namespace=os.getenv("NAMESPACE", "default"), idp=None):
    """
    Try to fetch an access token for the given idp from the wts
    in the given namespace
    """
    # attempt to get a token from the workspace-token-service
    auth_url = get_wts_endpoint(namespace) + "/token/"
    if idp:
        auth_url += "?idp={}".format(idp)
    resp = requests.get(auth_url)
    return _handle_access_token_response(resp, "token")


class Gen3Auth(AuthBase):
    """Gen3 auth helper class for use with requests auth.

    Implements requests.auth.AuthBase in order to support JWT authentication.
    Generates access tokens from the provided refresh token file or string.
    Automatically refreshes access tokens when they expire.

    Args:
        refresh_file (str, opt): The file containing the downloaded JSON web token. Optional if working in a Gen3 Workspace.
                Defaults to env["GEN3_API_KEY"] if refresh_token and idp not set.
                Includes ~/.gen3/ in search path if value does not include /.
                Interprets "idp://wts/idp" as an idp
        refresh_token (str, opt): The JSON web token. Optional if working in a Gen3 Workspace.
        idp (str, opt): If working in a Gen3 Workspace, the IDP to use can be specified.

    Examples:
        This generates the Gen3Auth class pointed at the sandbox commons while
        using the credentials.json downloaded from the commons profile page.

        >>> auth = Gen3Auth(refresh_file="credentials.json")

        If working in a Gen3 Workspace, initialize as follows:

        >>> auth = Gen3Auth()
    """

    def __init__(self, endpoint=None, refresh_file=None, refresh_token=None, idp=None):
        # note - this is not actually a JWT refresh token - it's a 
        #  gen3 api key with a token as the "api_key" property
        self._refresh_token = refresh_token
        self._access_token = None
        self._wts_idp = idp
        self._wts_namespace = os.environ.get("NAMESPACE", "default")    
        self._use_wts = False

        if refresh_file and refresh_token:
            raise ValueError(
                "Only one of 'refresh_file' and 'refresh_token' can be specified."
            )

        if not refresh_file and not refresh_token and not idp:
            refresh_file = os.getenv("GEN3_API_KEY", None)

        if refresh_file and not idp:
            idp_prefix = "idp://wts/"
            if refresh_file[0:len(idp_prefix) - 1] == idp_prefix:
                idp = refresh_file[len(idp_prefix):]
                refresh_file = None
            elif not os.path.isfile(refresh_file) and "/" not in refresh_file and "\\" not in refresh_file:
                refresh_file = "{}/.gen3/{}".format(os.path.expanduser("~"), refresh_file)
                if not os.path.isfile(refresh_file) and refresh_file[-5:] != ".json":
                    refresh_file += ".json"

        if not refresh_file and not refresh_token:
            # check if this is a Gen3 workspace environment
            # most production environments are in the "default" namespace
            # attempt to get a token from the workspace-token-service
            self._access_token = get_access_token_from_wts(self._wts_namespace, self._wts_idp)
            self._use_wts = True
        elif refresh_file:
            try:
                with open(refresh_file) as f:
                    file_data = f.read()
                self._refresh_token = json.loads(file_data)
            except Exception as e:
                raise ValueError(
                    "Couldn't load your refresh token file: {}\n{}".format(
                        refresh_file, str(e)
                    )
                )
        if self._use_wts:
            self.endpoint = endpoint_from_token(self._access_token)
        else:
            self.endpoint = endpoint_from_token(self._refresh_token["api_key"])

    def __call__(self, request):
        """Adds authorization header to the request

        This gets called by the python.requests package on outbound requests
        so that authentication can be added.

        Args:
            request (object): The incoming request object

        """
        request.headers["Authorization"] = self._get_auth_value()
        request.register_hook("response", self._handle_401)
        return request

    def _handle_401(self, response, **kwargs):
        """Handles failed requests when authorization failed.

        This gets called after a failed request when an HTTP 401 error
        occurs. This then tries to refresh the access token in the event
        that it expired.

        Args:
            request (object): The failed request object

        """
        if not response.status_code == 401 and not response.status_code == 403:
            return response

        # Free the original connection
        response.content
        response.close()

        # copy the request to resend
        newreq = response.request.copy()

        self._access_token = None
        newreq.headers["Authorization"] = self._get_auth_value()

        _response = response.connection.send(newreq, **kwargs)
        _response.history.append(response)
        _response.request = newreq

        return _response

    def get_access_token(self):
        # TODO - add cache and expiration check
        if not self._access_token:
            if self._use_wts:
                self._access_token = get_access_token_from_wts(self._wts_namespace, self._wts_idp)
            else:
                self._access_token = get_access_token_with_key(self._refresh_token)
        return self._access_token
        
    def _get_auth_value(self):
        """Returns the Authorization header value for the request

        This gets called when added the Authorization header to the request.
        This fetches the access token from the refresh token if the access token is missing.

        """
        return "bearer " + self.get_access_token()
    
    