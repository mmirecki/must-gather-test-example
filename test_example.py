#!/usr/bin/python3


import subprocess
import sys
import re
import os
import yaml
from deepdiff import DeepDiff

config = sys.argv[1]

IMAGE = 'docker.io/mmirecki/must-gather7'

NODES_DIR = 'nodes'
OPT_CNI_CONFIG_DIR = 'etc/cni/net.d'

OPT_CNI_BIN_FILE = 'opt-cni-bin'

CMD_RUN_MUST_GATHER = '/usr/bin/oc adm must-gather --image={image} --config={config}'
CMD_RUN_GET_PODS = '/usr/bin/oc get pods --config={config}'

CMD_NG_DS_ADMIN = 'oc login -u system:admin --config={config}'
CMD_NG_DS_CRD = 'oc create -f node-gather-crd.yaml --config={config}'
CMD_NG_DS_ADD_SCC_TO_USER = 'oc adm policy add-scc-to-user privileged -n node-gather -z node-gather --config={config}'
CMD_NG_DS_DS = 'oc create -f node-gather-ds.yaml --config={config}'

CMD_NG_DS_DEL_DS = 'oc delete -f node-gather-ds.yaml --config={config}'
CMD_NG_DS_DEL_CRD = 'oc delete -f node-gather-crd.yaml --config={config}'


def _get_results_dirs():
    files = [f for f in os.listdir('.') if re.match(r'must-gather*', f)]
    return files


def pre_run_check():
    results = _get_results_dirs()
    if len(results) > 0:
        print('Results directory exists. Please run the script in an empty dir')
        # exit()


def get_results_dir():
    results = _get_results_dirs()
    if len(results) != 1:
        print('Zero or multiple results dirs. Must be exactly 1.')
        exit()
    return results[0]


def run_must_gather(image, config):
    cmd_run_must_gather = CMD_RUN_MUST_GATHER.format(image=image, config=config).split()
    execute(cmd_run_must_gather)


def create_node_gather_ds(config):
    execute(CMD_NG_DS_ADMIN.format(config=config).split())
    execute(CMD_NG_DS_CRD.format(config=config).split())
    execute(CMD_NG_DS_ADD_SCC_TO_USER.format(config=config).split())
    execute(CMD_NG_DS_DS.format(config=config).split())


def delete_node_gather_ds(config):
    execute(CMD_NG_DS_DEL_DS.format(config=config).split())
    execute(CMD_NG_DS_DEL_CRD.format(config=config).split())


def execute(cmd):
    out = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )
    #print('IN:' + ' '.join(cmd))
    stdout, stderr = out.communicate()
    #print('OUT:' + str(stdout))
    #print('ERR:' + str(stderr))

    return stdout


CMD_GET_DS_NODES = 'oc get pod -o=custom-columns=NODE:.spec.nodeName,NAME:.metadata.name --no-headers -n node-gather --config={config}'


def get_node_gather_ds(config):
    nodes = dict()
    out = execute(CMD_GET_DS_NODES.format(config=config).split())
    for line in out.splitlines():
        print('Line: ' + str(line))
        line = line.split()
        nodes[line[0].decode("utf-8")] = line[1].decode("utf-8")
    return nodes


CMD_NODE_CNI_BIN = 'oc exec -i {ng_ds_pod} -n node-gather --config={config} -- ls -l /host/opt/cni/bin'


def check_cni_bin_files(config, resulsts_dir, node, ng_ds_pod):
    cni_opt_cni_bin_file_name = os.path.join('.', os.path.join(
        os.path.join(resulsts_dir, NODES_DIR),
        os.path.join(node, OPT_CNI_BIN_FILE)
    ))
    with open(cni_opt_cni_bin_file_name) as cni_bin_file:
        cni_bin_file_content = cni_bin_file.read()

        cmd = CMD_NODE_CNI_BIN.format(config=config, ng_ds_pod=ng_ds_pod).split()

        cni_bin_output = execute(cmd).decode("utf-8")

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
        print("CNI CONFIG FILE: " + cni_config_file_name)

        cmd = CMD_NODE_LS_CNI_CONFIG.format(config=config, ng_ds_pod=ng_ds_pod, file_name=cni_config_file_name).split()
        cni_config_output = execute(cmd).decode("utf-8")
        with open(os.path.join(cni_config_dir_name, cni_config_file_name)) as cni_config_file:
            cni_config_file_content = cni_config_file.read()
            if cni_config_file_content == cni_config_output:
                print('CNI CONFIG {} MATCHES'.format(cni_config_file_name))
            else:
                print('ERROR: CNI CONFIG {} MATCHES'.format(cni_config_file_name))


def check_nodes(results_dir, config):
    create_node_gather_ds(config)

    nodes = get_node_gather_ds(config)
    print('NODES ' + str(nodes))

    for node in nodes.keys():
        check_cni_bin_files(config, results_dir, node, nodes[node])
        check_cni_config_files(config, results_dir, node, nodes[node])


def check_resource(config, results_dir, resource, path, is_list=True):
    CMD_GET_NETWORKADDONSCONFIG = 'oc get {resource} -o yaml --config={config}'
    out = execute(CMD_GET_NETWORKADDONSCONFIG.format(config=config, resource=resource).split())
    data = yaml.load(out)

    if is_list:
        data = data['items'][0]

    networkaddonsconfig_file_name = os.path.join(results_dir, path)
    with open(networkaddonsconfig_file_name) as networkaddonsconfig_file:
        networkaddonsconfig_file_content = networkaddonsconfig_file.read()
        networkaddonsconfig = yaml.load(networkaddonsconfig_file_content)

        if (data['spec'] == networkaddonsconfig['spec']):
            print('MATCH: ' + resource)
        else:
            print('NO MATCH: ' + resource)
            print(DeepDiff(data, networkaddonsconfig))

def check_list_of_resources(config, results_dir, list_name, resource_name, path):
    CMD = 'oc get {name} -o=custom-columns=NAME:.metadata.name --no-headers --config={config}'
    cmd = CMD.format(config=config, name=list_name).split()
    network_attachments = execute(cmd).decode("utf-8")
    for network_attachment in network_attachments.splitlines():
        check_resource(
            config,
            results_dir,
            resource_name.format(name=network_attachment),
            path.format(name=network_attachment),
            is_list=False
        )

##################

pre_run_check()

run_must_gather(IMAGE, config)

results_dir = get_results_dir()

check_nodes(results_dir, config)


check_resource(
    config,
    results_dir,
    'NetworkAddonsConfig',
    'cluster-scoped-resources/networkaddonsoperator.network.kubevirt.io/networkaddonsconfigs/cluster.yaml'
)


check_resource(
    config,
    results_dir,
    'ns/nmstate',
    'namespaces/nmstate/nmstate.yaml',
    is_list=False
)


check_list_of_resources(
    config,
    results_dir,
    'network-attachment-definitions',
    'network-attachment-definitions/{name}',
    'namespaces/default/k8s.cni.cncf.io/network-attachment-definitions/{name}.yaml'
)

check_list_of_resources(
    config,
    results_dir,
    'nodenetworkstates',
    'nodenetworkstate/{name}',
    'cluster-scoped-resources/nmstate.io/nodenetworkstates/{name}.yaml'
)

