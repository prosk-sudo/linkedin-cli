import json
import mimetypes
import linkedin.utils.config as config
import logging
from urllib import request, parse


logger = logging.getLogger(__name__)

REST_API_VERSION = "202601"


class MemberNetworkVisibility():
    CONNECTIONS = "CONNECTIONS"
    PUBLIC = "PUBLIC"


class Linkedin():
    def _rest_headers(self):
        return {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + config.getConfig().CONFIG['access_token'],
            'LinkedIn-Version': REST_API_VERSION,
            'X-Restli-Protocol-Version': '2.0.0',
        }

    def _initialize_image_upload(self, owner_urn):
        url = "https://api.linkedin.com/rest/images?action=initializeUpload"
        data = json.dumps({
            "initializeUploadRequest": {
                "owner": owner_urn
            }
        }).encode('utf-8')
        req = request.Request(url, data=data, headers=self._rest_headers())
        response = request.urlopen(req)
        result = json.loads(response.read().decode('utf-8'))
        value = result['value']
        return value['uploadUrl'], value['image']

    def _upload_image_binary(self, upload_url, file_path):
        content_type, _ = mimetypes.guess_type(file_path)
        if content_type is None:
            content_type = 'application/octet-stream'
        with open(file_path, 'rb') as f:
            image_data = f.read()
        req = request.Request(upload_url, data=image_data, method='PUT', headers={
            'Content-Type': content_type,
            'Authorization': 'Bearer ' + config.getConfig().CONFIG['access_token'],
        })
        response = request.urlopen(req)
        logger.debug("Image upload response: %s", response.getcode())

    def post_with_images(self, visibility, content, image_paths):
        cfg = config.getConfig().CONFIG
        owner_urn = cfg['urn']

        image_urns = []
        for path in image_paths:
            logger.info("Uploading image: %s", path)
            upload_url, image_urn = self._initialize_image_upload(owner_urn)
            self._upload_image_binary(upload_url, path)
            image_urns.append(image_urn)
            logger.info("Image uploaded: %s", image_urn)

        data = {
            "author": owner_urn,
            "commentary": content,
            "visibility": visibility,
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": []
            },
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False
        }

        if len(image_urns) == 1:
            data["content"] = {
                "media": {
                    "id": image_urns[0]
                }
            }
        else:
            data["content"] = {
                "multiImage": {
                    "images": [{"id": urn} for urn in image_urns]
                }
            }

        logger.debug(data)
        url = "https://api.linkedin.com/rest/posts"
        encoded = json.dumps(data).encode('utf-8')
        req = request.Request(url, data=encoded, headers=self._rest_headers())
        response = request.urlopen(req)
        logger.debug("Response code: %s", response.getcode())
        post_urn = response.headers.get('x-restli-id', '')
        logger.info("Post with images sent!")
        return post_urn

    def delete_post(self, post_urn):
        encoded_urn = parse.quote(post_urn, safe='')
        url = "https://api.linkedin.com/rest/posts/" + encoded_urn
        headers = self._rest_headers()
        del headers['Content-Type']
        req = request.Request(url, method='DELETE', headers=headers)
        response = request.urlopen(req)
        logger.debug("Response code: %s", response.getcode())

    def post(self, visibility, content):
        data = {
            "author": config.getConfig().CONFIG['urn'],
            "commentary": content,
            "visibility": visibility,
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": []
            },
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False
        }
        logger.debug(data)
        url = "https://api.linkedin.com/rest/posts"
        encoded = json.dumps(data).encode('utf-8')
        req = request.Request(url, data=encoded, headers=self._rest_headers())
        response = request.urlopen(req)
        logger.debug("Response code: %s", response.getcode())
        post_urn = response.headers.get('x-restli-id', '')
        logger.info("Post sent!")
        return post_urn
