import pandas as pd
import json 
from collections import defaultdict
from anytree import Node, PreOrderIter
from anytree.exporter import DotExporter

df = pd.read_csv("discrete_table.csv", header=0, sep=",")

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
    # DotExporter(root).to_picture("BN_chow_liu_tree.pdf")
    
    # Get all possible path starting from root
    whole_tree = list(PreOrderIter(root, filter_=lambda node: node.is_leaf))
    all_path = [str(i)[7:-2].split(i.separator) for i in whole_tree]
    
    return nodes_list, [node.name for node in PreOrderIter(root)], all_path
 
def writeDice(relation):
    global df
    dice = []
    parents, children, nodes = tree_structure(relation)
    nodes_lis, nodes_name, allPath = construct_tree(parents, children, nodes) # produce tree graph "BN_Chow_liu_tree.png"
    
    with open("pgmpyCPD.json","r") as f:
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
        
            # dice.append("let " + n + " = if ((" + par + " == int(" + str(attr_range[par]-1) + ",0))) then (discrete(" + ",".join(cpd_T) + ")) else (discrete(" + ",".join(cpd_F) + ")) in\n")
    
    with open("queries.json","r") as q:
        queries = json.load(q)
        
    for query in queries:
        attrs = list(query.keys())
        l = "\n"
        for n in attrs:
            if attrs.index(n) == len(attrs)-1:
                l += "(" + n 
            else:
                l += "(" + n + ","
        l += ")" * len(attrs)
        
        dice.append(l)
               
    with open("bayescard.dice", "w+") as f:
        f.write("".join(dice))

                
if __name__ == "__main__":
    relation = [('iLang1', 'dAncstry1'), ('dAncstry1', 'dAncstry2'), ('iLooking', 'iAvail'), ('iRPOB', 'iCitizen'), ('dIndustry', 'iClass'), ('dTravtime', 'dDepart'), ('iDisabl2', 'iDisabl1'), ('iYearwrk', 'iDisabl2'), ('iLang1', 'iEnglish'), ('iRvetserv', 'iFeb55'), ('iRelat1', 'iFertil'), ('dAncstry1', 'dHispanic'), ('iWork89', 'dHour89'), ('iRlabor', 'dHours'), ('iRPOB', 'iImmigr'), ('dRearning', 'dIncome1'), ('iClass', 'dIncome2'), ('dOccup', 'dIncome3'), ('dRpincome', 'dIncome4'), ('dAge', 'dIncome5'), ('dRpincome', 'dIncome6'), ('dAge', 'dIncome7'), ('dRpincome', 'dIncome8'), ('dOccup', 'dIndustry'), ('iRvetserv', 'iKorean'), ('iYearsch', 'iLang1'), ('iRlabor', 'iLooking'), ('iRspouse', 'iMarital'), ('iRvetserv', 'iMay75880'), ('dHours', 'iMeans'), ('iRlabor', 'iMilitary'), ('iLang1', 'iMobility'), ('iDisabl1', 'iMobillim'), ('iYearwrk', 'dOccup'), ('iRvetserv', 'iOthrserv'), ('iMobillim', 'iPerscare'), ('dAncstry1', 'dPOB'), ('iRelat1', 'dPoverty'), ('iRPOB', 'dPwgt1'), ('iFertil', 'iRagechld'), ('dHour89', 'dRearning'), ('iRspouse', 'iRelat1'), ('iRelat1', 'iRelat2'), ('iRrelchld', 'iRemplpar'), ('iMeans', 'iRiders'), ('iYearwrk', 'iRlabor'), ('iRemplpar', 'iRownchld'), ('dRearning', 'dRpincome'), ('dPOB', 'iRPOB'), ('dAge', 'iRrelchld'), ('dAge', 'iRspouse'), ('iMilitary', 'iRvetserv'), ('dAge', 'iSchool'), ('iRvetserv', 'iSept80'), ('iRagechld', 'iSex'), ('iRelat1', 'iSubfam1'), ('iSubfam1', 'iSubfam2'), ('iRlabor', 'iTmpabsnt'), ('iMeans', 'dTravtime'), ('iRvetserv', 'iVietnam'), ('dRearning', 'dWeek89'), ('iYearwrk', 'iWork89'), ('iRlabor', 'iWorklwk'), ('iRvetserv', 'iWWII'), ('dAge', 'iYearsch'), ('dAge', 'iYearwrk'), ('iRvetserv', 'dYrsserv')]
    writeDice(relation)
   