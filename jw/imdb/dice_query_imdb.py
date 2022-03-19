import subprocess, re
import json
import itertools
from time import perf_counter
import time
import pandas as pd
import json 
from collections import defaultdict
from anytree import Node, PreOrderIter
from anytree.exporter import DotExporter
import numpy as np

# census
# relation = [('iLang1', 'dAncstry1'), ('dAncstry1', 'dAncstry2'), ('iLooking', 'iAvail'), ('iRPOB', 'iCitizen'), ('dIndustry', 'iClass'), ('dTravtime', 'dDepart'), ('iDisabl2', 'iDisabl1'), ('iYearwrk', 'iDisabl2'), ('iLang1', 'iEnglish'), ('iRvetserv', 'iFeb55'), ('iRelat1', 'iFertil'), ('dAncstry1', 'dHispanic'), ('iWork89', 'dHour89'), ('iRlabor', 'dHours'), ('iRPOB', 'iImmigr'), ('dRearning', 'dIncome1'), ('iClass', 'dIncome2'), ('dOccup', 'dIncome3'), ('dRpincome', 'dIncome4'), ('dAge', 'dIncome5'), ('dRpincome', 'dIncome6'), ('dAge', 'dIncome7'), ('dRpincome', 'dIncome8'), ('dOccup', 'dIndustry'), ('iRvetserv', 'iKorean'), ('iYearsch', 'iLang1'), ('iRlabor', 'iLooking'), ('iRspouse', 'iMarital'), ('iRvetserv', 'iMay75880'), ('dHours', 'iMeans'), ('iRlabor', 'iMilitary'), ('iLang1', 'iMobility'), ('iDisabl1', 'iMobillim'), ('iYearwrk', 'dOccup'), ('iRvetserv', 'iOthrserv'), ('iMobillim', 'iPerscare'), ('dAncstry1', 'dPOB'), ('iRelat1', 'dPoverty'), ('iRPOB', 'dPwgt1'), ('iFertil', 'iRagechld'), ('dHour89', 'dRearning'), ('iRspouse', 'iRelat1'), ('iRelat1', 'iRelat2'), ('iRrelchld', 'iRemplpar'), ('iMeans', 'iRiders'), ('iYearwrk', 'iRlabor'), ('iRemplpar', 'iRownchld'), ('dRearning', 'dRpincome'), ('dPOB', 'iRPOB'), ('dAge', 'iRrelchld'), ('dAge', 'iRspouse'), ('iMilitary', 'iRvetserv'), ('dAge', 'iSchool'), ('iRvetserv', 'iSept80'), ('iRagechld', 'iSex'), ('iRelat1', 'iSubfam1'), ('iSubfam1', 'iSubfam2'), ('iRlabor', 'iTmpabsnt'), ('iMeans', 'dTravtime'), ('iRvetserv', 'iVietnam'), ('dRearning', 'dWeek89'), ('iYearwrk', 'iWork89'), ('iRlabor', 'iWorklwk'), ('iRvetserv', 'iWWII'), ('dAge', 'iYearsch'), ('dAge', 'iYearwrk'), ('iRvetserv', 'dYrsserv')]
# dmv 
# relation = [('Record_Type', 'Registration_Class'), ('County', 'State'), ('Registration_Class', 'County'), ('Body_Type', 'Model_Year'), ('Registration_Class', 'Body_Type'), ('Body_Type', 'Fuel_Type'), ('County', 'Scofflaw_Indicator'), ('Body_Type', 'Suspension_Indicator'), ('Registration_Class', 'Revocation_Indicator')]

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
 
def writeDice(query, bn_index): #  write single BN and corresponding query
    with open(f"imdb/relation_{bn_index}.json","r") as r:
        relation = json.load(r)
        relation = [tuple(lis) for lis in relation]
    r.close()
    
    # print("relation: ", relation)
    dice = []
    parents, children, nodes = tree_structure(relation)
    nodes_lis, nodes_name, allPath = construct_tree(parents, children, nodes) # produce tree graph "BN_Chow_liu_tree.png"
    
    with open(f"imdb/pgmpyCPD_{bn_index}.json","r") as f:
        cpds = json.load(f)
    
    # print("cpds: ", cpds.keys())
    # print("nodes_name: ", nodes_name)
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

    with open("bayescard_imdb.dice", "w+") as f:
        f.write("".join(dice))

if __name__ == "__main__":
    with open("imdb/imdb_true_cardinality.json","r") as j:
        true_cardinalities = json.load(j)

    with open("imdb/imdb_queries.json","r") as j2:
        ensemble_queries = json.load(j2)

    with open("imdb/job-light.sql", "rb") as f:
        real_query = f.readlines()
        
    latencies = []
    q_errors = []
    for i, q in enumerate(ensemble_queries[:1]):
        # print("q: ", q)
        nrows = q[0]
        features = q[1:]
        ensemble_prob = 1
        try:
            print("predicting cardinality...")
            tic = time.time() # start to query and measure time
            for f in features:
                # iterating through each sub BN query in an ensemble query
                bn_index = f["bn_index"]
                query = f["query"]
                with open(f"attr_range_{bn_index}.json","r") as ar:
                    attr_range = json.load(ar)
                
                print("bn_index: ", bn_index)
                print("query: ", query)
                
                kk = list(query.keys()).copy()
                for aa in kk:
                    if query[aa] == []:
                        del query[aa]
        
                writeDice(query=query, bn_index=bn_index)

                output = subprocess.getoutput("~/Desktop/dice/Dice.native bayescard_imdb.dice").split("\n")[1]
                line = re.findall("[0-9\.]+", output)
                prob = float(line[-1].strip())
                print("prob: ", prob)

                ensemble_prob *= prob

        except:
            # this query itself is invalid or it is not recognizable by the learnt BN
            continue

        pred = ensemble_prob * nrows # cardinality predict
        latencies.append(time.time() - tic)
        cardinality_true = true_cardinalities[i]

        # print(f"cardinality predict: {cardinality_predict} and cardinality true: {cardinality_true}")
        if pred is None or pred <= 1:
            pred = 1
        error = max(pred / true_cardinalities[i], true_cardinalities[i] / pred)
        print("pred: ",pred)
        print("error: ", error)
        print(f"predicting query no {i}: {real_query[i]} \n")
        print(f"true cardinality {true_cardinalities[i]}, predicted {pred} with q-error {error}")
        q_errors.append(error)
    print("=====================================================================================")
    print("q_errors: ",q_errors)
    for i in [50, 90, 95, 99, 100]:
        percentile = np.percentile(q_errors, i)
        print(f"q-error {i}% percentile is {percentile}")
    print(f"average latency is {np.mean(latencies)*1000} ms")
