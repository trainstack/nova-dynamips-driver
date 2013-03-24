import logging

from quantum.api.api_common import OperationalStatus
from quantum.common import exceptions
from quantum.db import api as db
from quantum.quantum_plugin_base import QuantumPluginBase
from dynagen import dynamips_lib

from ermak.quantum.const import *
from ermak.quantum import db as plugin_db

LOG = logging.getLogger("quantum.plugin.dynamips_udp")
dynamips_lib.debug = LOG.debug


def net_dict(net):
    return {NET_ID: net[UUID],
            NET_NAME: net[NETWORKNAME],
            NET_OP_STATUS: net[OPSTATUS]}


def port_dict(port):
    if port[PORTSTATE] == PORT_UP:
        op_status = port[PORT_STATE]
    else:
        op_status = OperationalStatus.DOWN
    return {PORT_ID: str(port[UUID]),
            PORT_STATE: port[PORTSTATE],
            PORT_OP_STATUS: op_status,
            NET_ID: port[NETWORKID],
            ATTACHMENT: port[INTERFACEID]}


def auth_tenant_net(f):
    def validated(self, tenant_id, net_id, *args, **kwargs):
        db.validate_network_ownership(tenant_id, net_id)
        return f(self, tenant_id, net_id, *args, **kwargs)
    return validated


def auth_tenant_net_port(f):
    def validated(self, tenant_id, net_id, port_id, *args, **kwargs):
        db.validate_port_ownership(tenant_id, net_id, port_id)
        return f(self, tenant_id, net_id, port_id, *args, **kwargs)
    return validated


class UdpSocketPlugin(QuantumPluginBase):

    supported_extension_aliases = ['udp-channels', 'port-metadata']

    def __init__(self):
        plugin_db.initialize()

    def get_all_networks(self, tenant_id, **kwargs):
        network_list = db.network_list(tenant_id)
        return map(net_dict, network_list)

    @auth_tenant_net
    def get_network_details(self, tenant_id, net_id):
        net = db.network_get(net_id)
        ports = db.port_list(net_id)
        result = net_dict(net)
        result[NET_PORTS] = map(port_dict, ports)
        return result

    def create_network(self, tenant_id, net_name, **kwargs):
        new_network = db.network_create(tenant_id, net_name,
            op_status=OperationalStatus.DOWN)
        try:
            plugin_db.allocate_udp_link(new_network[UUID])
            return net_dict(new_network)
        except Exception:
            db.network_destroy(new_network[UUID])
            raise

    @auth_tenant_net
    def update_network(self, tenant_id, net_id, **kwargs):
        net = db.network_update(net_id, tenant_id, **kwargs)
        return net_dict(net)

    @auth_tenant_net
    def delete_network(self, tenant_id, net_id):
        net = db.network_get(net_id)
        ports = db.port_list(net_id)
        if not len(ports) and any(map(lambda p: p[INTERFACEID], ports)):
            raise exceptions.NetworkInUse(net_id=net_id)
        for port in ports:
            self.delete_port(tenant_id, net_id, port[UUID])
        plugin_db.deallocate_udp_link(net_id)
        db.network_destroy(net_id)
        return net_dict(net)

    @auth_tenant_net_port
    def plug_interface(self, tenant_id, net_id, port_id, remote_interface_id):
        port = db.port_get(port_id, net_id)
        if port[INTERFACEID]:
            raise exceptions.AlreadyAttached(port_id=port_id, net_id=net_id,
                                             att_id=remote_interface_id,
                                             att_port_id=port[INTERFACEID])
        db.port_set_attachment(port_id, net_id, remote_interface_id)

    @auth_tenant_net_port
    def unplug_interface(self, tenant_id, net_id, port_id):
        db.port_set_attachment(port_id, net_id, "")
        db.port_update(port_id, net_id, op_status=OperationalStatus.DOWN)


    @auth_tenant_net
    def get_all_ports(self, tenant_id, net_id, **kwargs):
        ports = db.port_list(net_id)
        return map(port_dict, ports)

    @auth_tenant_net_port
    def get_port_details(self, tenant_id, net_id, port_id):
        port = db.port_get(port_id, net_id)
        return port_dict(port)

    @auth_tenant_net
    def create_port(self, tenant_id, net_id, port_state=None, **kwargs):
        port = db.port_create(net_id, port_state,
            op_status=OperationalStatus.DOWN)
        try:
            plugin_db.allocate_udp_for_port(net_id, port[UUID])
            return port_dict(port)
        except Exception:
            db.port_destroy(port[UUID], net_id)
            raise

    @auth_tenant_net_port
    def update_port(self, tenant_id, net_id, port_id, **kwargs):
        port = db.port_update(port_id, net_id, **kwargs)
        # TODO: validate check port state (???)
        return port_dict(port)

    @auth_tenant_net_port
    def delete_port(self, tenant_id, net_id, port_id):
        port = db.port_get(port_id, net_id)
        if port[INTERFACEID]:
            raise exceptions.PortInUse(port_id=port_id, net_id=net_id,
                                       att_id=port[INTERFACEID])
        plugin_db.deallocate_udp_for_port(net_id, port_id)
        db.port_destroy(port_id, net_id)
        return port_dict(port)

    @auth_tenant_net_port
    def get_udp_port(self, tenant_id, network_id, port_id):
        return plugin_db.get_udp_for_port(network_id, port_id)

    @auth_tenant_net_port
    def get_port_attrs(self, tenant_id, network_id, port_id):
        return plugin_db.get_attrs_for_port(port_id)

    @auth_tenant_net_port
    def set_port_attrs(self, tenant_id, network_id, port_id, metadata):
        return plugin_db.set_attrs_for_port(port_id, metadata)