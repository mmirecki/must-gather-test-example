
import re
import subprocess
import os
import yaml
from deepdiff import DeepDiff





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
        print('Results directory exists! Please run the script in an empty dir!')
        # exit()


def get_results_dir():
    results = _get_results_dirs()
    if len(results) != 1:
        print('Zero or multiple results dirs. Must be exactly 1.')
        exit()
    return results[0]



def run_must_gather(image, config):
    #cmd = 'export kubeconfig="{config}"'.format(config=config).split()
    #execute(cmd)

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
    out = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    #print("  IN:   " + str(' '.join(cmd)))
    stdout, stderr = out.communicate()
    if out.returncode != 0:
        return stdout, out.returncode
    #print('  RET:   ' + str(out.returncode))

    #print("  OUT:   " + str(stdout))
    #print("  ERR:   " + str(stderr))

    return stdout, 0


CMD_GET_DS_NODES = 'oc get pod -o=custom-columns=NODE:.spec.nodeName,NAME:.metadata.name --no-headers -n node-gather --config={config}'


def get_node_gather_ds(config):
    nodes = dict()
    out, return_code = execute(CMD_GET_DS_NODES.format(config=config).split())
    for line in out.splitlines():
        print('Line: ' + str(line))
        line = line.split()
        nodes[line[0].decode("utf-8")] = line[1].decode("utf-8")
    return nodes

def check_resource(config, results_dir, resource, path, checks, namespace=None):
    CMD_GET_RESOURCE = 'oc get {resource} -o yaml --config={config}'
    cmd = CMD_GET_RESOURCE
    if namespace:
        cmd = cmd + ' -n ' + namespace

    out, return_code = execute(cmd.format(config=config, resource=resource).split())
    if return_code != 0:
        raise Exception('oc Error geting resource: {resource}'.format(resource=resource))

    oc_data = yaml.load(out)

    resource_file_name = os.path.join(results_dir, path)
    with open(resource_file_name) as resource_file:
        file_content = yaml.load(resource_file.read())

        # Only matching the spec, but other items should be matched too (depending on resource)
        for check in checks:
            oc_part = oc_data
            file_part = file_content
            for part in check:
                try:
                    oc_part = oc_part[part]
                    file_part = file_part[part]
                except Exception as e:
                    print('DUPA: ' + str(e))
                except:
                    print('DUPA')
            if (oc_part == file_part):
                print('MATCH: ' + resource  + '     ' + str(namespace) + '   ' + str(check))
            else:
                print('NO MATCH: ' + resource + '     ' + str(namespace) + '   ' + str(check))
                print(DeepDiff(oc_part, file_part))

def check_list_of_resources(config, results_dir, resource_name, path, checks):
    CMD = 'oc get {name} -o=custom-columns=NAME:.metadata.name,NODE:.metadata.namespace --no-headers --config={config} --all-namespaces'
    NONE_NAMESPACE = '<none>'
    cmd = CMD.format(config=config, name=resource_name).split()
    out, return_code =  execute(cmd)
    resources = out.decode("utf-8")
    for resource in resources.splitlines():
        name, namespace = resource.split()
        #print('NAME/NS  :  {name} / {ns}'.format(name=name, ns=namespace))
        if namespace == NONE_NAMESPACE:
            namespace = None

        check_resource(
            config,
            results_dir,
            resource_name + '/' + name,
            path.format(name=name, namespace=namespace or 'default'),
            checks,
            namespace
        )
