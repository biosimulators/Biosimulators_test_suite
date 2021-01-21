import os


class Config(object):
    def __init__(self, pull_docker_image=None):
        if pull_docker_image is not None:
            self.pull_docker_image = pull_docker_image
        else:
            self.pull_docker_image = os.getenv('PULL_DOCKER_IMAGE', '1').lower() in ['1', 'true']
