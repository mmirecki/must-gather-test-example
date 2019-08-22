#!/usr/bin/python3

import utils

import sys
import os

OPT_CNI_CONFIG_DIR = 'etc/cni/net.d'
OPT_CNI_BIN_FILE = 'opt-cni-bin'
NODES_DIR = 'nodes'
#IMAGE = 'docker.io/mmirecki/must-gather7'
IMAGE = 'quay.io/kubevirt/must-gather'


config = sys.argv[1]


os.environ["KUBECONFIG"] = config


CMD_NODE_CNI_BIN = 'oc exec -i {ng_ds_pod} -n node-gather --config={config} -- ls -l /host/opt/cni/bin'


def check_cni_bin_files(config, resulsts_dir, node, ng_ds_pod):
    cni_opt_cni_bin_file_name = os.path.join('.', os.path.join(
        os.path.join(resulsts_dir, NODES_DIR),
        os.path.join(node, OPT_CNI_BIN_FILE)
    ))
    with open(cni_opt_cni_bin_file_name) as cni_bin_file:
        cni_bin_file_content = cni_bin_file.read()

        cmd = CMD_NODE_CNI_BIN.format(config=config, ng_ds_pod=ng_ds_pod).split()

        cni_bin_output, return_code = utils.execute(cmd).decode("utf-8")

        if cni_bin_file_content == cni_bin_output:
            print('CNI BIN MATCHES')
        else:
            print('ERROR: CNI BIN DIR DOES NOT MATCH')


CMD_NODE_LS_CNI_CONFIG = 'oc exec -i {ng_ds_pod} -n node-gather --config={config} -- cat /host/etc/cni/net.d/{file_name}'


def check_cni_config_files(config, resulsts_dir, node, ng_ds_pod):
    cni_config_dir_name = os.path.join('.', os.path.join(
        os.path.join(resulsts_dir, NODES_DIR),
        os.path.join(node, OPT_CNI_CONFIG_DIR)
    ))

    for cni_config_file_name in os.listdir(cni_config_dir_name):
        cmd = CMD_NODE_LS_CNI_CONFIG.format(config=config, ng_ds_pod=ng_ds_pod, file_name=cni_config_file_name).split()
        cni_config_output, return_code = utils.execute(cmd).decode("utf-8")
        with open(os.path.join(cni_config_dir_name, cni_config_file_name)) as cni_config_file:
            cni_config_file_content = cni_config_file.read()
            if cni_config_file_content == cni_config_output:
                print('CNI CONFIG {} MATCHES'.format(cni_config_file_name))
            else:
                print('ERROR: CNI CONFIG {} MATCHES'.format(cni_config_file_name))


def check_ip_addr(config, results_dir, node, ng_ds_pod):
    pass

def check_nodes(results_dir, config):
    utils.create_node_gather_ds(config)

    nodes = utils.get_node_gather_ds(config)
    print('NODES ' + str(nodes))

    if __name__ == '__main__':
        for node in nodes.keys():
            check_cni_bin_files(config, results_dir, node, nodes[node])
            check_cni_config_files(config, results_dir, node, nodes[node])

            check_ip_addr(config, results_dir, node, nodes[node])

            # ...
            # ... check all items collected for nodes

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

    # Note: this assumes all is tags will be on the "latest" tag
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


    """
    # TODO
    check_list_of_resources(
        config,
        results_dir,
        'datavolumes',
        ''
    )

    # TODO
    check_list_of_resources(
        config,
        results_dir,
        'v2vvmwares',
        ''
    )

    # TODO
    check_list_of_resources(
        config,
        results_dir,
        'virtualmachineinstances',
        ''
    )

    # TODO
    check_list_of_resources(
        config,
        results_dir,
        'virtualmachineinstancereplicasets',
        ''
    )

    # TODO
    check_list_of_resources(
        config,
        results_dir,
        'virtualmachineinstancepresets',
        ''
    )

    # TODO
    check_list_of_resources(
        config,
        results_dir,
        'virtualmachineinstancemigrations',
        ''
    )

    # TODO
    check_list_of_resources(
        config,
        results_dir,
        'virtualmachines',
        ''
    )
"""








    # ... check all other resources collected by must-gather

##################


utils.pre_run_check()
print("1")
#utils.run_must_gather(IMAGE, config)
print("2")
results_dir = utils.get_results_dir()

# check_nodes(results_dir, config)

check_resources(results_dir, config)

