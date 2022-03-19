import math
import os
import subprocess, re
import json
from time import perf_counter
import numpy as np
from chow_liu import tree_structure, construct_tree, findSingleNodePath

def writeDice(query, attr_range, dataset, relation, gr="no", bitwidth="no"):
    dice = []
    parents, _, nodes = tree_structure(relation)
    nodes_lst, nodes_name, allPath = construct_tree(itsParents=parents, nodes=nodes, dataset=dataset) # produce tree graph "BN_Chow_liu_tree.png"
    paths = findSingleNodePath(allPath=allPath)

    if gr == "yes":
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

        nodes_name = reduced

    with open(f"{dataset}/pgmpyCPD.json","r") as f:
        cpds = json.load(f)
        
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
            
            if bitwidth=="yes":
                leng = len(cpd).bit_length()
            else:
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
               
    with open(f"bayescard_{dataset}.dice", "w+") as f:
        f.write("".join(dice))

def evaluate_single_table(dataset, gr, bitwidth):
    if dataset == "census":
        relation = [('iLang1', 'dAncstry1'), ('dAncstry1', 'dAncstry2'), ('iLooking', 'iAvail'), ('iRPOB', 'iCitizen'), ('dIndustry', 'iClass'), ('dTravtime', 'dDepart'), ('iDisabl2', 'iDisabl1'), ('iYearwrk', 'iDisabl2'), ('iLang1', 'iEnglish'), ('iRvetserv', 'iFeb55'), ('iRelat1', 'iFertil'), ('dAncstry1', 'dHispanic'), ('iWork89', 'dHour89'), ('iRlabor', 'dHours'), ('iRPOB', 'iImmigr'), ('dRearning', 'dIncome1'), ('iClass', 'dIncome2'), ('dOccup', 'dIncome3'), ('dRpincome', 'dIncome4'), ('dAge', 'dIncome5'), ('dRpincome', 'dIncome6'), ('dAge', 'dIncome7'), ('dRpincome', 'dIncome8'), ('dOccup', 'dIndustry'), ('iRvetserv', 'iKorean'), ('iYearsch', 'iLang1'), ('iRlabor', 'iLooking'), ('iRspouse', 'iMarital'), ('iRvetserv', 'iMay75880'), ('dHours', 'iMeans'), ('iRlabor', 'iMilitary'), ('iLang1', 'iMobility'), ('iDisabl1', 'iMobillim'), ('iYearwrk', 'dOccup'), ('iRvetserv', 'iOthrserv'), ('iMobillim', 'iPerscare'), ('dAncstry1', 'dPOB'), ('iRelat1', 'dPoverty'), ('iRPOB', 'dPwgt1'), ('iFertil', 'iRagechld'), ('dHour89', 'dRearning'), ('iRspouse', 'iRelat1'), ('iRelat1', 'iRelat2'), ('iRrelchld', 'iRemplpar'), ('iMeans', 'iRiders'), ('iYearwrk', 'iRlabor'), ('iRemplpar', 'iRownchld'), ('dRearning', 'dRpincome'), ('dPOB', 'iRPOB'), ('dAge', 'iRrelchld'), ('dAge', 'iRspouse'), ('iMilitary', 'iRvetserv'), ('dAge', 'iSchool'), ('iRvetserv', 'iSept80'), ('iRagechld', 'iSex'), ('iRelat1', 'iSubfam1'), ('iSubfam1', 'iSubfam2'), ('iRlabor', 'iTmpabsnt'), ('iMeans', 'dTravtime'), ('iRvetserv', 'iVietnam'), ('dRearning', 'dWeek89'), ('iYearwrk', 'iWork89'), ('iRlabor', 'iWorklwk'), ('iRvetserv', 'iWWII'), ('dAge', 'iYearsch'), ('dAge', 'iYearwrk'), ('iRvetserv', 'dYrsserv')]
    elif dataset == "dmv":
        relation = [('Record_Type', 'Registration_Class'), ('County', 'State'), ('Registration_Class', 'County'), ('Body_Type', 'Model_Year'), ('Registration_Class', 'Body_Type'), ('Body_Type', 'Fuel_Type'), ('County', 'Scofflaw_Indicator'), ('Body_Type', 'Suspension_Indicator'), ('Registration_Class', 'Revocation_Indicator')]
    else:
        print("Other datasets for single table query evaluation are not supported yet.")
        return 1

    with open(f"{dataset}/true_cardinality.json","r") as j:
        true_cardinalities = json.load(j)

    with open(f"{dataset}/queries.json","r") as j2:
        queries = json.load(j2)

    with open(f"{dataset}/attr_range.json","r") as j3:
        attr_range = json.load(j3)

    with open(f"{dataset}/query.sql", "rb") as f:
        real_query = f.readlines()

    latencies = []
    q_errors = []
    for i in range(len(queries)): 
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
                del query[q]

        print(f"predicting query no {i}: {real_query[i].strip()}")
        writeDice(query=query, attr_range=attr_range, dataset=dataset, relation=relation, gr=gr, bitwidth=bitwidth)
        card_start_t = perf_counter()
        output = subprocess.getoutput(f"~/Desktop/dice/Dice.native bayescard_{dataset}.dice").split("\n")[1]
        line = re.findall("[0-9\.]+", output)
        prob = float(line[-1].strip())
        if dataset == 'census':
            nrows = 2458285
        elif dataset == 'dmv':
            nrows = 11575483
        else:
            print("Other dataset are not supported yet.")

        cardinality_predict = prob * nrows
        card_end_t = perf_counter()
        latency_ms = (card_end_t-card_start_t) * 1000
        cardinality_true = true_cardinalities[i]

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

        print(f"cardinality predict: {cardinality_predict} and cardinality true: {cardinality_true}")
        print(f"latency: {latency_ms} and error: {q_error} \n")
        latencies.append(latency_ms)
        q_errors.append(q_error)

    print("=====================================================================================")
    for j in [50, 90, 95, 99, 100]:
        print(f"q-error {j}% percentile is {np.percentile(q_errors, j)}") # np.percentile uses same algorithm as percentile formula in Excel
    print(f"average latency is {np.mean(latencies)} ms")
    
    if gr == "yes":
        gr = "gr"
    elif gr == "no":
        gr = "no_gr"
    else:
        print("Incorrect input. Please input yes or no only.")
        return 1
    
    if not os.path.exists(f"{dataset}/{gr}"):
        os.makedirs(f"{dataset}/{gr}")

    with open(f"{dataset}/{gr}/q_errors.json","w+") as qq:
        json.dump(q_errors, qq, indent=2)

    with open(f"{dataset}/{gr}/latencies.json","w+") as t:
        json.dump(latencies, t, indent=2)