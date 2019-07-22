#!/usr/bin/env python3
from __future__ import print_function
import sys
import yaml
import json
import requests
from requests.auth import HTTPBasicAuth
import logging
import argparse


log = logging.getLogger('tagtool')


def pretty_json(obj):
    return json.dumps(obj, indent=4)


class DockerRegistry:

    def __init__(self, url, username=None, password=None):
        self.session = None
        self.token = None
        self.endpoint = "http://" + url + "/v2"
        self.web_endpoint = "https://hub.docker.com/v2"
        self.credentials = None
        if username and password:
            self.username = username
            self.password = password
            self.credentials = HTTPBasicAuth(self.username, self.password)

    def auth(self, repo, actions=["pull"], anonymous=False):
        url = 'https://auth.docker.io/token?service=registry.docker.io&scope=repository:{}:{}'.format(repo, ','.join(actions))
        log.debug('Requesting %s', url)
        if not self.credentials or anonymous:
            req = requests.get(url)
        else:
            req = requests.get(url, auth=self.credentials)
        log.debug(req.text)
        token = req.json()['token']
        log.debug("Token %s", token)
        return token

    def auth_web(self):
        auth_data = {"username": self.username, "password": self.password}
        resp = requests.post("https://hub.docker.com/v2/users/login/", data=auth_data)
        web_token = resp.json()["token"]
        return web_token

    def request(self, path, token=None, method='GET'):
        hdr = {'Accept': 'application/vnd.docker.distribution.manifest.v2+json'}
        if token is not None:
            hdr["Authorization"] = "Bearer " + token
        url = self.endpoint + '/' + path
        log.debug('Requesting %s', url)
        req = requests.request(method, url, headers=hdr)
        return req

    def request_web(self, path, method='GET'):
        if method == "DELETE":
            token = self.auth_web()
        hdr = {"Authorization": "JWT " + token}
        url = self.web_endpoint + '/' + path
        log.debug('Requesting %s', url)
        req = requests.request(method, url, headers=hdr)
        return req

    def manifest_request(self, image, tag, token=None, method='GET'):
        path = '{}/manifests/{}'.format(image, tag)
        if token is None:
            token = self.auth(image, anonymous=True)
        return self.request(path, token, method=method)

    def get_image_manifest(self, image, tag, token=None):
        manifest = self.manifest_request(image, tag, token).json()
        log.debug(pretty_json(manifest))
        return manifest

    def get_image_manifest_digest(self, image, tag="latest", token=None):
        manifest_req = self.manifest_request(image, tag, token)
        return manifest_req.headers['Docker-Content-Digest']

    def get_image_id_from_registry(self, image, tag="latest", token=None):
        return self.get_image_manifest(image, tag, token).get('config', {}).get('digest', None)

    def delete_manifest(self, repository, digest, token=None, dry_run=True):
        if dry_run:
            log.info('DRY RUN: delete_manifest %s %s %s', repository, digest)
            return
        else:
            log.info('delete_manifest %s %s %s', repository, digest)
        req = self.manifest_request(repository, digest, token, method='DELETE')
        log.debug("Headers: %s", req.headers)
        log.debug("Status code: %s", req.status_code)
        log.debug("Content: %s", req.content)

    # most useful, "public interface" methods

    def list_tags(self, image, token=None):
        resp = self.request(image + "/tags/list", token)
        resp = resp.json()
        if resp.get("errors", []):
            log.error("Error occured during listing tags for %s: %s", image, resp)
            return []
        return resp["tags"]

    def is_tag_present(self, repo, tag="latest"):
        log.debug("Checking whether {} contains {} tag".format(repo, tag))
        return tag in self.list_tags(repo)

    def delete_image(self, repo, tag="latest", token=None, dry_run=True):
        if dry_run:
            log.info('DRY RUN: delete_image %s %s', repo, tag)
            return
        else:
            log.info('delete_image %s %s', repo, tag)
        digest = self.get_image_manifest_digest(repo, tag, token)
        self.delete_manifest(repo, digest, token, dry_run)

    def delete_image_web(self, repo, tag="latest"):
        """Dockerhub doesn't allow deleting tags via the registry API.
        We need to use the API used by web browser when clicking on
        the delete "trash" icon."""
        path = "repositories/{}/tags/{}/".format(repo, tag)
        resp = self.request_web(path, method="DELETE")
        return resp

    def delete_repo_web(self, repo):
        """Dockerhub doesn't allow deleting tags via the registry API.
        We need to use the API used by web browser when clicking on
        the delete "trash" icon."""
        path = "repositories/{}".format(repo)
        resp = self.request_web(path, method="DELETE")
        return resp


def setup_logging(log_level):
    log.setLevel(log_level)
    console = logging.StreamHandler()
    console.setLevel(log_level)
    log.addHandler(console)

    logFormatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
    fileHandler = logging.FileHandler("/tmp/check_network/check.log")
    fileHandler.setFormatter(logFormatter)
    log.addHandler(fileHandler)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action")
    parser.add_argument("--registry")
    parser.add_argument("--repository")
    parser.add_argument("--tag")
    args = parser.parse_args()
    setup_logging("DEBUG")
    #with open("config.yaml", "r") as config_file:
    #    config = yaml.load(config_file)
    client = DockerRegistry(args.registry)
    if args.action == "is_tag_present":
        result = client.is_tag_present(args.repository, args.tag)
        print(result)
        sys.exit(int(not result))
    elif args.action == "list_tags":
        tags = client.list_tags(args.repository)
        [print(tag) for tag in tags]
    else:
        log.error("Unknown action: %s", args.action)
        sys.exit(1)
