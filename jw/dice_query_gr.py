import subprocess, re
import json
import itertools
from time import perf_counter
import pandas as pd
import json 
from collections import defaultdict
from anytree import Node, PreOrderIter
from anytree.exporter import DotExporter
import numpy as np

# census
# relation = [('iLang1', 'dAncstry1'), ('dAncstry1', 'dAncstry2'), ('iLooking', 'iAvail'), ('iRPOB', 'iCitizen'), ('dIndustry', 'iClass'), ('dTravtime', 'dDepart'), ('iDisabl2', 'iDisabl1'), ('iYearwrk', 'iDisabl2'), ('iLang1', 'iEnglish'), ('iRvetserv', 'iFeb55'), ('iRelat1', 'iFertil'), ('dAncstry1', 'dHispanic'), ('iWork89', 'dHour89'), ('iRlabor', 'dHours'), ('iRPOB', 'iImmigr'), ('dRearning', 'dIncome1'), ('iClass', 'dIncome2'), ('dOccup', 'dIncome3'), ('dRpincome', 'dIncome4'), ('dAge', 'dIncome5'), ('dRpincome', 'dIncome6'), ('dAge', 'dIncome7'), ('dRpincome', 'dIncome8'), ('dOccup', 'dIndustry'), ('iRvetserv', 'iKorean'), ('iYearsch', 'iLang1'), ('iRlabor', 'iLooking'), ('iRspouse', 'iMarital'), ('iRvetserv', 'iMay75880'), ('dHours', 'iMeans'), ('iRlabor', 'iMilitary'), ('iLang1', 'iMobility'), ('iDisabl1', 'iMobillim'), ('iYearwrk', 'dOccup'), ('iRvetserv', 'iOthrserv'), ('iMobillim', 'iPerscare'), ('dAncstry1', 'dPOB'), ('iRelat1', 'dPoverty'), ('iRPOB', 'dPwgt1'), ('iFertil', 'iRagechld'), ('dHour89', 'dRearning'), ('iRspouse', 'iRelat1'), ('iRelat1', 'iRelat2'), ('iRrelchld', 'iRemplpar'), ('iMeans', 'iRiders'), ('iYearwrk', 'iRlabor'), ('iRemplpar', 'iRownchld'), ('dRearning', 'dRpincome'), ('dPOB', 'iRPOB'), ('dAge', 'iRrelchld'), ('dAge', 'iRspouse'), ('iMilitary', 'iRvetserv'), ('dAge', 'iSchool'), ('iRvetserv', 'iSept80'), ('iRagechld', 'iSex'), ('iRelat1', 'iSubfam1'), ('iSubfam1', 'iSubfam2'), ('iRlabor', 'iTmpabsnt'), ('iMeans', 'dTravtime'), ('iRvetserv', 'iVietnam'), ('dRearning', 'dWeek89'), ('iYearwrk', 'iWork89'), ('iRlabor', 'iWorklwk'), ('iRvetserv', 'iWWII'), ('dAge', 'iYearsch'), ('dAge', 'iYearwrk'), ('iRvetserv', 'dYrsserv')]
# dmv 
relation = [('Record_Type', 'Registration_Class'), ('County', 'State'), ('Registration_Class', 'County'), ('Body_Type', 'Model_Year'), ('Registration_Class', 'Body_Type'), ('Body_Type', 'Fuel_Type'), ('County', 'Scofflaw_Indicator'), ('Body_Type', 'Suspension_Indicator'), ('Registration_Class', 'Revocation_Indicator')]


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
        print("Empty list for Csharp automation")
        
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
    DotExporter(root).to_picture("BN_chow_liu_tree.pdf")
    
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

def writeDice(query):
    global relation
    dice = []
    parents, children, nodes = tree_structure(relation)
    nodes_lst, nodes_name, allPath = construct_tree(parents, children, nodes) # produce tree graph "BN_Chow_liu_tree.png"
    paths = findSingleNodePath(allPath)

    # Implementing graph reduction
    attributes = list(query.keys())
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

    # print("subtree: ",subtree)
    with open("dmv/pgmpyCPD.json","r") as f:
        cpds = json.load(f)
        
    # write dice file
    # for n in nodes_name: 
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
        
    # write for query
    attrs = list(query.keys())
    l = "\nlet q = if ("
    lr = []
    for attr in attrs:
        vv = query[attr]
        if len(vv) == 1:
            lr.append("(" + attr + " == int(" + str(attr_range[attr]) + "," + str(vv[0]) + ")" + ")")
        else:
            lrr = []
            for v in vv:
                lrr.append("(" + attr + " == int(" + str(attr_range[attr]) + "," + str(v) + ")" + ")")
            lr.append("(" + "||".join(lrr) + ")")
    l += "&&".join(lr)
    l += ") then (discrete(1.0, 0.0)) else (discrete(0.0, 1.0)) in\nq"
    dice.append(l)
               
    with open("bayescard_gr.dice", "w+") as f:
        f.write("".join(dice))

if __name__ == "__main__":
    with open("dmv/true_cardinality.json","r") as j:
        true_cardinalities = json.load(j)

    with open("dmv/queries.json","r") as j2:
        queries = json.load(j2)

    with open("dmv/attr_range.json","r") as j3:
        attr_range = json.load(j3)

    latencies = []
    q_errors = []
    for i in range(len(queries)): 
        # len(queries)
        query = queries[i]
        
        for q in query.keys():
            attr = query[q]
            limit = attr_range[q]
            for num in attr:
                if num < 0 or num >= limit:
                    attr.remove(num)
        
        for q in list(query.keys()):
            attr = query[q]
            limit = attr_range[q]
            if len(attr) == limit:
                query.pop(q)

        kk = list(query.keys()).copy()
        for q in kk:
            if query[q] == []:
                print("q: ", q)
                print("query: ", query)
                del query[q]

        print(f"Predicting cardinality for query {i}: {query}")
        vals = list(query.values())
        writeDice(query)

        card_start_t = perf_counter()
        output = subprocess.getoutput("~/Desktop/dice/Dice.native bayescard_gr.dice").split("\n")[1]
        line = re.findall("[0-9\.]+", output)
        prob = float(line[-1].strip())
        # census total rows = 2458285, dmv total rows = 11575483
        cardinality_predict = prob * 11575483
        card_end_t = perf_counter()

        latency_ms = (card_end_t-card_start_t) * 1000
        cardinality_true = true_cardinalities[i]

        # print(f"cardinality predict: {cardinality_predict} and cardinality true: {cardinality_true}")
        if cardinality_predict == 0 and cardinality_true == 0:
            q_error = 1.0
        elif np.isnan(cardinality_predict) or cardinality_predict == 0:
            cardinality_predict = 1
            q_error = max(cardinality_predict / cardinality_true, cardinality_true / cardinality_predict)
        elif cardinality_true == 0:
            cardinality_true = 1
            q_error = max(cardinality_predict / cardinality_true, cardinality_true / cardinality_predict)
        else:
            q_error = max(cardinality_predict / cardinality_true, cardinality_true / cardinality_predict)
        print(f"latency: {latency_ms} and error: {q_error}")

        latencies.append(latency_ms)
        q_errors.append(q_error)

    print("=====================================================================================")
    for j in [50, 90, 95, 99, 100]:
        print(f"q-error {j}% percentile is {np.percentile(q_errors, j)}") # np.percentile uses same algorithm as percentile formula in Excel
    print(f"average latency is {np.mean(latencies)} ms")
    
    with open("dice_q_errors_GR.json","w+") as qq:
        json.dump(q_errors, qq, indent=2)

    with open("dice_latencies_GR.json","w+") as t:
        json.dump(latencies, t, indent=2)