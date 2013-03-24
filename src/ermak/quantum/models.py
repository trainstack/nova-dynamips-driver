from sqlalchemy import Column, Integer, String, Boolean

import json
from quantum.db.models import BASE
from quantum.db.models import QuantumBase
from sqlalchemy.schema import ForeignKey, PrimaryKeyConstraint
from quantum.const import PORT_ID


class UdpLink(BASE, QuantumBase):
    __tablename__ = 'udp_links'
    __table_args__ = (
        PrimaryKeyConstraint("cidr"),
    )

    net_uuid = Column(String(255), nullable=True)
    left_port_uuid = Column(String(255), nullable=True)
    right_port_uuid = Column(String(255), nullable=True)

    cidr = Column(String(255), nullable=False)
    left = Column(String(255), nullable=False)
    right = Column(String(255), nullable=False)
    port = Column(Integer, nullable=False)

    def __init__(self, cidr, left, right, port):
        self.cidr = cidr
        self.left = left
        self.right = right
        self.port = port

    def __repr__(self):
        return "<UdpLink(%s)>" % (self.cidr)


class PortAttributes(BASE, QuantumBase):
    __tablename__ = 'port_attrs'
    __table_args__ = (
            PrimaryKeyConstraint("port_uuid"),
        )

    port_uuid = Column(String(255),
        ForeignKey('ports.uuid', ondelete='CASCADE'), nullable=True)
    attributes_json = Column(String(255), nullable=False)

    def __init__(self, port_uuid, data):
        self.port_uuid = port_uuid
        self.attributes = data

    @property
    def attributes(self):
        return json.loads(self.attributes_json)

    @attributes.setter
    def attributes(self, data):
        self.attributes_json = json.dumps(data)

    def __repr__(self):
        return "<PortAttributes(%s,%s)>" % (
            self.port_uuid, self.attributes_json)


class UdpChannelPort(object):

    def __init__(self, port_id, src_address, src_port,
                 dst_address, dst_port):
        self.src_address = src_address
        self.src_port = src_port
        self.dst_address = dst_address
        self.dst_port = dst_port
        self.port_id = port_id

    def __iter__(self):
        data = {'src_address': self.src_address,
                'src_port': self.src_port,
                'dst_address': self.dst_address,
                'dst_port': self.dst_port,
                PORT_ID: self.port_id}
        return data.iteritems()