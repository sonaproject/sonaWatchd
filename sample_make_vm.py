#!/usr/bin/python
import time
from novaclient import client

if __name__ == "__main__":
    version = '2'
    username = 'admin'
    api_key = 'admin'
    project_id = 'admin'
    auth_url = 'http://192.168.0.213:5000/v2.0'

    instance_test = {'name': 'yhs_test',
                 'image': 'yhs_test',
                 'flavor': 'm1.large',
                 'zone': 'nova',
                 'networks': ['net1'],
                 'securitygroups': ['all_allow']}

    nova = client.Client(version, username, api_key, project_id, auth_url)

    # get vm list
    print str(nova.servers.list())

    # get image list
    print str(nova.images.list())

    # get flavor list
    print str(nova.flavors.list())

    # get networks list
    print str(nova.networks.list())

    network_list = []
    for net in instance_test['networks']:
        network_list.append({'net-id': nova.networks.find(label=net).id})

    print str(network_list)

    image = nova.images.find(name=instance_test['image'])
    flavor = nova.flavors.find(name=instance_test['flavor'])

    # create instance
    instance_rst = nova.servers.create(name=instance_test['name'],
                                       image=image,
                                       flavor=flavor,
                                       availability_zone=instance_test['zone'],
                                       nics=network_list,
                                       security_groups=instance_test['securitygroups'])


    print instance_rst

    floatingip_list = nova.floating_ips.list()

    extra_floatingip = ''
    for a in floatingip_list:
        if not a.fixed_ip:
            extra_floatingip = a.ip
            break

    if not extra_floatingip:
        extra_floatingip = nova.floating_ips.create('ext-net').ip

    print('floating ip = ' + extra_floatingip)

    time.sleep(1)
    instance_rst.add_floating_ip(extra_floatingip)

    # delete instance
    '''
    instance_ret = nova.servers.list(search_opts={'name': instance_test['name']})

    print str(instance_ret)
    for ins in instance_ret:
        delete_result = nova.servers.delete(ins)
        print str(ins) + ' result = ' + str(delete_result)
    '''
