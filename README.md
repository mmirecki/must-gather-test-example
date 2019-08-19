# Collecting node data

Export kubeconfig before running!

Data can be collected from nodes using the node-gather daemonset.
For this two files are needed:
node-gather-crd.yaml
node-gather-ds.yaml
These can be generated in the must-gather repo using:
    make manifests



Note: the data is collected the same way must-gather does it - the node-gather image.
This is not a good solution. If there are problems with node-gather,
we might not be able to detect it.
But I can not think of any better way right now.

