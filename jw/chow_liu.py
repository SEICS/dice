from collections import defaultdict
from anytree import Node, PreOrderIter
from anytree.exporter import DotExporter

def tree_structure(relation):
    nodes = []
    if relation:
        itsParents = defaultdict() # dictionary keys are children, values store a list of parents for each child node
        itsChildren = defaultdict() # dictionary keys are parents, values store a list of children for each parent node
        
        for parent, child in relation:
            if parent not in itsChildren.keys():
                itsChildren[parent] = [child]
            else:
                itsChildren[parent].append(child)
                
            if child not in itsParents.keys():
                itsParents[child] = [parent]
            else:
                itsParents[child].append(parent)

            nodes.append(parent)
            nodes.append(child)
    else:
        print("Empty list for dice automation")
        
    nodes = set(nodes)
    p_ = nodes - set(itsParents.keys())
    for p in p_:
        itsParents[p] = []
    
    c_ = nodes - set(itsChildren.keys())
    for c in c_:
        itsChildren[c] = []
 
    return itsParents, itsChildren, list(nodes)

def construct_tree(itsParents, nodes, dataset):
    nodes_list = {}
    notVisited = nodes.copy()
    while notVisited:
        for n in notVisited:
            if itsParents[n] == []:
                root = Node(n,parent=None) # root
                nodes_list[n] = root
                notVisited.remove(n)
            else:
                p = itsParents[n][0] # this node's parent
                if p in nodes_list.keys():
                    node = Node(n,parent=nodes_list[p])
                    nodes_list[n] = node
                    notVisited.remove(n)
                else:
                    continue

    # Generate the corresponding Bayesian network structure
    DotExporter(root).to_picture(f"{dataset}/BN_chow_liu_tree.pdf")
    
    # Get all possible path starting from root
    whole_tree = list(PreOrderIter(root, filter_=lambda node: node.is_leaf))
    all_path = [str(i)[7:-2].split(i.separator) for i in whole_tree]
    
    return nodes_list, [node.name for node in PreOrderIter(root)], all_path

def findSingleNodePath(allPath): 
    # find the path to each node starting from root, 
    # where dictionary key is the node, and its value 
    # is the path to it(previous visited node for this path)
    nodesPath = {}  
    paths = [path[:i] for path in allPath for i in range(1, len(path)+1)]

    for path in paths:
        node = path[-1]
        if node not in nodesPath.keys():
            if len(path) == 1:
                nodesPath[node] = []
            else:
                nodesPath[node] = path[:-1]
        else:
            continue
    return nodesPath