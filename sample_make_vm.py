#!/usr/bin/python
from novaclient import client

if __name__ == "__main__":
    version = '2'
    username = 'admin'
    api_key = 'admin'
    project_id = 'admin'
    auth_url = 'http://10.20.0.11:5000/v2.0'

    instance_test = {'name': 'yhs_test',
                 'image': 'cirros-0.3.4-x86_64',
                 'flavor': 'm1.tiny',
                 'zone': 'nova',
                 'networks': ['net_test'],
                 'securitygroups': ['test-sg1', 'default']}

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

    # delete instance
    '''
    instance_ret = nova.servers.list(search_opts={'name': instance_test['name']})

    print str(instance_ret)
    for ins in instance_ret:
        delete_result = nova.servers.delete(ins)
        print str(ins) + ' result = ' + str(delete_result)
    '''