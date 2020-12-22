import backoff
import requests
import urllib.parse
import logging
import sys
from urllib.parse import urlparse

from gen3.utils import append_query_params, DEFAULT_BACKOFF_SETTINGS
from gen3.auth import Gen3CurlError, check_curl_status


def wsurl_to_tokens(ws_urlstr):
    """
    Tokenize ws:/// paths - so ws:///@user/bla/foo returns ("@user", "bla/foo")
    """
    urlparts = urlparse(ws_urlstr)
    if urlparts.scheme != "ws":
        raise Exception("invalid path {}".format(ws_urlstr))
    pathparts = [ part for part in urlparts.path.split("/") if part ]
    if len(pathparts) < 1:
        raise Exception("invalid path {}".format(ws_urlstr))
    return (pathparts[0], "/".join(pathparts[1:]))

@backoff.on_exception(backoff.expo, Gen3CurlError, **DEFAULT_BACKOFF_SETTINGS)
def get_url(urlstr, dest_path):
    res = requests.get(urlstr)
    check_curl_status(res)
    if dest_path == "-":
        sys.stdout.write(res.text)
    else:
        with open(dest_path, 'wb') as f:
            f.write(res.content)

@backoff.on_exception(backoff.expo, Gen3CurlError, **DEFAULT_BACKOFF_SETTINGS)
def put_url(urlstr, src_path):
    with open(src_path, 'rb') as f:
        res = requests.put(urlstr, data=f)
    check_curl_status(res)

def trim_leading_slash(str):
    while str and str[0] == "/":
        str = str[1:]
    return str
        

class Gen3WsStorage:
    """
    A class for interacting with the Gen3 workspace storage service.

    Examples:
        This generates the Gen3WsStorage class pointed at the sandbox commons while
        using the credentials.json downloaded from the commons profile page.

        >>> auth = Gen3Auth(endpoint, refresh_file="credentials.json")
        ... sub = Gen3Metadata(auth.endpoint, auth)

    """

    def __init__(
        self,
        auth_provider=None
    ):
        """
        Initialization for instance of the class to setup basic endpoint info.

        Args:
            auth_provider (Gen3Auth, optional): Gen3Auth class to handle passing your
                token, required for admin endpoints
        """
        self._auth_provider = auth_provider

    @backoff.on_exception(backoff.expo, Gen3CurlError, **DEFAULT_BACKOFF_SETTINGS)
    def upload_url(self, ws, wskey):
        """
        Get a upload url for the given workspace key
        """
        wskey = trim_leading_slash(wskey)
        res = self._auth_provider.curl("/ws-storage/upload/{}/{}".format(ws, wskey))
        check_curl_status(res)
        return res.json()


    @backoff.on_exception(backoff.expo, Gen3CurlError, **DEFAULT_BACKOFF_SETTINGS)
    def upload(self, src_path, dest_ws, dest_wskey):
        """
        Upload a local file to the specified workspace path
        """
        url = self.upload_url(dest_ws, dest_wskey)["Data"]
        put_url(url, src_path)

    @backoff.on_exception(backoff.expo, Gen3CurlError, **DEFAULT_BACKOFF_SETTINGS)
    def download_url(self, ws, wskey):
        """
        Get a download url for the given workspace key
        """
        wskey = trim_leading_slash(wskey)
        res = self._auth_provider.curl("/ws-storage/download/{}/{}".format(ws, wskey))
        check_curl_status(res)
        return res.json()


    def download(self, src_ws, src_wskey, dest_path):
        """
        Download a file from the workspace to local disk
        """
        durl = self.download_url(src_ws, src_wskey)["Data"]
        get_url(durl, dest_path)

    def copy(self, src_urlstr, dest_urlstr):
        """
        Parse src_urlstr and dest_urlstr, and call upload or download
        as appropriate
        """
        if src_urlstr[0:3] == "ws:":
            if dest_urlstr[0:3] == "ws:":
                raise Exception("source and destination may not both reference a workspace")
            pathparts = wsurl_to_tokens(src_urlstr)
            return self.download(pathparts[0], pathparts[1], dest_urlstr)
        if dest_urlstr[0:3] == "ws:":
            pathparts = wsurl_to_tokens(dest_urlstr)
            return self.upload(src_urlstr, pathparts[0], pathparts[1])
        raise Exception("source and destination may not both be local")

    @backoff.on_exception(backoff.expo, Gen3CurlError, **DEFAULT_BACKOFF_SETTINGS)
    def ls(self, ws, wskey):
        """
        List the contents under the given workspace path
        """
        wskey = trim_leading_slash(wskey)
        res = self._auth_provider.curl("/ws-storage/list/{}/{}".format(ws, wskey))
        check_curl_status(res)
        return res.json()


    def ls_path(self, ws_urlstr):
        """
        Same as ls - but parses ws_urlstr argument of form:
          ws:///workspace/key
        """
        pathparts = wsurl_to_tokens(ws_urlstr)
        return self.ls(pathparts[0], pathparts[1])

    @backoff.on_exception(backoff.expo, Gen3CurlError, **DEFAULT_BACKOFF_SETTINGS)
    def rm(self, ws, wskey):
        """
        Remove the given workspace key
        """
        wskey = trim_leading_slash(wskey)
        res = self._auth_provider.curl("/ws-storage/list/{}/{}".format(ws, wskey), request="DELETE")
        check_curl_status(res)
        return res.json()

    def rm_path(self, ws_urlstr):
        """
        Same as rm - but parses the ws_urlstr argument
        """
        pathparts = wsurl_to_tokens(ws_urlstr)
        return self.rm(pathparts[0], pathparts[1])
