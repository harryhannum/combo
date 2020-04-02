from __future__ import print_function
from combo_core.source_maintainer import *
from combo_core.importer import *
from combo_core.compat import connection_error
import requests
import json

MAX_RESPONSE_LENGTH = 4096


class ServerError(ComboException):
    pass


class ServerConnectionError(ServerError, connection_error):
    pass


class ServerInvalidRequest(ServerError):
    pass


class RemoteSourceLocator(SourceLocator):
    def __init__(self, address):
        self._addr = address
        self._url = 'http://' + ':'.join(str(x) for x in address)

    def _extended_url(self, *args):
        return '/'.join((self._url, ) + args)

    def _send_get_request(self, url_extension, **params):
        req_url = self._extended_url(url_extension)

        try:
            response = requests.get(req_url, params=params)
            decoded_respone = response.content.decode()
        except BaseException as e:
            raise ServerConnectionError(
                'Could not get response for request to "{}" with params "{}"'.format(req_url, params), e)

        if decoded_respone.startswith('Error'):
            raise ServerInvalidRequest(decoded_respone)

        return decoded_respone

    def get_source(self, project_name, version):
        response = self._send_get_request('project/' + str(project_name) + "/" + str(version))

        try:
            source = json.loads(response)
        except BaseException as e:
            raise ServerError('Requested source from server, could not parse response "{}"'.format(response), e)

        return source

    def all_sources(self):
        response = self._send_get_request('get_available_versions')

        try:
            sources_dict = json.loads(response)
        except BaseException as e:
            raise ServerError('Requested all sources from server, could not parse response "{}"'.format(response), e)

        return sources_dict


class RemoteSourceMaintainer(RemoteSourceLocator, SourceMaintainer):
    def __init__(self, address):
        super(RemoteSourceMaintainer, self).__init__(address)

    def _send_post_request(self, url_extension, **data):
        headers = {
          'Content-Type': 'application/json'
        }

        req_url = self._extended_url(url_extension)

        try:
            response = requests.post(req_url, data=json.dumps(data), headers=headers)
            decoded_respone = response.content.decode()
        except BaseException as e:
            raise ServerConnectionError(
                'Could not post the request "{}" with data "{}"'.format(req_url, data), e)

        if decoded_respone.startswith('Error'):
            raise ServerInvalidRequest(decoded_respone)

        return decoded_respone

    def add_project(self, project_name, source_type=None):
        if source_type:
            data['source_type'] = source_type

        response = self._send_post_request('project/' + project_name + "/", None)
        print('Server response: {}'.format(response))

    def add_version(self, version_details, **kwargs):
        # kwargs is not relevant here, because it is not sent to the server anyway

        version_details_dump = json.dumps(version_details)
        response = self._send_post_request('project/', **version_details)
        print('Server response: {}'.format(response))


class RemoteImporter(Importer):
    def __init__(self, sources_locator):
        """
        Construct a dependencies importer which uses the combo server
        :param sources_locator: A RemoteSourceLocator object
        """
        if not isinstance(sources_locator, RemoteSourceLocator):
            raise UnhandledComboException(
                'Invalid sources locator for type for server importer: {}'.format(type(sources_locator)))
        super(RemoteImporter, self).__init__(sources_locator)

    def get_all_sources_map(self):
        return self._source_locator.all_sources()

    # TODO: Return this optimized implementation once the server has a real implementation of the all sources map
    # def get_dep_hash(self, dep):
    #     """
    #     :param dep: A combo dependency
    #     :return: The hash of the given dependency
    #     """
    #     # If already cached, return the cached hash
    #     if self._cached_data.has_dep(dep):
    #         return self._cached_data.get_hash(dep)
    #
    #     # Dependency is not cached, use the all sources json instead
    #     sources_map = self.get_all_sources_map()
    #     assert str(dep) in sources_map, 'Dependency "{}" not found on the remote sources map'.format(dep)
    #
    #     return sources_map[str(dep)]['hash']
