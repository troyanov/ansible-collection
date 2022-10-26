# -*- coding: utf-8 -*-
# # Copyright: (c) 2022, XLAB Steampunk <steampunk@xlab.si>
#
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

from ansible_collections.canonical.maas.plugins.module_utils.machine import Machine

__metaclass__ = type

import sys

import pytest

from ansible_collections.canonical.maas.plugins.module_utils.network_interface import (
    NetworkInterface,
)
from ansible_collections.canonical.maas.plugins.module_utils.client import (
    Response,
)
from ansible_collections.canonical.maas.plugins.module_utils import errors


pytestmark = pytest.mark.skipif(
    sys.version_info < (2, 7), reason="requires python2.7 or higher"
)


class TestMapper:
    @staticmethod
    def _get_net_interface():
        return dict(
            name="test_net_int",
            id=123,
            system_id=1234,
            mac_address="this-mac",
            tags=[],
            effective_mtu=1500,
            links=[
                dict(
                    subnet=dict(cidr="ip", vlan=dict(name="vlan-1", fabric="fabric-1"))
                )
            ],
        )

    @staticmethod
    def _get_net_interface_discovered():
        return dict(
            name="test_net_int",
            id=123,
            system_id=1234,
            mac_address="this-mac",
            tags=[],
            effective_mtu=1500,
            discovered=[
                dict(
                    subnet=dict(cidr="ip", vlan=dict(name="vlan-1", fabric="fabric-1"))
                )
            ],
            links=[],
        )

    @staticmethod
    def _get_net_interface_api_missing():
        return dict(
            name="test_net_int",
            id=123,
            system_id=1234,
            mac_address="this-mac",
            tags=[],
            discovered=[
                dict(
                    subnet=dict(cidr="ip", vlan=dict(name="vlan-1", fabric="fabric-1"))
                )
            ],
        )

    @staticmethod
    def _get_net_interface_from_ansible():
        return dict(name="test_net", subnet_cidr="ip")

    def test_from_maas_links(self):
        maas_net_interface_dict = self._get_net_interface()
        net_interface = NetworkInterface(
            maas_net_interface_dict["name"],
            maas_net_interface_dict["id"],
            maas_net_interface_dict["links"][0]["subnet"]["cidr"],
            maas_net_interface_dict["system_id"],
        )
        results = NetworkInterface.from_maas(maas_net_interface_dict)
        assert (
            results.name == net_interface.name
            and results.id == net_interface.id
            and results.machine_id == net_interface.machine_id
            and results.subnet_cidr == net_interface.subnet_cidr
        )

    def test_from_maas_discovered(self):
        maas_net_interface_dict = self._get_net_interface_discovered()
        net_interface = NetworkInterface(
            maas_net_interface_dict["name"],
            maas_net_interface_dict["id"],
            maas_net_interface_dict["discovered"][0]["subnet"]["cidr"],
            maas_net_interface_dict["system_id"],
        )
        results = NetworkInterface.from_maas(maas_net_interface_dict)
        assert (
            results.name == net_interface.name
            and results.id == net_interface.id
            and results.machine_id == net_interface.machine_id
            and results.subnet_cidr == net_interface.subnet_cidr
        )

    def test_from_maas_api_key_missing(self):
        maas_net_interface_dict = self._get_net_interface_api_missing()
        with pytest.raises(
            errors.MissingValueMAAS,
            match="Missing value from MAAS API - 'effective_mtu'",
        ):
            NetworkInterface.from_maas(maas_net_interface_dict)

    def test_from_ansible(self):
        net_interface_dict = self._get_net_interface_from_ansible()
        net_interface = NetworkInterface(
            name=net_interface_dict["name"],
            subnet_cidr=net_interface_dict["subnet_cidr"],
        )
        results = NetworkInterface.from_ansible(net_interface_dict)
        assert (
            results.name == net_interface.name
            and results.subnet_cidr == net_interface.subnet_cidr
        )

    def test_to_maas(self):
        net_interface_dict = self._get_net_interface()
        expected = dict(
            name="test_net_int",
            id=123,
            subnet_cidr="ip",
            mac_address="this-mac",
            ip_address="this-ip",
            fabric="fabric-1",
            vlan="this-vlan",
            label_name="this-interface",
            mtu=1500,
        )
        net_interface_obj = NetworkInterface(
            net_interface_dict["name"],
            net_interface_dict["id"],
            net_interface_dict["links"][0]["subnet"]["cidr"],
            net_interface_dict["system_id"],
            "this-mac",
            "this-vlan",
            1500,
            [],
            "this-ip",
            net_interface_dict["links"][0]["subnet"]["vlan"]["fabric"],
            "this-interface",
        )
        results = net_interface_obj.to_maas()
        assert results == expected

    def test_to_ansible(self):
        net_interface_dict = self._get_net_interface()
        expected = dict(
            id=123,
            name="test_net_int",
            subnet_cidr="ip",
            ip_address="this-ip",
            fabric="this-fabric",
            vlan="this-vlan",
            mac_address="this-mac",
            mtu=1500,
            tags=None,
        )
        net_interface_obj = NetworkInterface(
            net_interface_dict["name"],
            net_interface_dict["id"],
            net_interface_dict["links"][0]["subnet"]["cidr"],
            net_interface_dict["system_id"],
            "this-mac",
            "this-vlan",
            1500,
            None,
            "this-ip",
            "this-fabric",
            "this-label",
        )
        results = net_interface_obj.to_ansible()
        assert results == expected


class TestNeedsUpdate:
    @staticmethod
    def get_nic():
        return dict(
            name="this-nic",
            id=123,
            mac_address="this-mac",
            system_id=123,
            tags=["tag1", "tag2"],
            effective_mtu=1500,
            ip_address="this-ip",
            subnet_cidr="this-subnet",
            vlan=None,
            links=[],
        )

    @staticmethod
    def get_nic_other():
        return dict(
            name="this-nic",
            id=123,
            mac_address="this-mac-2",
            system_id=123,
            tags=["tag1", "tag2", "tag3"],
            effective_mtu=1700,
            ip_address="this-ip",
            subnet_cidr="this-subnet",
            vlan=None,
            links=[],
        )

    def test_needs_update_when_update_is_needed(self, mocker):
        new_nic_dict = self.get_nic()
        new_nic_obj = NetworkInterface.from_maas(new_nic_dict)
        other_nic_dict = self.get_nic_other()
        other_nic_obj = NetworkInterface.from_maas(other_nic_dict)
        results = other_nic_obj.needs_update(new_nic_obj)
        assert results is True

    def test_needs_update_when_update_is_not_needed(self):
        new_nic_dict = self.get_nic()
        new_nic_obj = NetworkInterface.from_maas(new_nic_dict)
        other_nic_dict = self.get_nic()
        other_nic_obj = NetworkInterface.from_maas(other_nic_dict)
        results = other_nic_obj.needs_update(new_nic_obj)
        assert results is False

    def test_eq_when_is_same(self):
        nic_dict = self.get_nic()
        other_nic_dic = self.get_nic_other()
        nic_obj = NetworkInterface.from_maas(nic_dict)
        other_nic_obj = NetworkInterface.from_maas(other_nic_dic)
        results = nic_obj != other_nic_obj
        assert results is True

    def test_eq_when_is_different(self):
        nic_dict = self.get_nic()
        other_nic_dic = self.get_nic_other()
        nic_obj = NetworkInterface.from_maas(nic_dict)
        other_nic_obj = NetworkInterface.from_maas(other_nic_dic)
        results = nic_obj == other_nic_obj
        assert results is False


class TestSendRequestAndPayload:
    @staticmethod
    def get_nic():
        return dict(
            name="this-nic",
            id=123,
            mac_address="this-mac",
            system_id=123,
            tags=["tag1", "tag2"],
            effective_mtu=1500,
            ip_address="this-ip",
            subnet_cidr="this-subnet",
            vlan=None,
            links=[],
        )

    @staticmethod
    def get_machine():
        return dict(
            fqdn="this-machine-fqdn",
            hostname="this-machine",
            cpu_count=2,
            memory=5000,
            system_id="123",
            interface_set=None,
            blockdevice_set=None,
            domain=dict(id=1),
            zone=dict(id=1),
            pool=dict(id=1),
            tag_names=["my_tag"],
            status_name="New",
            osystem="ubuntu",
            distro_series="jammy",
            hwe_kernel="ga-22.04",
            min_hwe_kernel="ga-22.04",
            power_type="this-power-type",
            architecture="this-architecture",
        )

    def test_nic_send_update_request(self, client):
        nic_dict = self.get_nic()
        nic_obj = NetworkInterface.from_maas(nic_dict)
        machine_dict = self.get_machine()
        machine_obj = Machine.from_maas(machine_dict)
        payload = nic_obj.payload_for_update()
        client.put.return_value = Response(200, '{"system_id": 123, "machine_id": 123}')
        results = nic_obj.send_update_request(client, machine_obj, payload, nic_obj.id)
        assert results == {"system_id": 123, "machine_id": 123}

    def test_nic_payload_for_update(self):
        nic_dict = self.get_nic()
        nic_obj = NetworkInterface.from_maas(nic_dict)
        results = nic_obj.payload_for_update()
        assert results == nic_obj.to_maas()

    def test_nic_send_create_request(self, client):
        nic_dict = self.get_nic()
        nic_obj = NetworkInterface.from_maas(nic_dict)
        machine_dict = self.get_machine()
        machine_obj = Machine.from_maas(machine_dict)
        payload = nic_obj.payload_for_create()
        client.post.return_value = Response(
            200, '{"system_id": 123, "machine_id": 123}'
        )
        results = nic_obj.send_create_request(client, machine_obj, payload)
        assert results == {"system_id": 123, "machine_id": 123}

    def test_nic_payload_for_create(self):
        nic_dict = self.get_nic()
        nic_obj = NetworkInterface.from_maas(nic_dict)
        results = nic_obj.payload_for_create()
        assert results == nic_obj.to_maas()

    def test_nic_send_delete_request(self, client):
        nic_dict = self.get_nic()
        nic_obj = NetworkInterface.from_maas(nic_dict)
        machine_dict = self.get_machine()
        machine_obj = Machine.from_maas(machine_dict)
        client.delete.return_value = None
        results = nic_obj.send_delete_request(client, machine_obj, nic_obj.id)
        assert results is None
