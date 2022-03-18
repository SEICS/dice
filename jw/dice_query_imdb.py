import os
import subprocess, re
import json
import time
import json 
import numpy as np
from sklearn import datasets
from chow_liu import tree_structure, construct_tree, findSingleNodePath

def writeDice(query, bn_index, attr_range, dataset, fanout_attrs=[], name="no_join", gr="no"): # write single BN and corresponding query
    with open(f"imdb/relation_{bn_index}.json","r") as r:
        relation = json.load(r)
        relation = [tuple(lis) for lis in relation]

    dice = []
    parents, _, nodes = tree_structure(relation=relation)
    nodes_lst, nodes_name, allPath = construct_tree(itsParents=parents, nodes=nodes, dataset=dataset) # produce tree graph "BN_Chow_liu_tree.png"
    with open(f"imdb/pgmpyCPD_{bn_index}.json","r") as f:
        cpds = json.load(f)
    
    if gr == "yes":
        # Implementing graph reduction
        paths = findSingleNodePath(allPath=allPath)
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
        nodes_name = reduced
    
    # write dice file
    for n in nodes_name: 
        if not parents[n]:
            cpd = [str(cpd) for cpd in cpds[n][0]] # root node
            dice.append("let " + n + " = discrete(" + ",".join(cpd) + ") in\n" )
        else:
            cpd = []
            par = parents[n][0]
            for c in cpds[n]:
                cpd.append([str(cc) for cc in c])
                   
            leng = len(cpd)
            line = ["let " + n + " = "]
            
            for idx in range(len(cpd)):
                c = cpd[idx]
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

    # write for query
    attrs = list(query.keys())
    if fanout_attrs:
        l = "\nlet _ = observe ("
        lr = []
        for attr in attrs:
            vv = query[attr]
            if isinstance(vv, int):
                lr.append("(" + attr + " == int(" + str(attr_range[attr]) + "," + str(vv) + ")" + ")")
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
        for attr in attrs:
            vv = query[attr]
            if isinstance(vv, int):
                lr.append("(" + attr + " == int(" + str(attr_range[attr]) + "," + str(vv) + ")" + ")")
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
    with open(f"bayescard_{dataset}_{name}.dice", "w+") as f:
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

def evaluate_cardinality_imdb(dataset, gr):
    with open("imdb/imdb_true_cardinality.json","r") as j:
        true_cardinalities = json.load(j)

    with open("imdb/imdb_queries.json","r") as j2:
        ensemble_queries = json.load(j2)

    with open("imdb/job-light.sql", "rb") as f:
        real_query = f.readlines()

    latencies = []
    q_errors = []
    for i in range(len(ensemble_queries)):
        q = ensemble_queries[i]
        nrows = q[0]
        features = q[1:]
        try:
            print(f"predicting query no {i}: {real_query[i].strip()}")
            ensemble_prob = 1
            tic = time.time() # start to query and measure time
            for f in features:
                # iterating through each sub BN query in an ensemble query
                bn_index = f["bn_index"]
                fanout_attrs = f["expectation"]
                query = rename(f["query"])
                n_distincts = np.prod([1*num for val in list(f["n_distinct"].values()) for num in val])
                
                with open(f"imdb/attr_range_{bn_index}.json","r") as ar:
                    attr_range = json.load(ar)
                
                with open(f"imdb/imdb_fanouts_{bn_index}.json","r") as fo:
                    fanouts = json.load(fo)
                
                kk = list(query.keys()).copy()
                for aa in kk:
                    if query[aa] == []:
                        del query[aa]
                
                if fanout_attrs:
                    fanout_attrs = [fa.replace(".","_") for fa in fanout_attrs]
                    name = "probsq"
                    writeDice(query=query, bn_index=bn_index, attr_range=attr_range, dataset=dataset, name=name, gr=gr)
                    output = subprocess.getoutput(f"~/Desktop/dice/Dice.native bayescard_{dataset}_{name}.dice").split("\n")[1]
                    line = re.findall("[0-9\.]+", output)
                    probsQ = float(line[-1].strip()) * n_distincts

                    name = "probsqf"
                    writeDice(query=query, bn_index=bn_index, attr_range=attr_range, dataset=dataset, name=name, fanout_attrs=fanout_attrs, gr=gr)
                    output2 = subprocess.getoutput(f"~/Desktop/dice/Dice.native bayescard_{dataset}_{name}.dice").split("\n")[1:-2]
                    for_reshape = tuple([int(elem)+1 for elem in re.findall("[0-9\.]+", output2[-1].split("\t")[0])])
                    probsQF = np.array([float(o.split("\t")[1]) for o in output2]).reshape(for_reshape)
                    probsQF = probsQF / np.sum(probsQF)
                    fanout_attrs_shape = tuple([len(fanouts[i]) for i in fanout_attrs])
                    probsQF = probsQF.reshape(fanout_attrs_shape)
                    prob = np.sum(probsQF * get_fanout_values(fanout_attrs=fanout_attrs, fanouts=fanouts)) * probsQ
                else:
                    writeDice(query=query, bn_index=bn_index, attr_range=attr_range, dataset=dataset, gr=gr)
                    output = subprocess.getoutput(f"~/Desktop/dice/Dice.native bayescard_{dataset}_no_join.dice").split("\n")[1]
                    line = re.findall("[0-9\.]+", output)
                    prob = float(line[-1].strip()) * n_distincts

                if f["inverse"]:
                    ensemble_prob *= (1/prob)
                else:
                    ensemble_prob *= prob
        except:
            # this query itself is invalid or it is not recognizable by the learnt BN
            continue

        pred = nrows * ensemble_prob
        latencies.append(time.time() - tic)
        if pred is None or pred <= 1:
            pred = 1
        error = max(pred / true_cardinalities[i], true_cardinalities[i] / pred)
        print(f"nrows {nrows}, true cardinality {true_cardinalities[i]}, predicted {pred} with q-error {error} \n")
        q_errors.append(error)
    print("=====================================================================================")
    for i in [50, 90, 95, 99, 100]:
        percentile = np.percentile(q_errors, i)
        print(f"q-error {i}% percentile is {percentile}")
    print(f"average latency is {np.mean(latencies)*1000} ms")
    print(f"total {len(q_errors)} queries evaluated.")

    if gr == "yes":
        gr = "gr"
    elif gr == "no":
        gr = "no_gr"
    else:
        print("Incorrect input. Please input yes or no only.")
        return 1

    if not os.path.exists(f"{dataset}/{gr}"):
        os.makedirs(f"{dataset}/{gr}")

    with open(f"{dataset}/{gr}/q_errors.json","w+") as qe:
        json.dump(q_errors, qe, indent=2)
    
    with open(f"{dataset}/{gr}/latencies.json", "w+") as lat:
        json.dump(latencies, lat, indent=2)
