from __future__ import print_function
import argparse
import requests
from requests.auth import HTTPBasicAuth
import docker
import sys
import os
import re
import itertools
import logging

log = logging.getLogger('tagtool')


def get_container_list(registry, auth=None):
    log.debug("get_container_list: %s", registry)
    url = registry + '/v2/_catalog'
    if auth:
        auth = HTTPBasicAuth(*auth)
        catalog_req = requests.get('https://' + url, auth=auth)
    else:
        catalog_req = requests.get('http://' + url)
    catalog = catalog_req.json()
    return catalog["repositories"]


def get_images_and_tags(registry, auth=None):
    images = get_container_list(registry, auth=auth)
    result = {}
    for image in images:
        tags = get_tag_list(registry, image, auth=auth)
        result[image] = tags
    return result


def get_tag_list(registry, repository, auth=None):
    url = registry + '/v2/' + repository + '/tags/list'
    if auth:
        auth = HTTPBasicAuth(*auth)
        catalog_req = requests.get('https://' + url, auth=auth)
    else:
        catalog_req = requests.get('http://' + url)
    catalog = catalog_req.json()
    return catalog["tags"] if catalog["tags"] is not None else []


def get_all_images_with_tag(registry, tag, auth=None):
    images = get_container_list(registry, auth=auth)
    matching_images = []
    for image in images:
        tags = get_tag_list(registry, image, auth=auth)
        if tag in tags:
            matching_images.append(image)
    return matching_images


def get_all_tags(registry, auth=None):
    images = get_container_list(registry, auth=auth)
    all_tags = set()
    for image in images:
        tags = set(get_tag_list(registry, image, auth=auth))
        all_tags.update(tags)
    return all_tags


def manifest_request(registry, image, tag, auth=None, method='GET'):
    headers = {'Accept': 'application/vnd.docker.distribution.manifest.v2+json'}
    url = '{}/v2/{}/manifests/{}'.format(registry, image, tag)
    if auth:
        auth = HTTPBasicAuth(*auth)
        manifest_req = requests.request(method, 'https://' + url, auth=auth, headers=headers)
    else:
        manifest_req = requests.request(method, 'http://' + url, headers=headers)
    return manifest_req


def get_image_manifest(registry, image, tag, auth=None):
    manifest = manifest_request(registry, image, tag, auth).json()
    return manifest


def get_image_id_from_registry(registry, image, tag, auth=None):
    return get_image_manifest(registry, image, tag, auth).get('config', {}).get('digest', None)


def get_image_manifest_digest(registry, image, tag, auth=None):
    manifest_req = manifest_request(registry, image, tag, auth)
    return manifest_req.headers['Docker-Content-Digest']


def delete_manifest(registry, repository, digest, dry_run=True):
    if dry_run:
        log.info('DRY RUN: delete_manifest %s %s %s', registry, repository, digest)
        return
    req = manifest_request(registry, repository, digest, method='DELETE')
    log.debug("Headers: %s", req.headers)
    log.debug("Status code: %s", req.status_code)
    log.debug("Content: %s", req.content)


client = docker.from_env()

build_number = os.environ.get('BUILD_NUMBER', None) or '30'
nightly_registry = os.environ.get('DOCKER_REGISTRY', None) or '10.84.5.81:35598'
sandbox_registry = "ccregdev.sndbx.junipercloud.net"
private_registry = "10.84.5.81:5010"
public_registry = "10.84.5.81:5000"
dockerhub = 'opencontrailnightly'
openstack_versions = ['ocata', 'newton']
contrail_versions = ['master', '5.0']

s_user = 'cntrlcld@juniper.net'
s_pass = 'kEYwAntANycE'

latest_openstack_version = 'ocata'
latest_contrail_version = 'master'
latest_distro = 'centos'


def list_build(registry = public_registry, tag='5.0-33', **kwargs):
    pass


def list_registry(registry=public_registry, tag='5.0-36', **kwargs):
    imgs = get_all_images_with_tag(registry, tag)
    print(len(imgs), 'images')
    [print(i) for i in imgs]
    imgs = get_container_list(registry)
    all_tags = set()
    for i in imgs:
        all_tags.update(set(get_tag_list(registry, i)))
    #[print(t) for t in sorted(list(all_tags))]


def list_repositories(registry=public_registry, auth=None, **kwargs):
    repositories = get_container_list(registry, auth)
    print(len(repositories), 'repositories')
    [print(i) for i in sorted(repositories)]


def list_tags(registry=None, **kwargs):
    tags = get_all_tags(registry)
    [print(t) for t in sorted(tags)]


def list_repository_tags(registry=public_registry, repository=None, auth=None, **kwargs):
    tags = get_tag_list(registry, repository, auth)
    print(len(tags), 'tags')
    [print(t) for t in sorted(tags)]


def list_repositories_with_tag(registry, tag, auth=None, **kwargs):
    repositories = get_all_images_with_tag(registry, tag, auth=None)
    print(len(repositories), 'repositories')
    [print(i) for i in sorted(repositories)]


def list_all_images_matching_tag(registry, tag, auth=None, **kwargs):
    # tag is regexp pattern this time
    regex = re.compile(tag)
    tags = get_all_tags(registry)
    for tag in tags:
        if regex.match(tag):
            repositories = get_all_images_with_tag(registry, tag, auth=None)
            for repo in repositories:
                print(registry + '/' + repo + ':' + tag)


def remove_image_from_registry(registry, repository, tag, auth=None, dry_run=True, **kwargs):
    """Remove single tag from single repository"""
    log.debug("remove_image_from_registry: Removing %s %s %s", registry, repository, tag)
    digest = get_image_manifest_digest(registry, repository, tag)
    log.debug("Digest to delete: %s", digest)
    delete_manifest(registry, repository, digest, dry_run)


def remove_tag_from_registry(registry, tag, auth=None, dry_run=True, **kwargs):
    """Remove all images tagged as `tag` from all repositories in this registry"""
    log.debug("remove_tag_from_registry %s %s %s", registry, tag, dry_run)
    repositories = get_all_images_with_tag(registry, tag, auth)
    log.info('Removing all images tagged as %s: %s', tag, repositories)
    for repository in repositories:
        remove_image_from_registry(registry, repository, tag, auth, dry_run)


def remove_repository_from_registry(registry=public_registry, repository=None, auth=None, dry_run=True, **kwargs):
    """Remove all tags from this repository"""
    dry_run = False
    log.debug("remove_repository_from_registry: Removing %s %s %s", registry, repository, 'DRY RUN' if dry_run else '')
    tags = get_tag_list(registry, repository, auth)
    for tag in tags:
        remove_image_from_registry(registry, repository, tag, auth, dry_run)


def clean_tag(registry=None, tag=None, auth=None, dry_run=True):
    log.debug("clean_tag %s %s %s", registry, tag, dry_run)
    tags = get_all_tags(public_registry)
    if registry is None:
        registry = public_registry
    [print(t) for t in sorted(tags)]
    image_count = 0
    images_and_tags = get_images_and_tags(registry)
    for image, tags in images_and_tags.items():
        image_count += len(tags)
    print(image_count, "images in total")
    if tag:
        remove_tag_from_registry(registry, tag, dry_run)
        return
    answer = sys.stdin.readline()
    for tag in tags:
        images = get_all_images_with_tag(registry, tag, auth=None)
        print('Do you want to delete tag?:')
        print(tag)
        [print(t) for t in sorted(images)]
        print()
        print()
        answer = sys.stdin.readline()
        print(answer + '|||')
        if answer.strip() != 'Y':
            print('Skipping...')
            continue
        else:
            remove_tag_from_registry(registry, tag, dry_run)
    return


def compare_registries():
    openstack_version = 'ocata'
    contrail_version = '5.0'
    build_number = '40'
    nightly_nostack = '{}-{}'.format(contrail_version, build_number)
    nightly_nostack_upload = nightly_nostack + '_upload'
    nightly_with_openstack = openstack_version + '-' + nightly_nostack
    nightly_with_openstack_upload = nightly_with_openstack + '_upload'
    nightly_with_openstack_rhel = 'rhel-' + nightly_with_openstack
    nightly_with_openstack_rhel_upload = nightly_with_openstack_rhel + '_upload'
    nightly_nostack_rhel = 'rhel-' + nightly_nostack
    r1_tag = 'ocata-5.0-35'
    r2_tag = '5.0-35'
    r2_tag = r1_tag
    auth=(s_user, s_pass)
    #compare_registries2(public_registry, None, r1_tag, sandbox_registry, auth, r2_tag, True)
    #compare_registries2(nightly_registry, None, r1_tag, public_registry, None, r2_tag, True)
    compare_registries2(nightly_registry, None, nightly_with_openstack, public_registry, None, nightly_with_openstack, True)
    compare_registries2(nightly_registry, None, nightly_with_openstack, public_registry, None, nightly_nostack, True)
    compare_registries2(nightly_registry, None, nightly_nostack, public_registry, None, nightly_nostack, True)
    compare_registries2(nightly_registry, None, nightly_with_openstack_rhel, public_registry, None, nightly_with_openstack_rhel, True)
    compare_registries2(nightly_registry, None, nightly_with_openstack_rhel, public_registry, None, nightly_nostack_rhel, True)
    compare_registries2(nightly_registry, None, nightly_nostack, public_registry, None, 'latest', True)
    #compare_registries2(public_registry, None, '5.0-35', public_registry, None, 'master-75', True)
    openstack_version = 'newton'
    contrail_version = '5.0'
    build_number = '40'
    nightly_nostack = '{}-{}'.format(contrail_version, build_number)
    nightly_nostack_upload = nightly_nostack + '_upload'
    nightly_with_openstack = openstack_version + '-' + nightly_nostack
    nightly_with_openstack_upload = nightly_with_openstack + '_upload'
    nightly_with_openstack_rhel = 'rhel-' + nightly_with_openstack
    nightly_with_openstack_rhel_upload = nightly_with_openstack_rhel + '_upload'
    nightly_nostack_rhel = 'rhel-' + nightly_nostack
    r1_tag = 'ocata-5.0-35'
    r2_tag = '5.0-35'
    r2_tag = r1_tag
    auth=(s_user, s_pass)
    #compare_registries2(public_registry, None, r1_tag, sandbox_registry, auth, r2_tag, True)
    #compare_registries2(nightly_registry, None, r1_tag, public_registry, None, r2_tag, True)
    compare_registries2(nightly_registry, None, nightly_with_openstack, public_registry, None, nightly_with_openstack, True)

    openstack_version = 'ocata'
    contrail_version = '5.0'
    build_number = '40'
    nightly_nostack = '{}-{}'.format(contrail_version, build_number)
    nightly_nostack_upload = nightly_nostack + '_upload'
    nightly_with_openstack = openstack_version + '-' + nightly_nostack
    nightly_with_openstack_rhel = 'rhel-' + nightly_with_openstack
    nightly_nostack_rhel = 'rhel-' + nightly_nostack
    release_nostack = '{}.0-0.{}'.format(contrail_version, build_number)
    release_with_openstack = release_nostack + '-' + openstack_version
    release_with_openstack_rhel = 'rhel-' + release_with_openstack
    release_nostack_rhel = 'rhel-' + release_nostack
    r1_tag = 'ocata-5.0-35'
    r2_tag = '5.0-35'
    r2_tag = r1_tag
    auth=(s_user, s_pass)
    sandbox_registry2 =  sandbox_registry + '/contrail'
    #compare_registries2(public_registry, None, r1_tag, sandbox_registry, auth, r2_tag, True)
    #compare_registries2(nightly_registry, None, r1_tag, public_registry, None, r2_tag, True)
    compare_registries2(public_registry, None, nightly_with_openstack, sandbox_registry2, auth, release_with_openstack, True)
    compare_registries2(public_registry, None, nightly_with_openstack, sandbox_registry2, auth, release_nostack, True)
    compare_registries2(public_registry, None, nightly_nostack, sandbox_registry2, auth, nightly_nostack, True)
    compare_registries2(public_registry, None, nightly_with_openstack_rhel, sandbox_registry2, auth, nightly_with_openstack_rhel, True)
    compare_registries2(public_registry, None, nightly_with_openstack_rhel, sandbox_registry2, auth, nightly_nostack_rhel, True)
    #compare_registries2(public_registry, None, nightly_nostack, sandbox_registry, None, , True)


def compare_registries2(r1, r1_auth, r1_tag, r2, r2_auth, r2_tag, force_id_compare=False):
    print('Comparing', r1, r1_tag, 'with', r2, r2_tag)
    r1_images = set(get_all_images_with_tag(r1, r1_tag, auth=r1_auth))
    r2_images = set(get_all_images_with_tag(r2, r2_tag, auth=r2_auth))
    id_mismatches = 0
    common_images = 0
    all_images = r1_images.union(r2_images)
    all_images_count = len(all_images)
    common_images = r1_images.intersection(r2_images)
    common_images_count = len(common_images)
    print('Common images:', common_images_count, '/', all_images_count)
    if r1_images != r2_images:
        print('Current container list mismatch')
        print('In {} but not in {}:'.format(r1, r2))
        print(set(r1_images).difference(r2_images))
        print('In {} but not in {}:'.format(r2, r1))
        print(set(r2_images).difference(r1_images))
        if not force_id_compare:
            return
        else:
            print('Continuing with comparing common images')
    else:
        print('Images match, starting image ID comparison')
    common_images = set(r1_images).intersection(set(r2_images))
    for r1i in common_images:
        r1_id = get_image_id_from_registry(r1, r1i, r1_tag, r1_auth)
        r2_id = get_image_id_from_registry(r2, r1i, r2_tag, r2_auth)
        if r1_id == r2_id:
            print('Image ids match', r1i)
        else:
            print('ERROR! IDs mismatch', r1i, r1_id, r2_id)
            id_mismatches += 1



def publish_nightly(contrail_version, openstack_version, build_number, distro):
    if distro == 'centos':
        distro_prefix = ''
    elif distro == 'rhel':
        distro_prefix = 'rhel-'

    nightly_nostack = '{}-{}'.format(contrail_version, build_number)
    nightly_nostack_upload = nightly_nostack + '_upload'
    nightly_with_openstack = openstack_version + '-' + nightly_nostack
    nightly_with_openstack_upload = nightly_with_openstack + '_upload'
    nightly_with_openstack_rhel = 'rhel-' + nightly_with_openstack
    nightly_with_openstack_rhel_upload = nightly_with_openstack_rhel + '_upload'
    nightly_nostack_rhel = 'rhel-' + nightly_nostack

    # get images with openstack version (container-builder and test-test)
    nightly_images = get_all_images_with_tag(nightly_registry, nightly_with_openstack)

    print('Found', len(nightly_images), 'nightly images in', nightly_registry)

    print('Upload phase start')
    retag(nightly_images, nightly_registry, nightly_with_openstack, public_registry, [nightly_with_openstack_upload])
    retag(['contrail-go'], nightly_registry, nightly_nostack, public_registry, [nightly_nostack_upload])
    retag(nightly_images, nightly_registry, nightly_with_openstack_rhel, public_registry, [nightly_with_openstack_rhel_upload])

    print('Tag phase start')
    retag(nightly_images, nightly_registry, nightly_with_openstack, public_registry, [nightly_with_openstack, nightly_nostack])
    retag(['contrail-go'], nightly_registry, nightly_nostack, public_registry, [nightly_nostack])
    retag(nightly_images, nightly_registry, nightly_with_openstack_rhel, public_registry, [nightly_with_openstack_rhel, nightly_nostack_rhel])

    if contrail_version == latest_contrail_version and openstack_version == latest_openstack_version:
        print('Latest tag phase start')
        retag(nightly_images, nightly_registry, nightly_with_openstack, public_registry, ['latest'])
        retag(['contrail-go'], nightly_registry, nightly_nostack, public_registry, ['latest'])
    else:
        print(contrail_version, openstack_version, 'not latest, skipping latest tag')


def publish_dockerhub(contrail_version='master', openstack_version='ocata', build_number='73', distro='centos'):
    nightly_nostack = '{}-{}'.format(contrail_version, build_number)
    nightly_nostack_upload = nightly_nostack + '_upload'
    nightly_with_openstack = openstack_version + '-' + nightly_nostack
    nightly_with_openstack_upload = nightly_with_openstack + '_upload'

    # get images with openstack version (container-builder and test-test)
    nightly_images = get_all_images_with_tag(nightly_registry, nightly_with_openstack)

    print('Found', len(nightly_images), 'nightly images in', nightly_registry)

    print('Upload phase start')
    retag(nightly_images, nightly_registry, nightly_with_openstack, public_registry, [nightly_with_openstack_upload])
    retag(['contrail-go'], nightly_registry, nightly_nostack, public_registry, [nightly_nostack_upload])
    retag(nightly_images, nightly_registry, nightly_with_openstack_rhel, public_registry, [nightly_with_openstack_rhel_upload])

    print('Tag phase start')
    retag(nightly_images, nightly_registry, nightly_with_openstack, public_registry, [nightly_with_openstack, nightly_nostack])
    retag(['contrail-go'], nightly_registry, nightly_nostack, public_registry, [nightly_nostack])
    retag(nightly_images, nightly_registry, nightly_with_openstack_rhel, public_registry, [nightly_with_openstack_rhel, nightly_nostack_rhel])

    if contrail_version == latest_contrail_version and openstack_version == latest_openstack_version:
        print('Latest tag phase start')
        retag(nightly_images, nightly_registry, nightly_with_openstack, public_registry, ['latest'])
        retag(['contrail-go'], nightly_registry, nightly_nostack, public_registry, ['latest'])
    else:
        print(contrail_version, openstack_version, 'not latest, skipping latest tag')


def tag():
    nightly_registry = "10.84.5.81:35173"  # 5.0-29

    build_number = '75'
    contrail_version = 'master'
    openstack_version = 'ocata'
    nightly_nostack = '{}-{}'.format(contrail_version, build_number)
    nightly_nostack_upload = nightly_nostack + '_upload'
    nightly_with_openstack = openstack_version + '-' + nightly_nostack
    nightly_with_openstack_upload = nightly_with_openstack + '_upload'
    nightly_with_openstack_rhel = 'rhel-' + nightly_with_openstack
    nightly_with_openstack_rhel_upload = nightly_with_openstack_rhel + '_upload'
    nightly_nostack_rhel = 'rhel-' + nightly_nostack

    with open('current_containers', 'r') as cont_file:
        current_containers = [x[:-1] for x in cont_file.readlines()]
    print(current_containers)
    #current_containers.append('contrail-go')
    #current_containers.append('contrail-test-test')

    retag(["contrail-go"],   public_registry,  nightly_nostack,      dockerhub,  ['latest'], skip_checks=True)
    retag(["contrail-test-test"],   public_registry,  nightly_with_openstack,      dockerhub,  ['latest'], skip_checks=True)
    retag(current_containers,   public_registry,  nightly_with_openstack,      dockerhub,  ['latest'], skip_checks=True)
    sys.exit(0)


    registry = "localhost:5000"
    registry = public_registry
    tag = 'ocata-master-' + build_number
    tag_short = 'master-29'

    # Step 1: tag ocata centos master from int public as latest to internal_public and dockerhub
    # Step 1: tag ocata centos master from int public as non-ocata to internal_public and dockerhub
    # Step 3: tag newton centos master/5.0 from int public to dockerhub

    # Step 2: tag ocata rhel 5.0 from int public as rhel-5.0.0-0.BN-ocata to sandbox
    # Step 2: tag ocata centos 5.0 from int public as 5.0.0-0.BN-ocata to sandbox
    # Step 2: tag command latest from int private as 5.0.0-0.BN-ocata to sandbox
    # Step 2: tag centos to sandbox???
    registry_containers = get_container_list(public_registry)
    print(registry_containers)
    contrail_containers = [ x for x in registry_containers if x.startswith('contrail-')]
    print(contrail_containers)
    #current_containers = []
    build_number = '70'
    nightly_nostack = 'master-{}'.format(build_number)
    nightly_with_openstack = 'ocata-' + nightly_nostack
    nightly_with_openstack_rhel = 'rhel-' + nightly_with_openstack

    # cross check
    #matching_images = get_all_images_with_tag(nightly_registry, nightly_with_openstack)
    #if set(matching_images) != set(current_containers):
    #    print('Current container list mismatch')
    #    print('In registry but not on list:')
    #    print(set(matching_images).difference(current_containers))
    #    print('On list but not in registry:')
    #    print(set(current_containers).difference(matching_images))

    #retag(["contrail-go"],   nightly_registry,  nightly_nostack,      public_registry,  [nightly_nostack, 'latest'])
    #retag(current_containers,   nightly_registry,  nightly_with_openstack,      public_registry,  [nightly_with_openstack])
    #current_containers.append('contrail-test-test')
    #retag(current_containers,   public_registry,  nightly_with_openstack,      public_registry,  [nightly_nostack, 'latest'])
    #retag(["contrail-go"],   public_registry,  nightly_nostack,      dockerhub,  [nightly_nostack, 'latest'])
    #retag(current_containers,   public_registry,  nightly_with_openstack,      dockerhub,        [nightly_with_openstack, nightly_nostack, 'latest'])


    build_number = '29'
    openstack_version = 'newton'
    nightly_nostack = '5.0-{}'.format(build_number)
    nightly_with_openstack = openstack_version + '-' + nightly_nostack
    nightly_with_openstack_rhel = 'rhel-' + nightly_with_openstack
    nightly_nostack_rhel = 'rhel-' + nightly_nostack
    release_nostack = '5.0.0-0.{}'.format(build_number)
    release_nostack_rhel = 'rhel-' + release_nostack
    release_with_openstack = release_nostack + '-' + openstack_version
    release_with_openstack_rhel = 'rhel-' + release_with_openstack

    # cross check
    matching_images = get_all_images_with_tag(public_registry, nightly_with_openstack)
    [print(i) for i in matching_images]
    print()
    print()
    print()
    print()
    print()
    if set(matching_images) != set(current_containers):
        print('Current container list mismatch')
        print('In registry but not on list:')
        print(set(matching_images).difference(current_containers))
        print('On list but not in registry:')
        print(set(current_containers).difference(matching_images))
    print(len(current_containers))
    # PUBLIC NEWTON
    if True:
        retag(current_containers,   nightly_registry,  nightly_with_openstack,      public_registry,  [nightly_with_openstack])
    # PUBLIC
    if False:
        retag(current_containers,   nightly_registry,  nightly_with_openstack,      public_registry,  [nightly_nostack, nightly_with_openstack])
        retag(["contrail-go"],      nightly_registry,  nightly_nostack,             public_registry,  [nightly_nostack])
        retag(["contrail-test-test"],      public_registry,  nightly_with_openstack,             public_registry,  [nightly_nostack])
    # SANDBOX
    if False:
        retag(current_containers,   nightly_registry,  nightly_with_openstack,      sandbox_registry, [release_nostack, release_with_openstack, 'latest'])
        retag(["contrail-go"],      nightly_registry,  nightly_nostack,             sandbox_registry,  [release_nostack, 'latest'])
        retag(["contrail-test-test"],      public_registry,  nightly_with_openstack,             sandbox_registry,  [release_nostack, release_with_openstack, 'latest'])
        retag(['contrail-command'], private_registry, 'latest',                    sandbox_registry, [release_nostack, 'latest'])
    # RHEL
    if False:
        retag(current_containers,   nightly_registry,  nightly_with_openstack_rhel, sandbox_registry, [release_with_openstack_rhel, release_nostack_rhel])
        retag(current_containers,   nightly_registry,  nightly_with_openstack_rhel, public_registry, [nightly_with_openstack_rhel, nightly_nostack_rhel])
    # DOCKERHUB
    if False:
        retag(current_containers,   public_registry,  nightly_with_openstack,      dockerhub,        [nightly_with_openstack, nightly_nostack])

    sys.exit(0)
    for container in contrail_containers:
        if container not in current_containers:
            continue
        print(container, 'tags ==============================================')
        tags = get_tag_list(registry, container)
        #[print(t) for t in tags]
        # check if all required tags are present
        for openstack_version in openstack_versions:
            base_tag = openstack_version + '-5.0-' + build_number
            release_tag = '5.0.0-0.' + build_number + '-' + openstack_version
            nostack_tag = '5.0.0-0.' + build_number
            print('Will tag', container + ':' + base_tag, 'as', release_tag)
            if openstack_version == 'ocata':
                print('Will tag', container + ':' + base_tag, 'as', nostack_tag)
        required_tags = ['-'.join(ver) for ver in itertools.product(openstack_versions, versions, [build_number])]
        required_tags = [x[0] + x[1] for x in itertools.product(['rhel-', ''], required_tags)]
        for tag in required_tags:
            if tag not in tags:
                print('Tag', tag, 'not available for', container, 'in', registry)

    sys.exit(0)

    for cont in current_containers:
        print('Processing', cont)
        pulled = client.images.pull(registry + '/' + cont, tag=tag)
        for t in [tag, tag_short]:
            print('Tagging', cont, t)
            pulled.tag('opencontrailnightly/' + cont, tag=t)
            print('Pushing', cont, t)
            ret = client.images.push('opencontrailnightly/' + cont, tag=t)
    # push latest tags as the last step to minimize time of inconsistent tagging
    for cont in current_containers:
        print('Processing', cont)
        t = 'latest'
        print('Tagging', cont, t)
        pulled.tag('opencontrailnightly/' + cont, tag=t)
        print('Pushing', cont, t)
        ret = client.images.push('opencontrailnightly/' + cont, tag=t)
    conts = client.containers.list()
    #print(conts)


pull =   True
do_tag = True
push =   True


def retag(containers, src_registry, src_tag, dst_registry, dst_tags, skip_checks=False):
    if not skip_checks:
        registry_containers = get_container_list(src_registry)
    for container in containers:
        if not skip_checks and container not in registry_containers:
            print('Container', container, 'missing from', src_registry)
            continue
        if not skip_checks:
            tags = get_tag_list(src_registry, container)
            if src_tag not in tags:
                print('Tag', src_tag, 'not available for', container, 'in', src_registry)
                raise Exception('Image with source tag not available')
            orig_id = get_image_id_from_registry(src_registry, container, src_tag)
        if pull:
            print('Pulling', src_registry, container, src_tag)
            pulled = client.images.pull(src_registry + '/' + container, tag=src_tag)
        for dst_tag in dst_tags:
            target = dst_registry + '/' + container
            if not skip_checks:
                dest_id = get_image_id_from_registry(dst_registry, container, dst_tag)
                if dest_id is not None and dest_id == orig_id:
                    print('Image', target, 'already in dest registry, skipping push')
                    continue
                if dest_id is not None and dest_id != orig_id:
                    print('Image', target, 'already in dest registry WITH WRONG ID, exiting')
                    raise Exception('Image ID mismatch')
            print('Will tag\n', src_registry+'/'+container+':'+src_tag, 'as\n', target +':' + dst_tag)
            if do_tag:
                pulled.tag(target, tag=dst_tag)
            if do_tag and push:
                print('Pushing', target, dst_tag)
                for line in client.images.push(target, tag=dst_tag, stream=True):
                    print(line, end='')
    if push and not skip_checks:
        for container in containers:
            orig_id = get_image_id_from_registry(src_registry, container, src_tag)
            for dst_tag in dst_tags:
                pushed_id = get_image_id_from_registry(dst_registry, container, dst_tag)


def clearcontainers():
    client = docker.from_env()
    containers = client.containers.list()
    print("Will delete containers:")
    [print(c.name, c.image) for c in containers]
    print("Ok?")
    sys.stdin.readline()
    retries = 3
    for container in containers:
        for i in range(retries):
            try:
                print("Stopping", container.name, i, '...')
                container.stop()
                print("Removing", container.name, i, '...')
                container.remove()
                break
            except Exception as e:
                pass


def clearimages():
    images = client.images.list()
    print("Will delete images:")
    [print(c.name) for c in images]
    print("Ok?")
    sys.stdin.readline()


def clearall():
    clearcontainers()
    clearimages()


def setup_logging(log_level):
    log.setLevel(log_level)
    console = logging.StreamHandler()
    console.setLevel(log_level)
    #console.setFormatter(formatter)
    log.addHandler(console)


def main(cmd):
    parser = argparse.ArgumentParser(description="Contrail Artifact Curator")
    parser.add_argument("action", type=str)
    parser.add_argument("--registry", default=public_registry)
    parser.add_argument("--dry-run", type=bool, default=True, help="Don't delete anything", dest="dry_run")
    parser.add_argument("--repository", default=argparse.SUPPRESS)
    parser.add_argument("--tag", default=argparse.SUPPRESS)
    args = parser.parse_args()

    setup_logging(logging.DEBUG)
    args_dict = vars(args).copy()
    del args_dict['action']

    try:
        globals()[args.action](**args_dict)
        sys.exit(0)
    except Exception as e:
        log.error("Got exception when trying to launch global function for action %s: %s", args.action, e)

    if args.action == "tag":
        tag()
    elif args.action == "publish_nightly":
        publish_nightly()
    elif args.action == "clearall":
        clearall()
    elif args.action == "clearcontainers":
        clearcontainers()
    elif args.action == "clearimages":
        clearimages()
    elif args.action == "compare_registries":
        compare_registries()
    elif args.action == "list_registry":
        list_registry()
    elif args.action == "list_repositories":
        list_repositories(**args_dict)
    elif args.action == "list_repository_tags":
        list_repository_tags(**args_dict)
    elif args.action == "list_all_images_matching_tag":
        list_all_images_matching_tag(**args_dict)
    elif args.action == "list_tags":
        list_tags(**args_dict)
    elif args.action == "clean_tag":
        clean_tag(**args_dict)
    elif args.action == "remove_repository_from_registry":
        remove_repository_from_registry()
    elif args.action == "remove_tag_from_registry":
        remove_tag_from_registry(**args_dict)
    else:
        print('No command')


if __name__ == "__main__":
    cmd = sys.argv[1]
    main(cmd)
