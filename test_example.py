#!/usr/bin/python3

import utils

import sys
import os
import re

OPT_CNI_BIN_FILE = 'opt-cni-bin'
NODES_DIR = 'nodes'
#IMAGE = 'docker.io/mmirecki/must-gather7'
IMAGE = 'quay.io/kubevirt/must-gather'


config = sys.argv[1]


os.environ["KUBECONFIG"] = config


CMD_NODE_CNI_BIN = 'oc exec -i {ng_ds_pod} -n node-gather --config={config} -- ls -l /host/opt/cni/bin'

OC_EXEC_COMMAND = 'oc exec -i {ng_ds_pod} -n node-gather --config={config} -- {resource_cmd}'

def check_node_resource(config, resulsts_dir, node, ng_ds_pod, file_path, resource_cmd, name):
    file_name = os.path.join('.', os.path.join(
        os.path.join(resulsts_dir, NODES_DIR),
        os.path.join(node, file_path)
    ))
    with open(file_name) as resource_file:
        file_content = resource_file.read()

        cmd = OC_EXEC_COMMAND.format(config=config, ng_ds_pod=ng_ds_pod, resource_cmd=resource_cmd).split()

        cmd_output, return_code = utils.execute(cmd)
        cmd_output = cmd_output.decode("utf-8")

        if file_content == cmd_output:
            print('    {name} MATCHES'.format(name=name))
        else:
            print('ERROR: {name} DOES NOT MATCH'.format(name=name))


OPT_CNI_CONFIG_DIR = 'etc/cni/net.d'
def check_cni_config_files(config, resulsts_dir, node, ng_ds_pod):
    cni_config_dir_name = os.path.join(os.path.join(resulsts_dir, NODES_DIR), os.path.join(node, OPT_CNI_CONFIG_DIR))
    for cni_config_file_name in os.listdir(cni_config_dir_name):
        check_node_resource(
            config, resulsts_dir, node, ng_ds_pod,
            os.path.join(OPT_CNI_CONFIG_DIR, cni_config_file_name),
            'cat /host/etc/cni/net.d/{file_name}'.format(file_name=cni_config_file_name),
            'CNI CONFIG'
        )

def check_nft_files(config, resulsts_dir, node, ng_ds_pod):
    nft_dir_name = os.path.join(os.path.join(resulsts_dir, NODES_DIR), node)
    files = [f for f in os.listdir(nft_dir_name) if re.match(r'nft-*', f)]
    for nft_file_name in files:
        nft_parts = nft_file_name.split('-')

        resource_cmd = 'nft list table {family} {table}'.format(family=nft_parts[1], table=nft_parts[2])
        cmd = OC_EXEC_COMMAND.format(config=config, ng_ds_pod=ng_ds_pod, resource_cmd=resource_cmd)
        _, return_code = utils.execute(cmd.split())
        # We can not compare content, as packet/byte count changes too fast.
        if return_code == 0:
            print('    NFT file present')
        else:
            print('ERROR: NFT file NOT present')

def check_nodes(results_dir, config):
    utils.create_node_gather_ds(config)

    nodes = utils.get_node_gather_ds(config)
    print('NODES ' + str(nodes))

    if __name__ == '__main__':
        for node in nodes.keys():
            print('NODE: {node}'.format(node=node))


            check_node_resource(
                config, results_dir, node, nodes[node], 'opt-cni-bin',
                'ls -l /host/opt/cni/bin', 'CNI BIN'
            )

            check_node_resource(
                config, results_dir, node, nodes[node], 'ip.txt',
                'ip a', 'IP ADDR'
            )

            check_node_resource(
                config, results_dir, node, nodes[node], 'bridge',
                'ip -o link show type bridge', 'BRIDGE'
            )

            check_node_resource(
                config, results_dir, node, nodes[node], 'vlan',
                'bridge -j vlan show', 'VLANS'
            )

            check_node_resource(
                config, results_dir, node, nodes[node], 'dev_vfio',
                'ls -al /host/dev/vfio/', 'VFIO'
            )

            check_node_resource(
                config, results_dir, node, nodes[node], 'dmesg',
                'dmesg', 'dmesg'
            )

            check_node_resource(
                config, results_dir, node, nodes[node], 'proc_cmdline',
                'cat /host/proc/cmdline', 'proc_cmdline'
            )

            check_node_resource(
                config, results_dir, node, nodes[node], 'lspci',
                'lspci -vv', 'lspci'
            )

            check_node_resource(
                config, results_dir, node, nodes[node], 'pcidp_config.json',
                'cat /host/etc/pcidp/config.json', 'pcidp_config'
            )


            check_cni_config_files(config, results_dir, node, nodes[node])
            check_nft_files(config, results_dir, node, nodes[node])

        utils.delete_node_gather_ds(config)



def check_namespaces(results_dir, config):

    namespaces_to_check = (
        'nmstate', 'kubemacpool-system', 'linux-bridge', 'openshift-sdn', 'cluster-network-addons-operator', 'sriov',
        'kubevirt-hyperconverged', 'openshift-operator-lifecycle-manager', 'openshift-marketplace',
        #'cdi', 'kubevirt-web-ui', '', '', '', '', '', '', '', '', '',

    )

    for namespace in namespaces_to_check:
        utils.check_resource(
            config,
            results_dir,
            'ns/{namespace}'.format(namespace=namespace),
            'namespaces/{namespace}/{namespace}.yaml'.format(namespace=namespace),
            ('spec')
        )

def check_resources(results_dir, config):

    utils.check_list_of_resources(
        config,
        results_dir,
        'NetworkAddonsConfig',
        'cluster-scoped-resources/networkaddonsoperator.network.kubevirt.io/networkaddonsconfigs/{name}.yaml',
        (('spec',),)
    )

    utils.check_list_of_resources(
        config,
        results_dir,
        'network-attachment-definitions',
        'namespaces/{namespace}/k8s.cni.cncf.io/network-attachment-definitions/{name}.yaml',
        (
            ('spec',),
            ('metadata', 'uid'),
            ('metadata', 'name'),
            ('metadata', 'namespace'),
        )
    )

    utils.check_list_of_resources(
        config,
        results_dir,
        'nodenetworkstates',
        'cluster-scoped-resources/nmstate.io/nodenetworkstates/{name}.yaml',
        (
            ('spec',),
            ('metadata', 'uid'),
            ('metadata', 'name'),
        )
    )

    utils.check_list_of_resources(
        config,
        results_dir,
        'istag',
        'namespaces/openshift/image.openshift.io/imagestreamtags/{name}.yaml',
        (
            ('image', 'dockerImageReference'),
            ('tag', 'name'),
            ('tag', 'from'),
            ('metadata', 'uid'),
            ('metadata', 'name'),
            ('metadata', 'namespace'),
         )
    )


    utils.check_list_of_resources(
        config,
        results_dir,
        'virtualmachines',
        'namespaces/{namespace}/kubevirt.io/virtualmachines/{name}.yaml',
        (
            ('spec',),
            ('metadata', 'uid'),
            ('metadata', 'name'),
        )
    )

##################


utils.pre_run_check()
print('Collecting must-gather data')
utils.run_must_gather(IMAGE, config)
print('Must-gather data collected')
results_dir = utils.get_results_dir()

check_nodes(results_dir, config)

check_namespaces(results_dir, config)

check_resources(results_dir, config)

