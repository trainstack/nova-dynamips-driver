import json
from bson.errors import InvalidId
from bson.objectid import ObjectId
from flask import Flask, request
from mongokit.schema_document import ValidationError
import logging

from ermak.api import db, facade
from ermak.api.views import *

app = Flask(__name__)


def api_response(payload = None, status=200, headers=None):
    all_headers = {'Content-Type': 'application/json'}
    if headers is not None:
        all_headers.update(headers)
    if payload is None:
        payload = {}
    return json.dumps(payload), status, all_headers


@app.route("/<tenant>/instances", methods=["GET"])
def instance_list(tenant):
    instances = db.get_instances_all(tenant)
    return api_response(status=200, payload=map(instance_to_json, instances))


@app.route("/<tenant>/instances/<id>", methods=["GET"])
def instance_get(tenant, id):
    try:
        instance_id = ObjectId(id)
    except InvalidId as e:
        return api_response(status=400, payload={'error': str(e)})
    try:
        instance = db.get_instance_by_id(tenant, instance_id)
        return api_response(status=200, payload=instance_to_json(instance))
    except LookupError:
        return api_response(
            status=404, payload={'error': "Instance with id %s not found" % id})


@app.route("/<tenant>/instances", methods=["POST"])
def instance_create(tenant):
    try:
        content = json.loads(request.data)
    except Exception as e:
        return api_response(status=400, payload={'error': "Can not parse json: %s" % str(e)})
    try:
        instance = instance_from_json(content)
        instance['tenant'] = tenant
    except ValidationError as e:
        return api_response(status=400, payload={'error': str(e)})
    saved = facade.launch_instance({}, instance)
    return api_response(status=201, payload=instance_to_json(saved))



@app.route("/<tenant>/instances/<id>", methods=["DELETE"])
def instance_delete(tenant, id):
    try:
        instance_id = ObjectId(id)
    except InvalidId as e:
        return api_response(status=400, payload={'error': str(e)})
    try:
        instance = db.get_instance_by_id(tenant, instance_id)
    except LookupError:
        return api_response(
            status=404, payload={'error': "Instance with id %s not found" % id})
    destroyed = facade.destroy_instance({}, instance)
    return api_response(status=200, payload=instance_to_json(destroyed))


if __name__ == '__main__':
    db.init_db("mongodb://localhost/ermak-test")
    app.run(debug=True)