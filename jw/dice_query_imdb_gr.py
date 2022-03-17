import subprocess, re
import json
import itertools
from time import perf_counter
import time
from xml.sax.xmlreader import AttributesImpl
import pandas as pd
import json 
from collections import defaultdict
from anytree import Node, PreOrderIter
from anytree.exporter import DotExporter
import numpy as np

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

def construct_tree(itsParents, itsChildren, nodes):
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
    DotExporter(root).to_picture("imdb/BN_chow_liu_tree.pdf")
    
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

def writeDice(query, bn_index, attr_range, fanout_attrs=[], name="no_join"): #  write single BN and corresponding query
    with open(f"imdb/relation_{bn_index}.json","r") as r:
        relation = json.load(r)
        relation = [tuple(lis) for lis in relation]
    r.close()
    
    # print("relation: ", relation)
    dice = []
    parents, children, nodes = tree_structure(relation)
    nodes_lst, nodes_name, allPath = construct_tree(parents, children, nodes) # produce tree graph "BN_Chow_liu_tree.png"
    paths = findSingleNodePath(allPath)

    with open(f"imdb/pgmpyCPD_{bn_index}.json","r") as f:
        cpds = json.load(f)
    
    # print("cpds: ", cpds.keys())
    # print("nodes_name: ", nodes_name)

    # Implementing graph reduction
    attributes = list(query.keys()) + fanout_attrs
    bn_dict = {a:paths[a] for a in attributes if a in paths}
    subtree = []
    for p in bn_dict.values():
        subtree += p
    subtree = set(subtree + attributes)

    depth = dict()
    for n in subtree:
        depth[n] = nodes_lst[n].depth

    depth = dict(sorted(depth.items(), key = lambda x:x[1]))
    subtree = depth.keys()

    reduced = []
    for n in nodes_name:
        if n in subtree:
            reduced.append(n)

    # write dice file
    for n in reduced: 
        if not parents[n]:
            cpd = [str(cpd) for cpd in cpds[n][0]] # root node
            dice.append("let " + n + " = discrete(" + ",".join(cpd) + ") in\n" )
        else:
            cpd = []
            par = parents[n][0]
            for c in cpds[n]:
                cpd.append([str(cc) for cc in c])
                   
            leng = len(cpd)
            # print("leng: ",leng)
            line = ["let " + n + " = "]
            
            for idx in range(len(cpd)):
                c = cpd[idx]
                # print(n + "[" + str(idx) + "]" + ": " + ",".join(c))
                
                if idx == len(cpd)-2: # last two
                    if len(cpd) == 2:
                        line.append("if (" + par + " == int(" + str(leng) + "," + str(idx) + ")) then (discrete(" + ",".join(c) + ")) else (discrete(" + ",". join(cpd[-1]) + "))")
                    else:
                        line.append("(if (" + par + " == int(" + str(leng) + "," + str(idx) + ")) then (discrete(" + ",".join(c) + ")) else (discrete(" + ",". join(cpd[-1]) + "))")
                    break
                elif idx == 0: # start
                    line.append("if (" + par + " == int(" + str(leng) + "," + str(idx) + ")) then (discrete(" + ",".join(c) + ")) else ")
                else:
                    line.append("(if (" + par + " == int(" + str(leng) + "," + str(idx) + ")) then (discrete(" + ",".join(c) + ")) else ")
                
            line.append(")" * (len(cpd)-2) + " in\n")
            
            dice.append("".join(line))  

    # print("dice: ", dice[:1])
    # write for query
    attrs = list(query.keys())

    # print("fanout_attrs: ", fanout_attrs)
    if fanout_attrs:
        # ranges = [attr_range[attrs] for attrs in fanout_attrs]
        # bigger = fanout_attrs[ranges.index((max(ranges)))]
        l = "\nlet _ = observe ("
        lr = []
        # print("attrs: ", attrs)
        for attr in attrs:
            vv = query[attr]
            if isinstance(vv, int):
                lr.append("(" + attr + " == int(" + str(attr_range[attr]) + "," + str(vv) + ")" + ")")
                # print("lr: ", lr)
            elif len(vv) == 1:
                lr.append("(" + attr + " == int(" + str(attr_range[attr]) + "," + str(vv[0]) + ")" + ")")
            else:
                lrr = []
                for v in vv:
                    lrr.append("(" + attr + " == int(" + str(attr_range[attr]) + "," + str(v) + ")" + ")")
                lr.append("(" + "||".join(lrr) + ")")

        l += "&&".join(lr)
        l += ") in\n"
        dice.append(l)

        l = "\n"
        if len(fanout_attrs) == 1:
            l += fanout_attrs[0]
        elif len(fanout_attrs) == 2:
            l += "(" + fanout_attrs[0] + ",(" + fanout_attrs[1] + "))"
        else:
            for i in range(len(fanout_attrs)-2):
                l += "(" + fanout_attrs[i] + ","
            l += "(" + fanout_attrs[-2] + "," + fanout_attrs[-1] + ")" * (len(fanout_attrs)-1)
    else:
        l = "\nlet q = if ("
        lr = []
        # print("attrs: ", attrs)
        for attr in attrs:
            vv = query[attr]
            if isinstance(vv, int):
                lr.append("(" + attr + " == int(" + str(attr_range[attr]) + "," + str(vv) + ")" + ")")
                # print("lr: ", lr)
            elif len(vv) == 1:
                lr.append("(" + attr + " == int(" + str(attr_range[attr]) + "," + str(vv[0]) + ")" + ")")
            else:
                lrr = []
                for v in vv:
                    lrr.append("(" + attr + " == int(" + str(attr_range[attr]) + "," + str(v) + ")" + ")")
                lr.append("(" + "||".join(lrr) + ")")

        l += "&&".join(lr)
        l += ") then (discrete(1.0, 0.0)) else (discrete(0.0, 1.0)) in\nq"
    
    dice.append(l)

    
    with open(f"bayescard_imdb_{name}.dice", "w+") as f:
        f.write("".join(dice))

def rename(dicts):
    # rename dictionary keys
    kk = list(dicts.keys())
    for k in kk:
        new_key = k.replace(".","_")
        dicts[new_key] = dicts.pop(k)
    return dicts

def get_fanout_values(fanout_attrs, fanouts):
    if len(fanout_attrs) == 1:
        return fanouts[fanout_attrs[0]]
    else:
        fanout_attrs_shape = tuple([len(fanouts[i]) for i in fanout_attrs])
        res = None
        for i in fanout_attrs:
            if res is None:
                res = fanouts[i]
            else:
                res = np.outer(res, fanouts[i]).reshape(-1)
        return res.reshape(fanout_attrs_shape)

if __name__ == "__main__":
    with open("imdb/imdb_true_cardinality.json","r") as j:
        true_cardinalities = json.load(j)

    with open("imdb/imdb_queries.json","r") as j2:
        ensemble_queries = json.load(j2)

    with open("imdb/job-light.sql", "rb") as f:
        real_query = f.readlines()
    
    # print("true cardinalities: ", true_cardinalities[:1])
    # print("ensemble_queries: ", ensemble_queries[:1])
    # print("real_query: ", real_query[:1])
    latencies = []
    q_errors = []
    for i in range(len(ensemble_queries)):
        # len(ensemble_queries)):
        q = ensemble_queries[i]
        # print("q: ", q)
        nrows = q[0]
        features = q[1:]
        try:
            print(f"predicting query no {i}: {real_query[i].strip()}")
            ensemble_prob = 1
            # print("predicting cardinality...")
            tic = time.time() # start to query and measure time
            for f in features:
                # print('f["query"]: ', f["query"])
                # iterating through each sub BN query in an ensemble query
                bn_index = f["bn_index"]
                fanout_attrs = f["expectation"]
                query = rename(f["query"])
                # print("n_distincts: ", np.prod([1*num for val in list(f["n_distinct"].values()) for num in val]))
                n_distincts = np.prod([1*num for val in list(f["n_distinct"].values()) for num in val])
                # print("n_distincts: ", n_distincts)

                with open(f"imdb/attr_range_{bn_index}.json","r") as ar:
                    attr_range = json.load(ar)
                
                with open(f"imdb/imdb_fanouts_{bn_index}.json","r") as fo:
                    fanouts = json.load(fo)

                # print("bn_index: ", bn_index)
                # print("query: ", query)
                
                kk = list(query.keys()).copy()
                for aa in kk:
                    if query[aa] == []:
                        del query[aa]
                
                # print("fanout_attrs: ", fanout_attrs)
                if fanout_attrs:
                    fanout_attrs = [fa.replace(".","_") for fa in fanout_attrs]
                    name = "probsq"
                    writeDice(query=query, bn_index=bn_index, attr_range=attr_range, name=name)
                    output = subprocess.getoutput(f"~/Desktop/dice/Dice.native bayescard_imdb_{name}.dice").split("\n")[1]
                    line = re.findall("[0-9\.]+", output)
                    probsQ = float(line[-1].strip()) * n_distincts
                    # print("probsQ: ", probsQ)

                    name = "probsqf"
                    writeDice(query=query, bn_index=bn_index, attr_range=attr_range, name=name, fanout_attrs=fanout_attrs)
                    output2 = subprocess.getoutput(f"~/Desktop/dice/Dice.native bayescard_imdb_{name}.dice").split("\n")[1:-2]
                    # print("output2: ", output2)
                    for_reshape = tuple([int(elem)+1 for elem in re.findall("[0-9\.]+", output2[-1].split("\t")[0])])
                    # print("for_reshape: ", for_reshape)
                    probsQF = np.array([float(o.split("\t")[1]) for o in output2]).reshape(for_reshape)
                    # print("probsQF: ", probsQF)
                    # print("probsQF shape: ", probsQF.shape)
                    # print("np.sum(probsQF)",np.sum(probsQF))
                    probsQF = probsQF / np.sum(probsQF)
                    fanout_attrs_shape = tuple([len(fanouts[i]) for i in fanout_attrs])
                    # print("fanout_attrs_shape: ", fanout_attrs_shape)
                    probsQF = probsQF.reshape(fanout_attrs_shape)
                    # print("probsQF shape: ", probsQF.shape)

                    # print("get_fanout_values(fanout_attrs=fanout_attrs, fanouts=fanouts): ", get_fanout_values(fanout_attrs=fanout_attrs, fanouts=fanouts))
                    # print("np.sum(probsQF * get_fanout_values(fanout_attrs=fanout_attrs, fanouts=fanouts)): ", np.sum(probsQF * get_fanout_values(fanout_attrs=fanout_attrs, fanouts=fanouts)))
                    # print("get_fanout_values(fanout_attrs): ", probsQF * get_fanout_values(fanout_attrs=fanout_attrs, fanouts=fanouts))
                    prob = np.sum(probsQF * get_fanout_values(fanout_attrs=fanout_attrs, fanouts=fanouts)) * probsQ
                    # print("exp: ", prob) 
                else:
                    writeDice(query=query, bn_index=bn_index, attr_range=attr_range)
                    output = subprocess.getoutput(f"~/Desktop/dice/Dice.native bayescard_imdb_no_join.dice").split("\n")[1]
                    line = re.findall("[0-9\.]+", output)
                    prob = float(line[-1].strip()) * n_distincts
                    # print("prob: ", prob)

                if f["inverse"]:
                    ensemble_prob *= (1/prob)
                else:
                    ensemble_prob *= prob

        except:
            # this query itself is invalid or it is not recognizable by the learnt BN
            continue

        # print("ensemble_prob: ", ensemble_prob)
        pred = nrows * ensemble_prob
        # print("pred: ", pred)
        latencies.append(time.time() - tic)
        cardinality_true = true_cardinalities[i]

        # print(f"cardinality predict: {cardinality_predict} and cardinality true: {cardinality_true}")
        if pred is None or pred <= 1:
            pred = 1
        error = max(pred / true_cardinalities[i], true_cardinalities[i] / pred)
        # print("error: ", error)
        print(f"nrows {nrows}, true cardinality {true_cardinalities[i]}, predicted {pred} with q-error {error} \n")
        q_errors.append(error)
    print("=====================================================================================")
    # print("q_errors: ",q_errors)
    for i in [50, 90, 95, 99, 100]:
        percentile = np.percentile(q_errors, i)
        print(f"q-error {i}% percentile is {percentile}")
    print(f"average latency is {np.mean(latencies)*1000} ms")
    print(f"total {len(q_errors)} queries evaluated.")

    with open("imdb_gr/imdb_q_errors_gr.json","w+") as qe:
        json.dump(q_errors, qe, indent=2)
    
    with open("imdb_gr/imdb_latencies_gr.json", "w+") as lat:
        json.dump(latencies, lat, indent=2)
